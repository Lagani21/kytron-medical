import asyncio
import logging
import os

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    """Ensure US phone numbers are in E.164 format (+1XXXXXXXXXX)."""
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return phone  # non-US or already formatted — pass through as-is


def _send_sync(to_phone, doctor_name, date, time):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")

    if not all([account_sid, auth_token, from_number]):
        logger.info(f"[STUB] Sending confirmation SMS to {to_phone}")
        logger.info(f"  Doctor: {doctor_name}, {date} at {time}")
        return {"status": "stub"}

    from twilio.rest import Client
    client = Client(account_sid, auth_token)
    normalized = _normalize_phone(to_phone)
    body = (
        f"Kyron Medical: Your appointment with {doctor_name} is confirmed for "
        f"{date} at {time}. Reply STOP to opt out."
    )
    message = client.messages.create(body=body, from_=from_number, to=normalized)
    logger.info(f"[SMS] Sent confirmation to {normalized}, SID={message.sid}")
    return {"status": "sent", "sid": message.sid}


def _send_refill_sync(to_phone, first_name, medication):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")

    if not all([account_sid, auth_token, from_number]):
        logger.info(f"[STUB] Sending refill confirmation SMS to {to_phone}")
        logger.info(f"  Patient: {first_name}, Medication: {medication}")
        return {"status": "stub"}

    from twilio.rest import Client
    client = Client(account_sid, auth_token)
    normalized = _normalize_phone(to_phone)
    body = (
        f"Kyron Medical: Your refill request for {medication} has been received "
        f"and is pending review. We'll be in touch within 1-2 business days. Reply STOP to opt out."
    )
    message = client.messages.create(body=body, from_=from_number, to=normalized)
    logger.info(f"[SMS] Sent refill confirmation to {normalized}, SID={message.sid}")
    return {"status": "sent", "sid": message.sid}


async def send_refill_sms(to_phone, first_name, medication):
    try:
        return await asyncio.to_thread(_send_refill_sync, to_phone, first_name, medication)
    except Exception as exc:
        logger.error(f"[SMS] Failed to send refill SMS to {to_phone}: {exc}")
        return {"status": "error", "message": str(exc)}


async def send_confirmation_sms(to_phone, doctor_name, date, time):
    try:
        return await asyncio.to_thread(_send_sync, to_phone, doctor_name, date, time)
    except Exception as exc:
        logger.error(f"[SMS] Failed to send to {to_phone}: {exc}")
        return {"status": "error", "message": str(exc)}
