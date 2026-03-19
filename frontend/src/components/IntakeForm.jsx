import { useState } from 'react'
import { ENDPOINTS, API_HEADERS } from '../config.js'

export default function IntakeForm({ onComplete }) {
  const [form, setForm] = useState({
    first_name: '', last_name: '', dob: '',
    phone: '', email: '', reason: '', sms_opt_in: false,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await fetch(ENDPOINTS.intake, {
        method: 'POST',
        headers: API_HEADERS,
        body: JSON.stringify(form),
      })
      const data = await res.json()
      if (data.session_id) {
        onComplete(data.session_id, form)
      } else {
        setError(data.detail || data.error || 'Something went wrong. Please try again.')
      }
    } catch {
      setError('Unable to connect. Is the backend running on port 8000?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 page-in">
      {/* Logo + heading above card */}
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-2 mb-4">
          <span style={{ color: '#2563EB', fontSize: '26px', lineHeight: 1 }}>◆</span>
          <span style={{ fontWeight: 700, fontSize: '18px', letterSpacing: '0.1em', color: '#0F172A' }}>
            KYRON
          </span>
          <span style={{ fontWeight: 400, fontSize: '18px', letterSpacing: '0.1em', color: '#94A3B8' }}>
            MEDICAL
          </span>
        </div>
        <h1 style={{ fontWeight: 800, fontSize: '32px', letterSpacing: '-0.03em', color: '#0F172A', lineHeight: 1.2 }}>
          Patient Check-In
        </h1>
        <p style={{ fontSize: '13px', color: '#94A3B8', marginTop: '8px' }}>
          Securely managed by Kyron Medical
        </p>
      </div>

      {/* Form card */}
      <div className="card w-full max-w-lg" style={{ padding: '32px' }}>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Name row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label style={labelStyle}>First Name</label>
              <input
                className="input-field"
                name="first_name"
                value={form.first_name}
                onChange={handleChange}
                placeholder="Jane"
                required
              />
            </div>
            <div>
              <label style={labelStyle}>Last Name</label>
              <input
                className="input-field"
                name="last_name"
                value={form.last_name}
                onChange={handleChange}
                placeholder="Doe"
                required
              />
            </div>
          </div>

          <div>
            <label style={labelStyle}>Date of Birth</label>
            <input type="date" className="input-field" name="dob" value={form.dob} onChange={handleChange} required />
          </div>

          <div>
            <label style={labelStyle}>Phone Number</label>
            <input
              type="tel"
              className="input-field"
              name="phone"
              value={form.phone}
              onChange={handleChange}
              placeholder="+1 (555) 000-0000"
              required
            />
          </div>

          <div>
            <label style={labelStyle}>Email Address</label>
            <input
              type="email"
              className="input-field"
              name="email"
              value={form.email}
              onChange={handleChange}
              placeholder="jane@example.com"
              required
            />
          </div>

          <div>
            <label style={labelStyle}>Reason for Visit</label>
            <textarea
              className="input-field"
              name="reason"
              value={form.reason}
              onChange={handleChange}
              placeholder="Describe your symptoms or reason for the appointment..."
              style={{ minHeight: '80px', resize: 'vertical' }}
              required
            />
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              name="sms_opt_in"
              checked={form.sms_opt_in}
              onChange={handleChange}
              style={{ width: '16px', height: '16px', accentColor: '#2563EB', cursor: 'pointer' }}
            />
            <span style={{ fontSize: '13px', color: '#475569' }}>
              Send me SMS appointment reminders
            </span>
          </label>

          {error && (
            <div style={{
              fontSize: '13px', color: '#EF4444', textAlign: 'center',
              padding: '10px 12px', background: 'rgba(239,68,68,0.1)',
              border: '1px solid rgba(239,68,68,0.2)', borderRadius: '8px',
            }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary"
            style={{ width: '100%', height: '44px', fontSize: '15px', marginTop: '4px' }}
          >
            {loading ? (
              <>
                <span className="btn-spinner" />
                Setting up your assistant...
              </>
            ) : 'Continue →'}
          </button>
        </form>
      </div>
    </div>
  )
}

const labelStyle = {
  display: 'block',
  fontSize: '13px',
  color: '#94A3B8',
  marginBottom: '6px',
  fontWeight: '500',
}
