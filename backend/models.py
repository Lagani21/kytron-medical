from pydantic import BaseModel


class PatientIntake(BaseModel):
    first_name: str
    last_name: str
    dob: str
    phone: str
    email: str
    reason: str
    sms_opt_in: bool = False


class ChatMessage(BaseModel):
    session_id: str
    message: str
    role: str = "user"


class BookingRequest(BaseModel):
    session_id: str
    doctor_id: str
    slot_date: str
    slot_time: str


class VoiceCallRequest(BaseModel):
    session_id: str
    phone_number: str


class IntakeResponse(BaseModel):
    session_id: str
    message: str


class BookingConfirmationResponse(BaseModel):
    confirmed: bool
    doctor_name: str
    specialty: str
    date: str
    time: str
    address: str
    phone: str
