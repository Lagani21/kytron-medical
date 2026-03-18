# Kyron Medical Assistant

A patient-facing medical appointment web app with an AI-powered chat interface. Built with **React + Vite** (frontend) and **FastAPI** (backend). All external API integrations (OpenAI, Vapi, SendGrid, Twilio) are stubbed with realistic mock responses — no real API keys needed to run.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, lucide-react |
| Backend | FastAPI, Uvicorn, Pydantic v2 |
| AI | Stubbed (pure Python keyword matching + streaming) |
| Voice | Vapi stub |
| Email | SendGrid stub |
| SMS | Twilio stub |

---

## Setup & Running

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

The API starts at **http://localhost:8000**. All routes are logged on startup.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

The UI starts at **http://localhost:5173**. The Vite dev server proxies `/api/*` requests to the backend automatically.

> **No real API keys required.** All stubs return realistic responses immediately.

---

## App Flow

```
IntakeForm  →  ChatWindow  →  BookingConfirmation
   ↓               ↓
POST /api/intake   POST /api/chat  (streaming)
                   POST /api/book
                   POST /api/voice/initiate
```

1. **Intake** — patient fills in name, DOB, phone, email, reason for visit (+ optional SMS opt-in)
2. **Chat** — AI assistant greets patient, matches symptoms to a specialist, shows available slots as clickable pills, confirms booking
3. **Confirmation** — animated confirmation card with doctor details, date/time, location, and email/SMS notice

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/intake` | Save patient info, create session |
| POST | `/api/chat` | Streaming AI chat response |
| GET | `/api/slots/{session_id}` | Available slots for matched doctor |
| POST | `/api/book` | Book a slot |
| POST | `/api/voice/initiate` | Initiate voice call (stubbed) |

---

## Doctors

| ID | Name | Specialty | Keywords |
|---|---|---|---|
| `chen` | Dr. Sarah Chen | Cardiology | heart, chest pain, blood pressure, palpitations… |
| `webb` | Dr. Marcus Webb | Orthopedics | knee, hip, shoulder, back, joints… |
| `nair` | Dr. Priya Nair | Dermatology | skin, rash, acne, moles, eczema… |
| `okafor` | Dr. James Okafor | Neurology | headaches, migraines, dizziness, numbness… |

Each doctor has 4 slots per weekday (9:00 AM, 10:30 AM, 2:00 PM, 3:30 PM) across the next 45 weekdays.

---

## Environment Variables

`backend/.env` — all stubs, no real keys needed:

```
OPENAI_API_KEY=sk-stub
VAPI_API_KEY=stub
SENDGRID_API_KEY=stub
TWILIO_ACCOUNT_SID=stub
TWILIO_AUTH_TOKEN=stub
TWILIO_PHONE_NUMBER=+15550000000
```

---

## AI Stub Behaviour

The AI service (`backend/services/ai_service.py`) uses pure Python logic — no LLM calls:

- **Symptom → specialist**: keyword matching across 4 specialty lists
- **Slot queries**: "show me slots", "do you have anything on Tuesday?" → filtered results
- **Booking**: "Book 2026-04-01 at 9:00 AM" → confirms and marks slot booked
- **Office info**: returns address, hours, phone for matched doctor
- **Medical advice**: returns a safe refusal message
- **Prescription refill**: redirects to call the office
- Responses stream **word by word** (40 ms/word) so the frontend can render them progressively
