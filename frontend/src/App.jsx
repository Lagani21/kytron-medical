import { useState } from 'react'
import IntakeForm from './components/IntakeForm.jsx'
import ChatWindow from './components/ChatWindow.jsx'
import BookingConfirmation from './components/BookingConfirmation.jsx'

export default function App() {
  const [view, setView] = useState('intake') // 'intake' | 'chat' | 'confirmed'
  const [sessionId, setSessionId] = useState(null)
  const [patientInfo, setPatientInfo] = useState(null)
  const [bookingData, setBookingData] = useState(null)

  const handleIntakeComplete = (sid, info) => {
    setSessionId(sid)
    setPatientInfo(info)
    setView('chat')
  }

  const handleBookingConfirmed = (data) => {
    setBookingData(data)
    setView('confirmed')
  }

  const handleReset = () => {
    setView('intake')
    setSessionId(null)
    setPatientInfo(null)
    setBookingData(null)
  }

  return (
    <div className="relative min-h-screen">
      {/* Background orbs */}
      <div className="bg-orbs">
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />
      </div>

      {/* Content */}
      <div className="relative z-10">
        {view === 'intake' && (
          <IntakeForm onComplete={handleIntakeComplete} />
        )}
        {view === 'chat' && (
          <ChatWindow
            sessionId={sessionId}
            patientInfo={patientInfo}
            onBookingConfirmed={handleBookingConfirmed}
          />
        )}
        {view === 'confirmed' && (
          <BookingConfirmation
            bookingData={bookingData}
            patientInfo={patientInfo}
            onReset={handleReset}
          />
        )}
      </div>
    </div>
  )
}
