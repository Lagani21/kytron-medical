import re

SESSIONS = {}
PHONE_INDEX = {}  # normalized E.164 phone → session_id (most recent intake)


def _normalize(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}" if digits else phone


def create_session(session_id: str):
    SESSIONS[session_id] = {
        "patient_info": {},
        "conversation_history": [],
        "matched_doctor": None,
        "booked_slot": None,
        "sms_opt_in": False,
        "intake_complete": False,
    }
    return SESSIONS[session_id]


def get_session(session_id: str):
    return SESSIONS.get(session_id)


def get_session_id_by_phone(phone: str) -> str | None:
    return PHONE_INDEX.get(_normalize(phone))


def get_session_by_phone(phone: str):
    sid = get_session_id_by_phone(phone)
    return SESSIONS.get(sid) if sid else None


def register_phone(session_id: str, phone: str):
    PHONE_INDEX[_normalize(phone)] = session_id


def update_session(session_id: str, **kwargs):
    if session_id not in SESSIONS:
        return None
    for key, value in kwargs.items():
        SESSIONS[session_id][key] = value
    return SESSIONS[session_id]
