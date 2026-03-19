import os
import re
import logging
import httpx

logger = logging.getLogger(__name__)

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID")


def _to_e164(phone: str) -> str:
    """Normalize phone to E.164. Assumes US number if no country code."""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("1") and len(digits) == 11:
        return f"+{digits}"
    if len(digits) == 10:
        return f"+1{digits}"
    return f"+{digits}"


def _build_system_prompt(patient: dict, history: list, matched_doctor, booked_slot) -> str:
    name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip() or "the patient"
    reason = patient.get("reason", "their medical concern")

    lines = [
        "You are a Kyron Medical voice assistant. You are continuing a conversation that began "
        "on the Kyron Medical web chat. Pick up exactly where the conversation left off — "
        "do not re-introduce yourself at length or repeat information already covered.",
        "",
        f"Patient name: {name}",
        f"Reason for visit: {reason}",
    ]

    if matched_doctor:
        lines.append(f"Matched specialist: Dr. {matched_doctor.capitalize()}")
    if booked_slot:
        lines.append(f"Appointment booked: {booked_slot}")

    if history:
        lines += ["", "--- Web chat history ---"]
        for msg in history:
            role_label = "Patient" if msg.get("role") == "user" else "Assistant"
            lines.append(f"{role_label}: {msg.get('content', '')}")
        lines.append("--- End of web chat history ---")

    lines += [
        "",
        "Continue helping the patient. If they have already booked an appointment, "
        "confirm the details. Otherwise help them find a specialist and schedule a time.",
    ]

    return "\n".join(lines)


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

    e164_phone = _to_e164(phone_number)
    name = patient.get("first_name", "")
    first_message = (
        f"Hi {name}, this is your Kyron Medical assistant. "
        "I'm picking up right where we left off in our chat. How can I continue helping you?"
        if name else
        "Hi, this is your Kyron Medical assistant. "
        "I'm picking up right where we left off in our chat. How can I continue helping you?"
    )

    system_prompt = _build_system_prompt(patient, history, matched_doctor, booked_slot)

    try:
        payload = {
            "assistantId": VAPI_ASSISTANT_ID,
            "customer": {
                "number": e164_phone,
            },
            "assistantOverrides": {
                "firstMessage": first_message,
                "model": {
                    "messages": [
                        {"role": "system", "content": system_prompt}
                    ]
                },
                "variableValues": {
                    "session_id": session_id,
                    "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                },
            },
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.vapi.ai/call/phone",
                headers={
                    "Authorization": f"Bearer {VAPI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()

        logger.info(f"Vapi call initiated: {data.get('id')} for session {session_id}")
        return {
            "status": "initiated",
            "call_id": data.get("id"),
            "session_id": session_id,
        }

    except httpx.HTTPStatusError as exc:
        logger.error(f"Vapi API error {exc.response.status_code}: {exc.response.text}")
        return {"status": "error", "session_id": session_id, "message": exc.response.text}
    except Exception as exc:
        logger.error(f"Voice service error: {exc}")
        return {"status": "error", "session_id": session_id, "message": str(exc)}
