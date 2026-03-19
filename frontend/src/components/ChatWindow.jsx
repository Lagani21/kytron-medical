import { useState, useEffect, useRef } from 'react'
import { Send } from 'lucide-react'
import MessageBubble from './MessageBubble.jsx'
import CallMeButton from './CallMeButton.jsx'
import { useChat } from '../hooks/useChat.js'

export default function ChatWindow({ sessionId, patientInfo, onBookingConfirmed }) {
  const { messages, isLoading, sendMessage, addMessage } = useChat(sessionId)
  const [inputText, setInputText] = useState('')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const welcomeSent = useRef(false)
  const confirmedRef = useRef(false)

  // Inject welcome message once on mount
  useEffect(() => {
    if (!welcomeSent.current && patientInfo) {
      welcomeSent.current = true
      const reason = patientInfo.reason?.trim().toLowerCase() || ''
      let welcomeContent
      if (reason.includes('prescription') || reason.includes('refill') || reason.includes('medication refill')) {
        welcomeContent = `Hi ${patientInfo.first_name}! I'm your Kyron Medical Assistant. I see you need a prescription refill. I can help get that request to your doctor. Which medication do you need refilled, and who is your prescribing doctor at our practice?`
      } else if (reason.includes('address') || reason.includes('hours') || reason.includes('location') || reason.includes('office') || reason.includes('where')) {
        welcomeContent = `Hi ${patientInfo.first_name}! I'm your Kyron Medical Assistant. Looking for office information? I can share addresses, hours, and contact details for any of our specialists. Which doctor or specialty are you looking for?`
      } else if (reason) {
        welcomeContent = `Hi ${patientInfo.first_name}! I'm your Kyron Medical Assistant. I understand you're here about: "${patientInfo.reason.trim()}". Let me help you find the right specialist and schedule an appointment. Can you tell me a bit more about what you're experiencing?`
      } else {
        welcomeContent = `Hi ${patientInfo.first_name}! I'm your Kyron Medical Assistant. What brings you in today? I can help you schedule an appointment, check on a prescription refill, or look up office information.`
      }
      addMessage({
        id: `welcome-${Date.now()}`,
        role: 'assistant',
        content: welcomeContent,
        timestamp: new Date(),
        streaming: false,
      })
    }
  }, [patientInfo, addMessage])

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Detect booking confirmation — fire onBookingConfirmed exactly once
  useEffect(() => {
    if (confirmedRef.current) return
    const lastAi = [...messages].reverse().find(m => m.role === 'assistant' && !m.streaming)
    if (!lastAi) return
    const content = lastAi.content
    if (!(content.includes('✅') && content.includes('confirmed'))) return

    const doctorMatch  = content.match(/Doctor: ([^\n]+)/)
    const specialtyMatch = content.match(/Specialty: ([^\n]+)/)
    const dateMatch    = content.match(/Date: ([^\n]+)/)
    const timeMatch    = content.match(/Time: ([^\n]+)/)
    const locationMatch = content.match(/Location: ([^\n]+)/)

    if (doctorMatch && dateMatch && timeMatch) {
      confirmedRef.current = true
      setTimeout(() => {
        onBookingConfirmed({
          doctor_name:  doctorMatch[1].trim(),
          specialty:    specialtyMatch?.[1]?.trim() || '',
          date:         dateMatch[1].trim(),
          time:         timeMatch[1].trim(),
          address:      locationMatch?.[1]?.trim() || '',
        })
      }, 2000)
    }
  }, [messages, onBookingConfirmed])

  const handleSend = () => {
    if (inputText.trim() && !isLoading) {
      sendMessage(inputText.trim())
      setInputText('')
      if (inputRef.current) inputRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSlotClick = (slot) => {
    setInputText(`Book ${slot.date} at ${slot.time}`)
    inputRef.current?.focus()
  }

  return (
    <div className="flex flex-col page-in" style={{ height: '100dvh' }}>

      {/* ── Top bar ─────────────────────────────────────────────── */}
      <div className="topbar flex items-center px-4 sm:px-5 flex-shrink-0" style={{ height: '56px' }}>
        {/* Left: logo + name */}
        <div className="flex items-center gap-2.5">
          <span style={{ color: '#2563EB', fontSize: '18px', lineHeight: 1 }}>◆</span>
          <span style={{ fontWeight: 600, fontSize: '14px', color: '#0F172A' }}>
            Kyron Medical Assistant
          </span>
        </div>

        {/* Center: status */}
        <div className="flex items-center gap-2 mx-auto">
          <div className="status-dot" />
          <span style={{ fontSize: '13px', color: '#475569' }}>Online</span>
        </div>

        {/* Right: call me */}
        <CallMeButton sessionId={sessionId} phone={patientInfo?.phone} />
      </div>

      {/* ── Messages ────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-3 sm:px-6 lg:px-20 xl:px-40 py-5">
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
          {messages.map(msg => (
            <MessageBubble key={msg.id} message={msg} onSlotClick={handleSlotClick} />
          ))}

          {/* Typing indicator — only while waiting for first chunk */}
          {isLoading && !messages.some(m => m.streaming) && (
            <div className="flex items-end gap-2 mb-3 msg-appear">
              <div className="ai-avatar">K</div>
              <div style={{
                background: '#FFFFFF',
                border: '1px solid rgba(0,0,0,0.08)',
                borderRadius: '18px 18px 18px 4px',
                padding: '12px 16px',
                display: 'flex', alignItems: 'center', gap: '5px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
              }}>
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* ── Input bar ───────────────────────────────────────────── */}
      <div className="bottombar px-3 sm:px-6 lg:px-20 xl:px-40 py-3 flex-shrink-0">
        <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', alignItems: 'flex-end', gap: '10px' }}>
          <textarea
            ref={inputRef}
            className="input-field"
            rows={1}
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message… (Enter to send)"
            style={{
              flex: 1,
              borderRadius: '24px',
              padding: '10px 18px',
              resize: 'none',
              minHeight: '44px',
              maxHeight: '120px',
              lineHeight: '1.5',
            }}
            onInput={e => {
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
            }}
          />
          <button
            onClick={handleSend}
            disabled={!inputText.trim() || isLoading}
            aria-label="Send message"
            style={{
              width: '40px', height: '40px', flexShrink: 0,
              background: (!inputText.trim() || isLoading) ? 'rgba(0,0,0,0.08)' : '#2563EB',
              border: 'none', borderRadius: '50%',
              cursor: (!inputText.trim() || isLoading) ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'all 0.15s ease',
              boxShadow: (!inputText.trim() || isLoading) ? 'none' : '0 4px 12px rgba(37,99,235,0.3)',
            }}
            onMouseEnter={e => {
              if (inputText.trim() && !isLoading) e.currentTarget.style.background = '#1D4ED8'
            }}
            onMouseLeave={e => {
              if (inputText.trim() && !isLoading) e.currentTarget.style.background = '#2563EB'
            }}
          >
            <Send size={16} color="white" />
          </button>
        </div>
      </div>
    </div>
  )
}
