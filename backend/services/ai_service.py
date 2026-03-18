import asyncio
import re
import os
import httpx
from datetime import datetime
from data.doctors import DOCTORS
from session_store import get_session, update_session

_SYSTEM_PROMPT = """You are a medical intake assistant. Given a patient's symptom description, determine which specialist they should see.

Available specialists:
- chen: Cardiology — heart problems, chest pain, palpitations, high blood pressure, shortness of breath, irregular heartbeat
- webb: Orthopedics — bone, joint, or muscle issues, back pain, knee/shoulder/hip pain, fractures, sprains, arthritis
- nair: Dermatology — skin conditions, rashes, acne, moles, eczema, psoriasis, itching, hives
- okafor: Neurology — headaches, migraines, dizziness, nerve pain, numbness, seizures, tremors, vertigo

Reply with ONLY one of these exact IDs: chen, webb, nair, okafor
Reply with ONLY "none" if the description is too vague, unrelated to these specialties, or needs more clarification to decide."""


async def match_doctor(text: str) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": text},
                    ],
                    "max_tokens": 10,
                    "temperature": 0,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"].strip().lower()
            return result if result in DOCTORS else None
    except Exception:
        return None


async def stream_response(text: str):
    words = text.split()
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")
        await asyncio.sleep(0.04)


