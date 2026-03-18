// Detect slot lines emitted by AI: "• YYYY-MM-DD at H:MM AM/PM"
function parseSlots(content) {
  const re = /•\s*(\d{4}-\d{2}-\d{2})\s+at\s+(\d{1,2}:\d{2}\s*(?:AM|PM))/gi
  const slots = []
  let m
  while ((m = re.exec(content)) !== null) {
    slots.push({ date: m[1], time: m[2].toUpperCase().trim() })
  }
  return slots
}

function formatTime(date) {
  return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function MessageBubble({ message, onSlotClick }) {
  const isUser = message.role === 'user'
  const slots = !isUser ? parseSlots(message.content) : []

  if (isUser) {
    return (
      <div className="flex justify-end mb-3 msg-appear">
        <div style={{ maxWidth: '72%' }}>
          <div style={{
            background: '#2563EB',
            color: 'white',
            borderRadius: '18px 18px 4px 18px',
            padding: '10px 16px',
            fontSize: '14px',
            lineHeight: '1.5',
            wordBreak: 'break-word',
          }}>
            {message.content}
          </div>
          <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.3)', marginTop: '4px', textAlign: 'right' }}>
            {formatTime(message.timestamp)}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-end gap-2 mb-3 msg-appear">
      <div className="ai-avatar">K</div>
      <div style={{ maxWidth: '72%' }}>
        <div style={{
          background: 'rgba(255,255,255,0.06)',
          border: '1px solid rgba(255,255,255,0.08)',
          color: 'rgba(255,255,255,0.9)',
          borderRadius: '18px 18px 18px 4px',
          padding: '10px 16px',
          fontSize: '14px',
          lineHeight: '1.5',
          wordBreak: 'break-word',
          whiteSpace: 'pre-wrap',
        }}>
          {message.content}
          {message.streaming && <span className="stream-cursor" />}
        </div>

        {/* Slot selection pills — only after stream is complete */}
        {slots.length > 0 && !message.streaming && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '8px' }}>
            {slots.map((slot, i) => (
              <button
                key={i}
                className="filter-pill"
                onClick={() => onSlotClick && onSlotClick(slot)}
              >
                {slot.date} · {slot.time}
              </button>
            ))}
          </div>
        )}

        <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.3)', marginTop: '4px' }}>
          {formatTime(message.timestamp)}
        </div>
      </div>
    </div>
  )
}
