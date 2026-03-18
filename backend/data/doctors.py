from datetime import datetime, timedelta


def _generate_slots(doctor_id, start_days_ahead=1, num_days=45):
    slots = []
    today = datetime.now().date()
    times = ["9:00 AM", "10:30 AM", "2:00 PM", "3:30 PM"]
    count = 0
    offset = start_days_ahead
    while count < num_days:
        candidate = today + timedelta(days=offset)
        offset += 1
        # Skip weekends (5=Sat, 6=Sun)
        if candidate.weekday() >= 5:
            continue
        for t in times:
            slots.append({
                "doctor_id": doctor_id,
                "date": candidate.strftime("%Y-%m-%d"),
                "time": t,
                "duration": 30,
                "status": "available",
            })
        count += 1
    return slots


DOCTORS = {
    "chen": {
        "id": "chen",
        "name": "Dr. Sarah Chen",
        "specialty": "Cardiology",
        "specialties_keywords": [
            "heart", "cardiology", "chest pain", "palpitation", "blood pressure",
            "hypertension", "shortness of breath", "cardiac", "arrhythmia",
        ],
        "office": "120 Heart Way, Suite 300, San Francisco, CA 94102",
        "phone": "(415) 555-0101",
        "hours": "Mon–Fri 8am–5pm",
        "slots": _generate_slots("chen"),
    },
    "webb": {
        "id": "webb",
        "name": "Dr. Marcus Webb",
        "specialty": "Orthopedics",
        "specialties_keywords": [
            "knee", "hip", "shoulder", "back", "joint", "bone", "orthopedic",
            "fracture", "arthritis", "spine", "wrist", "ankle", "elbow", "arm",
            "broke", "broken", "sprain", "torn", "tendon", "ligament",
        ],
        "office": "500 Joint Blvd, Suite 210, San Francisco, CA 94103",
        "phone": "(415) 555-0202",
        "hours": "Mon–Fri 9am–6pm",
        "slots": _generate_slots("webb"),
    },
    "nair": {
        "id": "nair",
        "name": "Dr. Priya Nair",
        "specialty": "Dermatology",
        "specialties_keywords": [
            "skin", "rash", "acne", "mole", "eczema", "dermatology",
            "psoriasis", "itching", "hives", "lesion",
        ],
        "office": "88 Skin Street, Suite 150, San Francisco, CA 94104",
        "phone": "(415) 555-0303",
        "hours": "Mon–Fri 8am–4pm",
        "slots": _generate_slots("nair"),
    },
    "okafor": {
        "id": "okafor",
        "name": "Dr. James Okafor",
        "specialty": "Neurology",
        "specialties_keywords": [
            "headache", "migraine", "dizziness", "nerve", "numbness", "neurology",
            "seizure", "tremor", "vertigo", "tingling",
        ],
        "office": "200 Neuro Ave, Suite 400, San Francisco, CA 94105",
        "phone": "(415) 555-0404",
        "hours": "Mon–Fri 7am–4pm",
        "slots": _generate_slots("okafor"),
    },
}
