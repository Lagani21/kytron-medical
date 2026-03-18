import os
import logging
import httpx

logger = logging.getLogger(__name__)

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID")


async def initiate_voice_call(phone_number: str, session_id: str, context_summary: str):
    try:
        payload = {
            "assistantId": VAPI_ASSISTANT_ID,
            "customer": {
                "number": phone_number,
            },
            "assistantOverrides": {
                "variableValues": {
                    "context_summary": context_summary,
                    "session_id": session_id,
                }
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
