from fastapi import APIRouter
from fastapi.responses import JSONResponse
from models import PatientIntake, BookingRequest
from session_store import create_session, get_session, update_session, register_phone
from data.doctors import DOCTORS
from services.ai_service import match_doctor
import uuid

router = APIRouter()


@router.post("/api/intake")
async def intake(data: PatientIntake):
    try:
        session_id = str(uuid.uuid4())
        create_session(session_id)
        matched_doctor = await match_doctor(data.reason) if data.reason else None
        update_session(
            session_id,
            patient_info={
                "first_name": data.first_name,
                "last_name": data.last_name,
                "dob": data.dob,
                "phone": data.phone,
                "email": data.email,
                "reason": data.reason,
            },
            matched_doctor=matched_doctor,
            sms_opt_in=data.sms_opt_in,
            intake_complete=True,
        )
        # Index phone → session so inbound calls can resume this context
        if data.phone:
            register_phone(session_id, data.phone)
        return {"session_id": session_id, "message": "Intake complete. You may now chat with the assistant."}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@router.get("/api/slots/{session_id}")
async def get_slots(session_id: str):
    try:
        session = get_session(session_id)
        if not session:
            return JSONResponse(status_code=404, content={"error": "Session not found"})
        doctor_id = session.get("matched_doctor")
        if not doctor_id:
            return {"slots": [], "message": "No doctor matched yet"}
        doctor = DOCTORS.get(doctor_id)
        if not doctor:
            return JSONResponse(status_code=404, content={"error": "Matched doctor not found"})
        available = [s for s in doctor["slots"] if s["status"] == "available"][:10]
        return {"doctor": doctor["name"], "specialty": doctor["specialty"], "slots": available}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@router.get("/api/test-email/{email}")
async def test_email(email: str):
    from services.email_service import send_confirmation_email
    result = await send_confirmation_email(
        email, "Test", "Dr. Test", "2026-01-01", "9:00 AM", "123 Test St"
    )
    return result


@router.post("/api/book")
async def book(req: BookingRequest):
    try:
        session = get_session(req.session_id)
        if not session:
            return JSONResponse(status_code=404, content={"error": "Session not found"})
        doctor = DOCTORS.get(req.doctor_id)
        if not doctor:
            return JSONResponse(status_code=404, content={"error": "Doctor not found"})
        for slot in doctor["slots"]:
            if (
                slot["date"] == req.slot_date
                and slot["time"] == req.slot_time
                and slot["status"] == "available"
            ):
                slot["status"] = "booked"
                update_session(
                    req.session_id,
                    booked_slot={"date": req.slot_date, "time": req.slot_time, "doctor_id": req.doctor_id},
                )
                return {
                    "confirmed": True,
                    "doctor_name": doctor["name"],
                    "specialty": doctor["specialty"],
                    "date": req.slot_date,
                    "time": req.slot_time,
                    "address": doctor["office"],
                    "phone": doctor["phone"],
                }
        return JSONResponse(status_code=409, content={"error": "Slot not available"})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
