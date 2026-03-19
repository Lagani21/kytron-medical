from fastapi import APIRouter
from fastapi.responses import JSONResponse
from models import VoiceCallRequest
from session_store import get_session
from services.voice_service import initiate_voice_call

router = APIRouter()


@router.post("/api/voice/initiate")
async def voice_initiate(req: VoiceCallRequest):
    try:
        session = get_session(req.session_id)
        if not session:
            return JSONResponse(status_code=404, content={"error": "Session not found"})
        history = session.get("conversation_history", [])
        patient = session.get("patient_info", {})
        doctor = session.get("matched_doctor")
        booked_slot = session.get("booked_slot")
        result = await initiate_voice_call(
            req.phone_number, req.session_id,
            history=history,
            patient=patient,
            matched_doctor=doctor,
            booked_slot=booked_slot,
        )
        return result
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