async def get_ai_response(session_id: str, user_message: str):
    session = get_session(session_id)
    msg_lower = user_message.lower()
    patient = session.get("patient_info", {})
    first_name = patient.get("first_name", "there")

    # Check for medical advice keywords
    medical_advice_keywords = [
        "diagnose", "diagnosis", "what do i have", "is it serious",
        "should i take", "what medication", "treatment for", "cure for", "do i have",
    ]
    if any(kw in msg_lower for kw in medical_advice_keywords):
        async for chunk in stream_response(
            "I'm not able to provide medical advice. Please consult your doctor directly "
            "for any medical concerns. I can help you schedule an appointment with the right specialist."
        ):
            yield chunk
        return

    # Prescription refill
    if "prescription" in msg_lower or "refill" in msg_lower or "medication refill" in msg_lower:
        async for chunk in stream_response(
            "For prescription refills, please call your doctor's office directly. "
            "I can help you schedule an in-person appointment if needed."
        ):
            yield chunk
        return

    # Try to match a doctor from the current message first; fall back to session cache
    doctor_id = await match_doctor(user_message)
    if doctor_id:
        update_session(session_id, matched_doctor=doctor_id)
    else:
        doctor_id = session.get("matched_doctor")

    doctor = DOCTORS.get(doctor_id) if doctor_id else None

    # Affirmative response when doctor already matched → show slots
    # Use word-boundary matching so "ok" in "book" doesn't trigger this
    _AFFIRMATIVE_RE = re.compile(
        r'\b(yes|sure|ok|okay|yeah|yep|please)\b|go ahead|sounds good|show me'
    )
    if doctor and _AFFIRMATIVE_RE.search(msg_lower):
        available_slots = [s for s in doctor["slots"] if s["status"] == "available"]
        slots_to_show = available_slots[:5]
        if slots_to_show:
            slot_lines = "\n".join([f"• {s['date']} at {s['time']}" for s in slots_to_show])
            response = (
                f"Here are available slots with {doctor['name']} ({doctor['specialty']}):\n\n"
                f"{slot_lines}\n\nJust click a slot below to book it!"
            )
        else:
            response = f"I'm sorry, there are no available slots for {doctor['name']} at the moment. Would you like to check back later?"
        async for chunk in stream_response(response):
            yield chunk
        return

    # Office hours / address
    if any(kw in msg_lower for kw in ["hours", "address", "location", "office", "where"]):
        if doctor:
            response = (
                f"Dr. {doctor['name'].split()[-1]}'s office is located at {doctor['office']}. "
                f"Office hours are {doctor['hours']}. "
                f"You can also reach them at {doctor['phone']}."
            )
        else:
            response = (
                "Could you tell me more about your symptoms so I can match you with the right specialist? "
                "Then I can share their office details."
            )
        async for chunk in stream_response(response):
            yield chunk
        return

    # Show available slots
    if any(kw in msg_lower for kw in ["available", "slot", "appointment", "schedule", "show", "see", "when", "time"]):
        if not doctor:
            doctor_id = await match_doctor(user_message)
            if not doctor_id:
                async for chunk in stream_response(
                    "I'd like to help you schedule an appointment. Could you describe your symptoms "
                    "so I can match you with the right specialist?"
                ):
                    yield chunk
                return
            update_session(session_id, matched_doctor=doctor_id)
            doctor = DOCTORS[doctor_id]

        # Filter by day of week if mentioned
        days = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4}
        target_day = None
        for day_name, day_num in days.items():
            if day_name in msg_lower:
                target_day = day_num
                break

        available_slots = [s for s in doctor["slots"] if s["status"] == "available"]
        if target_day is not None:
            available_slots = [
                s for s in available_slots
                if datetime.strptime(s["date"], "%Y-%m-%d").weekday() == target_day
            ]

        slots_to_show = available_slots[:5]

        if not slots_to_show:
            day_names = list(days.keys())
            day_suffix = (
                f" on {day_names[target_day].capitalize()}s" if target_day is not None else ""
            )
            response = (
                f"I'm sorry, there are no available slots{day_suffix} "
                f"for {doctor['name']}. Would you like to check other days?"
            )
            async for chunk in stream_response(response):
                yield chunk
            return

        slot_lines = "\n".join([f"• {s['date']} at {s['time']}" for s in slots_to_show])
        response = (
            f"Here are available slots with {doctor['name']} ({doctor['specialty']}):\n\n"
            f"{slot_lines}\n\nJust click a slot below to book it!"
        )
        async for chunk in stream_response(response):
            yield chunk
        return

    # Book a slot
    if "book" in msg_lower or "confirm" in msg_lower:
        # Try to find date pattern YYYY-MM-DD
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", user_message)
        # Try to find time pattern like "9:00 AM"
        time_match = re.search(r"\d{1,2}:\d{2}\s*(?:AM|PM)", user_message, re.IGNORECASE)

        if date_match and time_match and doctor:
            slot_date = date_match.group()
            slot_time = time_match.group().upper().strip()

            # Find and book the slot
            booked = False
            for slot in doctor["slots"]:
                if (
                    slot["date"] == slot_date
                    and slot["time"].upper().strip() == slot_time
                    and slot["status"] == "available"
                ):
                    slot["status"] = "booked"
                    booked = True
                    update_session(
                        session_id,
                        booked_slot={"date": slot_date, "time": slot_time, "doctor_id": doctor_id},
                    )
                    break

            if booked:
                from services.email_service import send_confirmation_email
                from services.sms_service import send_confirmation_sms

                patient = session["patient_info"]
                email_result = await send_confirmation_email(
                    patient["email"],
                    patient["first_name"],
                    doctor["name"],
                    slot_date,
                    slot_time,
                    doctor["office"],
                )
                if session.get("sms_opt_in"):
                    await send_confirmation_sms(
                        patient["phone"], doctor["name"], slot_date, slot_time
                    )

                if email_result.get("status") in ("sent", "stub"):
                    email_line = f"Email confirmation sent to: {patient['email']}"
                else:
                    email_line = f"Note: Email confirmation could not be sent ({email_result.get('message', 'unknown error')})"
                sms_line = (
                    f"\nText confirmation sent to: {patient['phone']}"
                    if session.get("sms_opt_in")
                    else ""
                )
                response = (
                    f"✅ Your appointment has been confirmed!\n\n"
                    f"Doctor: {doctor['name']}\n"
                    f"Specialty: {doctor['specialty']}\n"
                    f"Date: {slot_date}\n"
                    f"Time: {slot_time}\n"
                    f"Location: {doctor['office']}\n\n"
                    f"{email_line}{sms_line}"
                )
                async for chunk in stream_response(response):
                    yield chunk
                return
            else:
                async for chunk in stream_response(
                    f"I'm sorry, that slot is no longer available. "
                    f"Let me show you other options for {doctor['name']}."
                ):
                    yield chunk
                return
        else:
            async for chunk in stream_response(
                "I'd be happy to book that for you. Could you please confirm the date and time you'd like?"
            ):
                yield chunk
            return

    # General symptom matching
    if doctor_id:
        update_session(session_id, matched_doctor=doctor_id)
        doctor = DOCTORS[doctor_id]
        response = (
            f"Based on what you've described, I'd recommend seeing {doctor['name']}, "
            f"our {doctor['specialty']} specialist. They're experts in cases like yours.\n\n"
            f"Would you like to see available appointment slots with {doctor['name']}?"
        )
    else:
        response = (
            f"I understand you're experiencing some health concerns, {first_name}. "
            "To connect you with the right specialist, could you describe your symptoms in more detail? "
            "For example, are you experiencing any pain, discomfort, or specific issues?"
        )

    async for chunk in stream_response(response):
        yield chunk
