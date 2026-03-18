import { Mail, MessageSquare } from 'lucide-react'

const SPECIALTY_BADGE = {
  Cardiology:  { bg: 'rgba(239,68,68,0.15)',   text: '#EF4444',  border: 'rgba(239,68,68,0.3)' },
  Orthopedics: { bg: 'rgba(245,158,11,0.15)',  text: '#F59E0B',  border: 'rgba(245,158,11,0.3)' },
  Dermatology: { bg: 'rgba(167,139,250,0.15)', text: '#A78BFA',  border: 'rgba(167,139,250,0.3)' },
  Neurology:   { bg: 'rgba(96,165,250,0.15)',  text: '#60A5FA',  border: 'rgba(96,165,250,0.3)' },
}

function SpecialtyBadge({ specialty }) {
  const colors = SPECIALTY_BADGE[specialty] || {
    bg: 'rgba(255,255,255,0.08)', text: 'rgba(255,255,255,0.7)', border: 'rgba(255,255,255,0.15)',
  }
  return (
    <span style={{
      fontSize: '11px', fontWeight: 600,
      padding: '2px 8px', borderRadius: '4px',
      background: colors.bg, color: colors.text,
      border: `1px solid ${colors.border}`,
    }}>
      {specialty}
    </span>
  )
}

function DetailRow({ label, value, extra }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
      <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)', flexShrink: 0 }}>{label}</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', textAlign: 'right' }}>
        <span style={{ fontSize: '14px', fontWeight: 500, color: 'white' }}>{value}</span>
        {extra}
      </div>
    </div>
  )
}

export default function BookingConfirmation({ bookingData, patientInfo, onReset }) {
  const d = bookingData || {}

  return (
    <div className="min-h-screen flex items-center justify-center p-4 page-in">
      <div className="card w-full max-w-lg" style={{ padding: '40px 36px', textAlign: 'center' }}>

        {/* Animated checkmark */}
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '24px' }}>
          <svg className="check-circle" width="64" height="64" viewBox="0 0 64 64" fill="none">
            <circle cx="32" cy="32" r="30" stroke="#2563EB" strokeWidth="2" fill="rgba(37,99,235,0.1)" />
            <polyline
              className="check-path"
              points="18,32 27,41 46,22"
              stroke="#2563EB"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        <h1 style={{ fontWeight: 700, fontSize: '28px', letterSpacing: '-0.01em', color: 'white', marginBottom: '8px' }}>
          You're all set, {patientInfo?.first_name}!
        </h1>
        <p style={{ fontSize: '14px', color: 'rgba(255,255,255,0.5)', marginBottom: '28px' }}>
          Your appointment has been confirmed.
        </p>

        {/* Appointment details */}
        <div className="card-inner" style={{ padding: '20px', textAlign: 'left', marginBottom: '20px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <DetailRow
              label="Doctor"
              value={d.doctor_name}
              extra={d.specialty && <SpecialtyBadge specialty={d.specialty} />}
            />
            <div style={{ height: '1px', background: 'rgba(255,255,255,0.06)' }} />
            <DetailRow label="Date" value={d.date} />
            <div style={{ height: '1px', background: 'rgba(255,255,255,0.06)' }} />
            <DetailRow label="Time" value={d.time} />
            {d.address && (
              <>
                <div style={{ height: '1px', background: 'rgba(255,255,255,0.06)' }} />
                <DetailRow label="Location" value={d.address} />
              </>
            )}
          </div>
        </div>

        {/* Notification confirmations */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '24px' }}>
          {patientInfo?.email && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              padding: '10px 14px', borderRadius: '8px',
              background: 'rgba(37,99,235,0.08)',
              border: '1px solid rgba(37,99,235,0.2)',
            }}>
              <Mail size={15} color="#60A5FA" style={{ flexShrink: 0 }} />
              <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)' }}>
                Confirmation email sent to{' '}
                <span style={{ color: 'white', fontWeight: 500 }}>{patientInfo.email}</span>
              </span>
            </div>
          )}
          {patientInfo?.sms_opt_in && patientInfo?.phone && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              padding: '10px 14px', borderRadius: '8px',
              background: 'rgba(37,99,235,0.08)',
              border: '1px solid rgba(37,99,235,0.2)',
            }}>
              <MessageSquare size={15} color="#60A5FA" style={{ flexShrink: 0 }} />
              <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)' }}>
                Text confirmation sent to{' '}
                <span style={{ color: 'white', fontWeight: 500 }}>{patientInfo.phone}</span>
              </span>
            </div>
          )}
        </div>

        <button className="btn-outlined" onClick={onReset} style={{ width: '100%', height: '44px', fontSize: '14px' }}>
          Book another appointment
        </button>
      </div>
    </div>
  )
}
