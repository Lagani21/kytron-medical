import asyncio
import json
import os
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse, Response

import websockets

from models import VoiceCallRequest
from session_store import get_session, update_session, get_session_id_by_phone, create_session
from services.voice_service import initiate_voice_call
from data.doctors import DOCTORS

router = APIRouter()
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL       = os.getenv("BASE_URL", "")
REALTIME_URL   = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"


# ─── 1. Initiate call ────────────────────────────────────────────────────────

@router.post("/api/voice/initiate")
async def voice_initiate(req: VoiceCallRequest):
    session = get_session(req.session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    result = initiate_voice_call(req.phone_number, req.session_id)
    return result


# ─── 2. TwiML webhook — Twilio fetches this when the patient picks up ────────

@router.post("/api/voice/twiml/{session_id}")
async def voice_twiml(session_id: str, request: Request):
    ws_url = f"{BASE_URL.replace('https://', 'wss://').replace('http://', 'ws://')}/ws/voice/{session_id}"
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{ws_url}" />
  </Connect>
</Response>"""
    return Response(content=twiml, media_type="text/xml")


# ─── 2b. Inbound call webhook — patient calls the Twilio number directly ─────

@router.post("/api/voice/inbound")
async def voice_inbound(request: Request):
    """
    Twilio posts here when the patient calls the Kyron number directly.
    We look up their session by caller ID so the AI resumes with full context.
    """
    form = await request.form()
    from_number = form.get("From", "")

    session_id = get_session_id_by_phone(from_number) if from_number else None
    session = get_session(session_id) if session_id else None

    if session and session.get("intake_complete"):
        # Returning patient — resume context via the existing WebSocket bridge
        ws_url = (
            f"{BASE_URL.replace('https://', 'wss://').replace('http://', 'ws://')}"
            f"/ws/voice/{session_id}"
        )
        logger.info(f"Inbound call from {from_number} → resuming session {session_id}")
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{ws_url}" />
  </Connect>
</Response>"""
    else:
        # Unknown caller — no session on file
        logger.info(f"Inbound call from unknown number {from_number}")
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">
    Hi, thank you for calling Kyron Medical. To get started, please visit our website
    to complete a quick intake form. Once that's done, you can call us back and I'll
    be able to pull up your information right away. Thank you!
  </Say>
</Response>"""

    return Response(content=twiml, media_type="text/xml")


# ─── 2c. Post-appointment follow-up SMS scheduler ────────────────────────────

async def _send_followup_sms(phone: str, doctor_name: str, date: str, time: str):
    """Fires ~24 hours after the appointment slot to check in with the patient."""
    from datetime import datetime, timedelta
    from services.sms_service import send_confirmation_sms  # reuse sender

    # Calculate seconds until 24h after the appointment
    try:
        appt_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %I:%M %p")
    except ValueError:
        appt_dt = datetime.now()

    followup_dt = appt_dt + timedelta(hours=24)
    delay_seconds = max((followup_dt - datetime.now()).total_seconds(), 60)
    await asyncio.sleep(delay_seconds)

    # Re-use the SMS sender with a custom body by monkey-patching is ugly —
    # call Twilio directly here for a clean follow-up message.
    try:
        import os
        from twilio.rest import Client

        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token  = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_FROM_NUMBER")
        if not all([account_sid, auth_token, from_number]):
            logger.info(f"[STUB] Follow-up SMS to {phone} — Twilio not configured")
            return

        client = Client(account_sid, auth_token)
        body = (
            f"Hi! This is Kyron Medical checking in after your appointment with {doctor_name} today. "
            "We hope everything went well. Reply with any questions or call us to schedule a follow-up."
        )
        from session_store import _normalize
        client.messages.create(body=body, from_=from_number, to=_normalize(phone))
        logger.info(f"[SMS] Follow-up sent to {phone}")
    except Exception as exc:
        logger.error(f"[SMS] Follow-up failed for {phone}: {exc}")


def schedule_followup(phone: str, doctor_name: str, date: str, time: str, sms_opt_in: bool):
    """Schedule a post-appointment follow-up SMS if the patient opted in."""
    if not sms_opt_in or not phone:
        return
    import asyncio as _asyncio
    try:
        loop = _asyncio.get_event_loop()
        loop.create_task(_send_followup_sms(phone, doctor_name, date, time))
        logger.info(f"Follow-up SMS scheduled for {phone} after {date} {time}")
    except RuntimeError:
        pass  # No running loop (e.g. during tests)


# ─── 3. System prompt ────────────────────────────────────────────────────────

def _build_system_prompt(session: dict) -> str:
    patient    = session.get("patient_info", {})
    history    = session.get("conversation_history", [])
    doctor_id  = session.get("matched_doctor")
    booked     = session.get("booked_slot")

    name   = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
    reason = patient.get("reason", "unspecified")

    doc_block = ""
    if doctor_id and doctor_id in DOCTORS:
        doc = DOCTORS[doctor_id]
        doc_block = (
            f"\nMatched specialist: {doc['name']} ({doc['specialty']})"
            f"\nOffice address:     {doc['office']}"
            f"\nOffice phone:       {doc['phone']}"
            f"\nOffice hours:       {doc['hours']}"
        )

    booked_block = ""
    if booked:
        booked_block = f"\nAppointment ALREADY BOOKED: {booked.get('date')} at {booked.get('time')}"

    history_block = ""
    if history:
        lines = []
        for msg in history:
            role = "Patient" if msg.get("role") == "user" else "Assistant"
            lines.append(f"  {role}: {msg.get('content', '')}")
        history_block = "\n\nPRIOR WEB CHAT:\n" + "\n".join(lines)

    return f"""You are a friendly, professional voice assistant for Kyron Medical.
You are continuing a conversation that began on the Kyron Medical website chat.
Pick up naturally where the chat left off — do not re-read the whole history aloud.

PATIENT: {name}
REASON:  {reason}{doc_block}{booked_block}{history_block}

════════════════════════════════════════════
SAFETY RULES — ABSOLUTE, NON-NEGOTIABLE
════════════════════════════════════════════
1. NEVER provide medical advice, diagnosis, prognosis, or treatment of any kind.
2. NEVER suggest what condition or illness a patient might have.
3. NEVER recommend medications, dosages, supplements, or home remedies.
4. NEVER interpret symptoms beyond routing to a specialist.
5. NEVER comment on lab results, imaging, or test results.
6. If asked ANY medical question, say exactly:
   "I'm not able to give medical advice — that's something to discuss with your doctor at your appointment."
7. If the patient describes a medical emergency or says they cannot breathe, have chest pain, etc., say immediately:
   "If this is an emergency, please hang up now and call 911."
8. Do NOT speculate, reassure, or offer any opinion on whether symptoms are serious.
9. Do NOT confirm or deny whether something sounds normal or concerning.
10. These rules override all other instructions.

════════════════════════════════════════════
YOUR WORKFLOWS
════════════════════════════════════════════

APPOINTMENT SCHEDULING (primary task):
- If appointment is already booked: confirm the date, time, doctor, and address warmly.
  Ask if they have logistical questions (directions, parking, what to bring — NOT medical questions).
- If not yet booked: call get_available_slots, offer 3 options naturally (say "Wednesday March 19th at nine AM"),
  then call book_appointment when they confirm.
- After booking: confirm aloud and tell them they'll receive a confirmation email.

PRESCRIPTION REFILLS:
- "For prescription refills, please call the office directly at {DOCTORS.get(doctor_id, {}).get('phone', 'the office')}."

LAB / TEST RESULTS:
- "For test results, please contact the office — they'll go through everything with you and your doctor."

OFFICE INFORMATION:
- You have the address, phone, and hours above. Share them when asked.

GENERAL CONDUCT:
- Keep responses short — this is a phone call.
- Speak naturally: say "nine AM" not "9:00 AM", "March nineteenth" not "2026-03-19".
- Be warm but efficient. Do not repeat the patient's details unnecessarily.
- If the patient is frustrated, empathize briefly: "I completely understand, let me help you sort this out."
"""


# ─── 4. Tool definitions ─────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "name": "get_available_slots",
        "description": "Get the next available appointment slots for the patient's matched doctor.",
        "parameters": {
            "type": "object",
            "properties": {
                "doctor_id": {
                    "type": "string",
                    "description": "Doctor ID: chen, webb, nair, or okafor"
                }
            },
            "required": ["doctor_id"]
        }
    },
    {
        "type": "function",
        "name": "book_appointment",
        "description": "Book a specific appointment slot for the patient after they confirm.",
        "parameters": {
            "type": "object",
            "properties": {
                "doctor_id": {"type": "string"},
                "date":      {"type": "string", "description": "YYYY-MM-DD"},
                "time":      {"type": "string", "description": "Exact time string from get_available_slots"}
            },
            "required": ["doctor_id", "date", "time"]
        }
    }
]


def _run_tool(name: str, args: dict, session_id: str) -> str:
    if name == "get_available_slots":
        doctor_id = args.get("doctor_id", "")
        doc = DOCTORS.get(doctor_id)
        if not doc:
            return json.dumps({"error": "Unknown doctor ID"})
        available = [s for s in doc["slots"] if s["status"] == "available"][:5]
        return json.dumps({
            "doctor": doc["name"],
            "specialty": doc["specialty"],
            "slots": [{"date": s["date"], "time": s["time"]} for s in available]
        })

    if name == "book_appointment":
        doctor_id = args.get("doctor_id", "")
        date      = args.get("date", "")
        time      = args.get("time", "")
        doc = DOCTORS.get(doctor_id)
        if not doc:
            return json.dumps({"error": "Unknown doctor ID"})
        for slot in doc["slots"]:
            if slot["date"] == date and slot["time"] == time and slot["status"] == "available":
                slot["status"] = "booked"
                update_session(session_id, booked_slot={"date": date, "time": time, "doctor_id": doctor_id})
                return json.dumps({
                    "confirmed":   True,
                    "doctor_name": doc["name"],
                    "specialty":   doc["specialty"],
                    "date":        date,
                    "time":        time,
                    "address":     doc["office"],
                    "phone":       doc["phone"]
                })
        return json.dumps({"error": "Slot no longer available — please choose another"})

    return json.dumps({"error": f"Unknown tool: {name}"})


# ─── 5. WebSocket bridge: Twilio ↔ OpenAI Realtime ──────────────────────────

@router.websocket("/ws/voice/{session_id}")
async def voice_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    session = get_session(session_id)
    if not session:
        await websocket.close(code=1008, reason="Session not found")
        return

    system_prompt = _build_system_prompt(session)
    doctor_id     = session.get("matched_doctor")

    openai_headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta":   "realtime=v1",
    }

    try:
        async with websockets.connect(REALTIME_URL, additional_headers=openai_headers) as openai_ws:

            # Configure the Realtime session
            await openai_ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "turn_detection":      {"type": "server_vad"},
                    "input_audio_format":  "g711_ulaw",
                    "output_audio_format": "g711_ulaw",
                    "voice":               "alloy",
                    "instructions":        system_prompt,
                    "modalities":          ["text", "audio"],
                    "temperature":         0.7,
                    "tools":               TOOLS,
                    "tool_choice":         "auto",
                }
            }))

            # Trigger the assistant's opening greeting
            patient_name = session.get("patient_info", {}).get("first_name", "")
            greeting = (
                f"Hi {patient_name}, I'm your Kyron Medical assistant. I'm picking up right where our chat left off — how can I help?"
                if patient_name else
                "Hi, I'm your Kyron Medical assistant, picking up from your web chat. How can I help?"
            )
            await openai_ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "__start__"}]
                }
            }))
            await openai_ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "text", "text": greeting}]
                }
            }))
            await openai_ws.send(json.dumps({"type": "response.create"}))

            stream_sid         = None
            fn_call_id         = None
            fn_call_name       = None
            fn_call_args_buf   = ""

            async def from_twilio():
                nonlocal stream_sid
                async for raw in websocket.iter_text():
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue

                    event = msg.get("event")

                    if event == "start":
                        stream_sid = msg["start"]["streamSid"]
                        logger.info(f"Twilio stream started: {stream_sid}")

                    elif event == "media":
                        await openai_ws.send(json.dumps({
                            "type":  "input_audio_buffer.append",
                            "audio": msg["media"]["payload"]
                        }))

                    elif event == "stop":
                        logger.info("Twilio stream stopped")
                        break

            async def from_openai():
                nonlocal stream_sid, fn_call_id, fn_call_name, fn_call_args_buf
                async for raw in openai_ws:
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue

                    t = msg.get("type", "")

                    # Stream audio back to Twilio
                    if t == "response.audio.delta" and msg.get("delta") and stream_sid:
                        await websocket.send_text(json.dumps({
                            "event":     "media",
                            "streamSid": stream_sid,
                            "media":     {"payload": msg["delta"]}
                        }))

                    # Capture function call name + id
                    elif t == "response.output_item.added":
                        item = msg.get("item", {})
                        if item.get("type") == "function_call":
                            fn_call_id   = item.get("call_id")
                            fn_call_name = item.get("name")
                            fn_call_args_buf = ""

                    # Accumulate function arguments
                    elif t == "response.function_call_arguments.delta":
                        fn_call_args_buf += msg.get("delta", "")

                    # Execute function and send result back
                    elif t == "response.function_call_arguments.done":
                        try:
                            args = json.loads(fn_call_args_buf or "{}")
                        except Exception:
                            args = {}
                        result = _run_tool(fn_call_name, args, session_id)
                        logger.info(f"Tool {fn_call_name}({args}) → {result}")

                        await openai_ws.send(json.dumps({
                            "type": "conversation.item.create",
                            "item": {
                                "type":    "function_call_output",
                                "call_id": fn_call_id,
                                "output":  result,
                            }
                        }))
                        await openai_ws.send(json.dumps({"type": "response.create"}))

                        # Reset
                        fn_call_id = fn_call_name = None
                        fn_call_args_buf = ""

                    elif t == "error":
                        logger.error(f"OpenAI Realtime error: {msg}")

            await asyncio.gather(from_twilio(), from_openai())

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as exc:
        logger.error(f"Voice WebSocket error [{session_id}]: {exc}")
        try:
            await websocket.close()
        except Exception:
            pass
