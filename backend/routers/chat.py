from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from session_store import get_session, update_session
from services.ai_service import get_ai_response

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        session = get_session(req.session_id)
        if not session:
            return JSONResponse(status_code=404, content={"error": "Session not found. Please complete intake first."})
        if not session.get("intake_complete"):
            return JSONResponse(status_code=400, content={"error": "Please complete the intake form first."})

        session["conversation_history"].append({"role": "user", "content": req.message})
        full_response = []

        async def generate():
            try:
                async for chunk in get_ai_response(req.session_id, req.message):
                    full_response.append(chunk)
                    yield chunk
            finally:
                # Persist assistant turn whether we finished normally or the client disconnected
                if full_response:
                    update_session(
                        req.session_id,
                        conversation_history=session["conversation_history"]
                        + [{"role": "assistant", "content": "".join(full_response)}],
                    )

        return StreamingResponse(generate(), media_type="text/plain")
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
