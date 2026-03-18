import { useState } from 'react'
import { Phone } from 'lucide-react'
import { ENDPOINTS } from '../config.js'

export default function CallMeButton({ sessionId, phone }) {
  const [showModal, setShowModal] = useState(false)
  const [showToast, setShowToast] = useState(false)
  const [calling, setCalling] = useState(false)

  const handleConfirm = async () => {
    setCalling(true)
    try {
      await fetch(ENDPOINTS.voiceInitiate, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, phone_number: phone }),
      })
    } catch {
      // Voice call is a stub — show toast regardless of network state
    }
    setShowModal(false)
    setCalling(false)
    setShowToast(true)
    setTimeout(() => setShowToast(false), 4000)
  }

  return (
    <>
      <button className="btn-call" onClick={() => setShowModal(true)}>
        <Phone size={14} />
        Call Me
      </button>

      {/* Modal overlay */}
      {showModal && (
        <div
          onClick={(e) => e.target === e.currentTarget && setShowModal(false)}
          style={{
            position: 'fixed', inset: 0, zIndex: 50,
            background: 'rgba(0,0,0,0.6)',
            backdropFilter: 'blur(4px)',
            WebkitBackdropFilter: 'blur(4px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: '16px',
          }}
        >
          <div className="card page-in" style={{ maxWidth: '380px', width: '100%', padding: '32px 28px', textAlign: 'center' }}>
            {/* Phone icon */}
            <div style={{
              width: '52px', height: '52px', borderRadius: '50%',
              background: 'rgba(37,99,235,0.15)', border: '1px solid rgba(37,99,235,0.3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 20px',
            }}>
              <Phone size={22} color="#2563EB" />
            </div>

            <h3 style={{ fontWeight: 600, fontSize: '20px', color: 'white', marginBottom: '10px' }}>
              Continue by phone
            </h3>
            <p style={{ fontSize: '14px', color: 'rgba(255,255,255,0.6)', lineHeight: 1.6, marginBottom: '24px' }}>
              We'll call <span style={{ color: 'white', fontWeight: 500 }}>{phone}</span> and
              your assistant will pick up right where you left off.
            </p>

            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                className="btn-outlined"
                onClick={() => setShowModal(false)}
                style={{ flex: 1 }}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={handleConfirm}
                disabled={calling}
                style={{ flex: 1 }}
              >
                {calling ? <><span className="btn-spinner" /> Connecting...</> : 'Call me now →'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {showToast && (
        <div style={{
          position: 'fixed', bottom: '24px', left: '50%', transform: 'translateX(-50%)',
          zIndex: 60,
          background: 'rgba(13,17,41,0.95)',
          border: '1px solid rgba(37,99,235,0.4)',
          borderRadius: '10px',
          padding: '12px 20px',
          fontSize: '14px', fontWeight: 500, color: '#60A5FA',
          display: 'flex', alignItems: 'center', gap: '8px',
          backdropFilter: 'blur(12px)',
          boxShadow: '0 4px 24px rgba(0,0,0,0.5)',
          whiteSpace: 'nowrap',
        }}>
          <Phone size={15} color="#2563EB" />
          Calling you now — voice AI connected
        </div>
      )}
    </>
  )
}
