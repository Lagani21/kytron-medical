import { useState, useCallback, useRef } from 'react'
import { ENDPOINTS } from '../config.js'

let msgCounter = 0
function nextId() {
  return `msg-${Date.now()}-${++msgCounter}`
}

export function useChat(sessionId) {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  // Prevent concurrent sends
  const loadingRef = useRef(false)

  const addMessage = useCallback((message) => {
    setMessages(prev => [...prev, message])
  }, [])

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || loadingRef.current) return
    loadingRef.current = true
    setIsLoading(true)

    const userMsg = {
      id: nextId(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMsg])

    // aiMsg is injected lazily on the first streamed chunk so the
    // typing indicator shows until actual text begins arriving.
    const aiMsgId = nextId()
    let aiMsgAdded = false

    try {
      const response = await fetch(ENDPOINTS.chat, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: text }),
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        setMessages(prev => [...prev, {
          id: aiMsgId,
          role: 'assistant',
          content: err.error || 'Something went wrong. Please try again.',
          timestamp: new Date(),
          streaming: false,
        }])
        return
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let fullContent = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        fullContent += chunk

        if (!aiMsgAdded) {
          // First chunk: add the message bubble (typing indicator disappears)
          aiMsgAdded = true
          setMessages(prev => [...prev, {
            id: aiMsgId,
            role: 'assistant',
            content: fullContent,
            timestamp: new Date(),
            streaming: true,
          }])
        } else {
          setMessages(prev => prev.map(m =>
            m.id === aiMsgId ? { ...m, content: fullContent } : m
          ))
        }
      }

      // Mark stream complete
      if (aiMsgAdded) {
        setMessages(prev => prev.map(m =>
          m.id === aiMsgId ? { ...m, streaming: false } : m
        ))
      } else {
        // Empty response edge case
        setMessages(prev => [...prev, {
          id: aiMsgId,
          role: 'assistant',
          content: 'No response received. Please try again.',
          timestamp: new Date(),
          streaming: false,
        }])
      }
    } catch {
      setMessages(prev => {
        if (aiMsgAdded) {
          return prev.map(m =>
            m.id === aiMsgId ? { ...m, content: 'Connection error. Please try again.', streaming: false } : m
          )
        }
        return [...prev, {
          id: aiMsgId,
          role: 'assistant',
          content: 'Connection error. Please try again.',
          timestamp: new Date(),
          streaming: false,
        }]
      })
    } finally {
      loadingRef.current = false
      setIsLoading(false)
    }
  }, [sessionId])

  return { messages, isLoading, sendMessage, addMessage }
}
