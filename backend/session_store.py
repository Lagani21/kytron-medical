SESSIONS = {}


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


def update_session(session_id: str, **kwargs):
    if session_id not in SESSIONS:
        return None
    for key, value in kwargs.items():
        SESSIONS[session_id][key] = value
    return SESSIONS[session_id]
