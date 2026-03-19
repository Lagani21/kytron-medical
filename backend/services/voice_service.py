import os
import re
import logging
import httpx

logger = logging.getLogger(__name__)

VAPI_API_KEY     = os.getenv("VAPI_API_KEY")
VAPI_PHONE_ID    = os.getenv("VAPI_PHONE_ID")
VAPI_WORKFLOW_ID = os.getenv("VAPI_WORKFLOW_ID")


def _to_e164(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("1") and len(digits) == 11:
        return f"+{digits}"
    if len(digits) == 10:
        return f"+1{digits}"
    return f"+{digits}"


def _build_system_prompt(patient: dict, history: list, matched_doctor, booked_slot) -> str:
    name   = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
    reason = patient.get("reason", "")

    context_lines = [
        f"Patient name: {name}",
        f"Reason for visit: {reason}",
    ]
    if matched_doctor:
        context_lines.append(f"Matched specialist: {matched_doctor}")
    if booked_slot:
        context_lines.append(
            f"Appointment already booked: {booked_slot.get('date')} at {booked_slot.get('time')}"
        )
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
- If appointment is already booked: confirm date, time, doctor, and address.
- If not yet booked: help them select a time and confirm the booking.

PRESCRIPTION REFILLS:
- Redirect to the office phone directly.

LAB / TEST RESULTS:
- Redirect: "Please contact the office — they'll go through results with you and your doctor."

GENERAL CONDUCT:
- Keep responses short — this is a phone call.
- Be warm but efficient."""


async def initiate_voice_call(
    phone_number: str,
    session_id: str,
    history: list = None,
    patient: dict = None,
    matched_doctor=None,
    booked_slot=None,
):
    history = history or []
    patient = patient or {}

    e164         = _to_e164(phone_number)
    name         = patient.get("first_name", "")
    system_prompt = _build_system_prompt(patient, history, matched_doctor, booked_slot)

    if name and matched_doctor:
        first_message = f"Hi {name}, I'm your Kyron Medical assistant, picking up right where our chat left off. I have your details on file — let me help you get that appointment scheduled."
    elif name:
        first_message = f"Hi {name}, I'm your Kyron Medical assistant, picking up from your web chat. I just have a couple of quick questions to make sure I match you with the right specialist."
    else:
        first_message = "Hi, I'm your Kyron Medical assistant, picking up from your web chat. How can I help you today?"

    try:
        payload = {
            "phoneNumberId": VAPI_PHONE_ID,
            "workflowId":    VAPI_WORKFLOW_ID,
            "customer": {
                "number": e164,
            },
            "assistantOverrides": {
                "firstMessage": first_message,
                "variableValues": {
                    "session_id":      session_id,
                    "patient_name":    name,
                    "reason":          patient.get("reason", ""),
                    "matched_doctor":  str(matched_doctor) if matched_doctor else "",
                    "context_summary": system_prompt,
                },
            },
        }

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
