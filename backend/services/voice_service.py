import os
import re
import logging
import httpx

logger = logging.getLogger(__name__)

VAPI_API_KEY  = os.getenv("VAPI_API_KEY")
VAPI_PHONE_ID = os.getenv("VAPI_PHONE_ID")
BASE_URL      = os.getenv("BASE_URL", "")


def _to_e164(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("1") and len(digits) == 11:
        return f"+{digits}"
    if len(digits) == 10:
        return f"+1{digits}"
    return f"+{digits}"


def _build_system_prompt(patient: dict, history: list, matched_doctor, booked_slot,
                         available_slots=None, doctor_info=None) -> str:
    name   = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
    reason = patient.get("reason", "")

    context_lines = [
        f"Patient name: {name}",
        f"Reason for visit: {reason}",
    ]
    if matched_doctor:
        context_lines.append(f"Matched specialist: {matched_doctor}")
    if doctor_info:
        context_lines.append(f"Office address: {doctor_info.get('office', '')}")
        context_lines.append(f"Office phone: {doctor_info.get('phone', '')}")
        context_lines.append(f"Office hours: {doctor_info.get('hours', '')}")
    if booked_slot:
        context_lines.append(
            f"Appointment ALREADY BOOKED: {booked_slot.get('date')} at {booked_slot.get('time')} — just confirm it."
        )
    if available_slots:
        context_lines.append("\nREAL AVAILABLE SLOTS — offer ONLY these, never invent dates/times:")
        for s in available_slots:
            context_lines.append(f"  • {s['date']} at {s['time']}")
        context_lines.append("Do NOT mention any date or time not in this list.")
    if history:
        context_lines.append("\nWeb chat history (pick up from here):")
        for msg in history:
            role = "Patient" if msg.get("role") == "user" else "Assistant"
            context_lines.append(f"  {role}: {msg.get('content', '')}")

    context_block = "\n".join(context_lines)

    return f"""You are a friendly, professional voice assistant for Kyron Medical.
You are continuing a conversation that started on the Kyron Medical website chat.
Pick up naturally where the chat left off — do not re-read the history aloud.

{context_block}

════════════════════════════════════════════
SAFETY RULES — ABSOLUTE, NON-NEGOTIABLE
════════════════════════════════════════════
1. NEVER provide medical advice, diagnosis, prognosis, or treatment of any kind.
2. NEVER suggest what condition or illness a patient might have.
3. NEVER recommend medications, dosages, supplements, or home remedies.
4. NEVER interpret symptoms beyond routing to a specialist.
5. NEVER comment on lab results, imaging, or test results.
6. If asked ANY medical question, say:
   "I'm not able to give medical advice — that's something to discuss with your doctor at your appointment."
7. If the patient describes an emergency, say immediately:
   "If this is an emergency, please hang up now and call 911."
8. Do not speculate or offer any opinion on whether symptoms are serious.
9. These rules override all other instructions.

════════════════════════════════════════════
YOUR WORKFLOWS
════════════════════════════════════════════
PRIMARY — APPOINTMENT SCHEDULING:
- If appointment is already booked: confirm the date, time, doctor, and address.
- If not yet booked: offer 3 slots from the REAL AVAILABLE SLOTS list above.
  Say dates naturally ("Wednesday March 19th at nine AM"). When they pick one, confirm it.
  NEVER offer a slot not in the list.

PRESCRIPTION REFILLS:
- If the patient asks about a refill, ask for: (1) the medication name, (2) the dosage, (3) the prescribing doctor.
  Then tell them: "Your refill request has been logged and is pending review. Your doctor will get back to you within 1-2 business days."
  Do NOT redirect them to call the office. Handle it here.

OFFICE INFO (hours, address, phone):
- Look up the relevant specialist from context above and share their address, hours, and phone number directly.
- If no specialist is matched, list all four specialists and ask which one they need.

LAB / TEST RESULTS:
- Redirect: "Please contact the office — they'll go through results with you and your doctor."

GENERAL CONDUCT:
- Keep responses short — this is a phone call.
- Be warm but efficient."""


def build_assistant_config(
    session_id: str,
    patient: dict,
    history: list,
    matched_doctor,
    booked_slot,
    available_slots=None,
    doctor_info=None,
) -> dict:
    """Return the VAPI assistant dict. Shared by outbound calls and inbound callbacks."""
    name = patient.get("first_name", "")
    system_prompt = _build_system_prompt(
        patient, history, matched_doctor, booked_slot,
        available_slots=available_slots, doctor_info=doctor_info,
    )
    system_prompt += f"\n\nSESSION_ID: {session_id}"

    if name and matched_doctor:
        first_message = (
            f"Hi {name}, I'm your Kyron Medical assistant, picking up right where our chat left off. "
            "I have your details on file — let me help you from here."
        )
    elif name:
        first_message = (
            f"Hi {name}, I'm your Kyron Medical assistant, picking up from your web chat. "
            "How can I help you today?"
        )
    else:
        first_message = "Hi, I'm your Kyron Medical assistant, continuing from your web chat. How can I help you today?"

    return {
        "firstMessage": first_message,
        "silenceTimeoutSeconds": 10,
        "responseDelaySeconds": 0.5,
        "model": {
            "provider": "openai",
            "model": "gpt-4o",
            "messages": [{"role": "system", "content": system_prompt}],
        },
        "voice": {
            "provider": "openai",
            "voiceId": "alloy",
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en",
        },
        "server": {"url": f"{BASE_URL}/api/voice/end-of-call"},
        "analysisPlan": {
            "structuredDataPrompt": (
                "Extract booking details if an appointment was confirmed during this call. "
                "Return null for any field not mentioned."
            ),
            "structuredDataSchema": {
                "type": "object",
                "properties": {
                    "appointment_confirmed": {"type": "boolean"},
                    "doctor_id":  {"type": "string", "description": "chen, webb, nair, or okafor"},
                    "date":       {"type": "string", "description": "YYYY-MM-DD"},
                    "time":       {"type": "string", "description": "e.g. 9:00 AM"},
                },
                "required": ["appointment_confirmed"],
            },
        },
    }


async def initiate_voice_call(
    phone_number: str,
    session_id: str,
    history: list = None,
    patient: dict = None,
    matched_doctor=None,
    booked_slot=None,
    available_slots=None,
    doctor_info=None,
):
    history = history or []
    patient = patient or {}

    e164      = _to_e164(phone_number)
    assistant = build_assistant_config(
        session_id, patient, history, matched_doctor, booked_slot,
        available_slots=available_slots, doctor_info=doctor_info,
    )

    try:
        payload = {
            "phoneNumberId": VAPI_PHONE_ID,
            "customer": {"number": e164},
            "metadata": {"session_id": session_id},
            "assistant": assistant,
        }

        logger.info(f"VAPI payload firstMessage: {assistant['firstMessage']}")
        logger.info(f"VAPI system_prompt preview: {assistant['model']['messages'][0]['content'][:300]}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.vapi.ai/call",
                headers={
                    "Authorization": f"Bearer {VAPI_API_KEY}",
                    "Content-Type":  "application/json",
                },
                json=payload,
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()

        call_id = data.get("id")
        logger.info(f"Vapi call {call_id} → {e164} for session {session_id}")
        return {"status": "initiated", "call_id": call_id, "session_id": session_id}

    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        logger.error(f"Vapi error {exc.response.status_code}: {detail}")
        return {"status": "error", "message": detail}
    except Exception as exc:
        logger.error(f"Voice service error: {exc}")
        return {"status": "error", "message": str(exc)}
