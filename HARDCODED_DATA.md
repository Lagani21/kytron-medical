# Kytron Medical — Hardcoded Data Reference

This document lists all static/demo data currently hardcoded in the codebase. Update these before deploying to production.

---

## 1. Doctors (`backend/data/doctors.py`)

| Field | Dr. Sarah Chen | Dr. Marcus Webb | Dr. Priya Nair | Dr. James Okafor |
|---|---|---|---|---|
| **ID** | `chen` | `webb` | `nair` | `okafor` |
| **Specialty** | Cardiology | Orthopedics | Dermatology | Neurology |
| **Office** | 120 Heart Way, Suite 300, San Francisco, CA 94102 | 500 Joint Blvd, Suite 210, San Francisco, CA 94103 | 88 Skin Street, Suite 150, San Francisco, CA 94104 | 200 Neuro Ave, Suite 400, San Francisco, CA 94105 |
| **Phone** | (415) 555-0101 | (415) 555-0202 | (415) 555-0303 | (415) 555-0404 |
| **Hours** | Mon–Fri 8am–5pm | Mon–Fri 9am–6pm | Mon–Fri 8am–4pm | Mon–Fri 7am–4pm |

### Doctor Specialty Keywords (used for routing)
- **Chen (Cardiology):** heart, cardiology, chest pain, palpitation, blood pressure, hypertension, shortness of breath, cardiac, arrhythmia
- **Webb (Orthopedics):** knee, hip, shoulder, back, joint, bone, fracture, arthritis, spine, wrist, ankle, elbow, sprain, torn, tendon, ligament
- **Nair (Dermatology):** skin, rash, acne, mole, eczema, psoriasis, itching, hives, lesion
- **Okafor (Neurology):** headache, migraine, dizziness, nerve, numbness, seizure, tremor, vertigo, tingling

---

## 2. Appointment Slots (`backend/data/doctors.py`)

All doctors share the same 4 daily time slots:

```
9:00 AM   |   10:30 AM   |   2:00 PM   |   3:30 PM
```

---

## 3. Practice / Company Info (`backend/services/ai_service.py`)

| Field | Value |
|---|---|
| **Practice Name** | Kytron Medical |
| **Main / Billing Phone** | (415) 555-0100 |
| **Accepted Insurance** | Aetna, BlueCross BlueShield, Cigna, United Health, Medicare, Medicaid |
| **Transit** | 5-minute walk from nearest BART/Muni station |

---

## 4. Prescription Refill SLA (`backend/services/sms_service.py`, `voice_service.py`, `email_service.py`)

Refill requests are promised a review turnaround of **1–2 business days** — mentioned in SMS confirmations, email confirmations, and the voice assistant script.

---

## 5. Emergency Keywords (`backend/services/ai_service.py`)

The AI refuses to advise and redirects to 911 when it detects:
```
emergency, 911, can't breathe, cannot breathe, chest pain, unconscious, bleeding heavily
```

---

## 6. Email / SMS Sender Branding (`backend/services/email_service.py`, `sms_service.py`)

- **From name:** `Kytron Medical <{SMTP_FROM_ADDRESS}>`
- **Email signature:** `— Kytron Medical Team`
- **SMS opt-out footer:** `Reply STOP to opt out.`

---

## 7. Test Data (`backend/routers/appointments.py`)

A `/test-email` route uses hardcoded values for development:
- Date: `2026-01-01`
- Time: `9:00 AM`
- Address: `123 Test St`

Remove or gate this endpoint before going to production.
