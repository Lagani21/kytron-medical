// Central API configuration.
// In development Vite proxies /api → http://localhost:8000 automatically.
// Set VITE_API_URL in frontend/.env to override for production.
const API_BASE = import.meta.env.VITE_API_URL ?? ''

export const ENDPOINTS = {
  intake:        `${API_BASE}/api/intake`,
  chat:          `${API_BASE}/api/chat`,
  slots:         (sessionId) => `${API_BASE}/api/slots/${sessionId}`,
  book:          `${API_BASE}/api/book`,
  voiceInitiate: `${API_BASE}/api/voice/initiate`,
}
