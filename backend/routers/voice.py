import asyncio
import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from models import VoiceCallRequest
from session_store import get_session, update_session
from services.voice_service import initiate_voice_call, build_assistant_config
from data.doctors import DOCTORS

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── 1. Initiate VAPI call ────────────────────────────────────────────────────

@router.post("/api/voice/initiate")
async def voice_initiate(req: VoiceCallRequest):
    session = get_session(req.session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Session not found"})

    doctor_id = session.get("matched_doctor")
    if not doctor_id:
        reason = session.get("patient_info", {}).get("reason", "")
        if reason:
            from services.ai_service import match_doctor
            doctor_id = await match_doctor(reason)
            if doctor_id:
                update_session(req.session_id, matched_doctor=doctor_id)

    doctor = DOCTORS.get(doctor_id) if doctor_id else None
    matched_doctor_name = f"{doctor['name']} ({doctor['specialty']})" if doctor else None

    # Fetch real available slots so the AI never hallucinates dates/times
    available_slots = None
    if doctor and not session.get("booked_slot"):
        available_slots = [
            {"date": s["date"], "time": s["time"]}
            for s in doctor["slots"]
            if s["status"] == "available"
        ][:6]

    # Serialize current chat context as a snapshot so inbound callbacks can resume it
    update_session(req.session_id, voice_snapshot={
        "matched_doctor": doctor_id,
        "matched_doctor_name": matched_doctor_name,
        "booked_slot": session.get("booked_slot"),
        "refill_state": session.get("refill_state"),
        "refill_medication": session.get("refill_medication"),
        "refill_dosage": session.get("refill_dosage"),
        "refill_prescriber": session.get("refill_prescriber"),
        "conversation_history": session.get("conversation_history", []),
        "available_slots": available_slots,
        "doctor_info": {k: v for k, v in (doctor or {}).items() if k != "slots"} if doctor else None,
    })

    result = await initiate_voice_call(
        req.phone_number,
        req.session_id,
        history=session.get("conversation_history", []),
        patient=session.get("patient_info", {}),
        matched_doctor=matched_doctor_name,
        booked_slot=session.get("booked_slot"),
        available_slots=available_slots,
        doctor_info=doctor,
    )
    return result


# ─── 2. VAPI end-of-call webhook ─────────────────────────────────────────────

@router.post("/api/voice/end-of-call")
async def voice_end_of_call(request: Request):
    body = await request.json()
    msg  = body.get("message", {})

    if msg.get("type") != "end-of-call-report":
        return {"status": "ignored"}

    structured = msg.get("analysis", {}).get("structuredData", {})
    call       = msg.get("call", {})
    session_id = call.get("metadata", {}).get("session_id") or \
                 (call.get("customer", {}).get("number") and
                  get_session_id_by_phone(call["customer"]["number"]))

    if not structured.get("appointment_confirmed"):
        logger.info("End-of-call: no appointment confirmed")
        return {"status": "no_booking"}

    doctor_id = structured.get("doctor_id")
    slot_date = structured.get("date")
    slot_time = structured.get("time")
    doctor    = DOCTORS.get(doctor_id) if doctor_id else None

    if not session_id or not doctor or not slot_date or not slot_time:
        logger.warning(
            f"End-of-call: missing data — session={session_id} "
            f"doctor={doctor_id} date={slot_date} time={slot_time}"
        )
        return {"status": "missing_data"}

    session = get_session(session_id)
    if not session:
        logger.warning(f"End-of-call: session {session_id} not found")
        return {"status": "session_not_found"}

    # Mark slot as booked
    for slot in doctor["slots"]:
        if slot["date"] == slot_date and slot["time"] == slot_time and slot["status"] == "available":
            slot["status"] = "booked"
            update_session(session_id, booked_slot={"date": slot_date, "time": slot_time, "doctor_id": doctor_id})
            break

    # Send confirmation email + SMS
    patient = session.get("patient_info", {})
    from services.email_service import send_confirmation_email
    from services.sms_service import send_confirmation_sms

    await send_confirmation_email(
        patient.get("email", ""), patient.get("first_name", ""),
        doctor["name"], slot_date, slot_time, doctor["office"]
    )
    if session.get("sms_opt_in"):
        await send_confirmation_sms(patient.get("phone", ""), doctor["name"], slot_date, slot_time)
        schedule_followup(patient.get("phone", ""), doctor["name"], slot_date, slot_time, sms_opt_in=True)

    logger.info(f"End-of-call booking confirmed: {doctor['name']} {slot_date} {slot_time} → {patient.get('email')}")
    return {"status": "ok"}



# ─── 4. Post-appointment follow-up SMS ───────────────────────────────────────

async def _send_followup_sms(phone: str, doctor_name: str, date: str, time: str):
    """Fires ~24 hours after the appointment slot to check in with the patient."""
    from datetime import datetime, timedelta

    try:
        appt_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %I:%M %p")
    except ValueError:
        appt_dt = datetime.now()

    followup_dt  = appt_dt + timedelta(hours=24)
    delay_seconds = max((followup_dt - datetime.now()).total_seconds(), 60)
    await asyncio.sleep(delay_seconds)

    try:
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
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_send_followup_sms(phone, doctor_name, date, time))
        logger.info(f"Follow-up SMS scheduled for {phone} after {date} {time}")
    except RuntimeError:
        pass
