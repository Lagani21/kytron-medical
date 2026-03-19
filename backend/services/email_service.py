import asyncio
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def _build_email(to_email, first_name, doctor_name, date, time, address, from_addr):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Appointment Confirmed — {doctor_name} on {date} at {time}"
    msg["From"] = f"Kyron Medical <{from_addr}>"
    msg["To"] = to_email

    plain = (
        f"Hi {first_name},\n\n"
        f"Your appointment has been confirmed!\n\n"
        f"Doctor:   {doctor_name}\n"
        f"Date:     {date}\n"
        f"Time:     {time}\n"
        f"Location: {address}\n\n"
        f"If you need to reschedule, please contact us.\n\n"
        f"— Kyron Medical Team"
    )
    html = f"""
<html><body style="font-family:sans-serif;color:#111;max-width:480px;margin:auto">
  <h2 style="color:#2563EB">Appointment Confirmed ✅</h2>
  <p>Hi <strong>{first_name}</strong>,</p>
  <p>Your appointment has been confirmed.</p>
  <table style="border-collapse:collapse;width:100%;margin:16px 0">
    <tr><td style="padding:8px 0;color:#555">Doctor</td><td style="padding:8px 0"><strong>{doctor_name}</strong></td></tr>
    <tr><td style="padding:8px 0;color:#555">Date</td><td style="padding:8px 0">{date}</td></tr>
    <tr><td style="padding:8px 0;color:#555">Time</td><td style="padding:8px 0">{time}</td></tr>
    <tr><td style="padding:8px 0;color:#555">Location</td><td style="padding:8px 0">{address}</td></tr>
  </table>
  <p style="color:#555;font-size:13px">If you need to reschedule, please contact us.</p>
  <p style="color:#888;font-size:12px">— Kyron Medical Team</p>
</body></html>
"""
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))
    return msg


def _send_sync(to_email, first_name, doctor_name, date, time, address):
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_password:
        logger.info(f"[STUB] Sending confirmation email to {to_email}")
        logger.info(f"  Patient: {first_name}, Doctor: {doctor_name}, {date} at {time}, {address}")
        return {"status": "stub"}

    msg = _build_email(to_email, first_name, doctor_name, date, time, address, gmail_user)
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, to_email, msg.as_string())

    logger.info(f"[EMAIL] Sent confirmation to {to_email}")
    return {"status": "sent", "to": to_email}


def _build_refill_email(to_email, first_name, medication, dosage, prescriber, from_addr):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Prescription Refill Request Received — {medication}"
    msg["From"] = f"Kyron Medical <{from_addr}>"
    msg["To"] = to_email

    plain = (
        f"Hi {first_name},\n\n"
        f"We've received your prescription refill request.\n\n"
        f"Medication:  {medication}\n"
        f"Dosage:      {dosage}\n"
        f"Prescriber:  {prescriber}\n"
        f"Status:      Pending review\n\n"
        f"Your doctor will review the request within 1–2 business days.\n"
        f"You'll be contacted if any additional information is needed.\n\n"
        f"— Kyron Medical Team"
    )
    html = f"""
<html><body style="font-family:sans-serif;color:#111;max-width:480px;margin:auto">
  <h2 style="color:#2563EB">Refill Request Received</h2>
  <p>Hi <strong>{first_name}</strong>,</p>
  <p>We've received your prescription refill request and it is now pending review.</p>
  <table style="border-collapse:collapse;width:100%;margin:16px 0">
    <tr><td style="padding:8px 0;color:#555">Medication</td><td style="padding:8px 0"><strong>{medication}</strong></td></tr>
    <tr><td style="padding:8px 0;color:#555">Dosage</td><td style="padding:8px 0">{dosage}</td></tr>
    <tr><td style="padding:8px 0;color:#555">Prescriber</td><td style="padding:8px 0">{prescriber}</td></tr>
    <tr><td style="padding:8px 0;color:#555">Status</td><td style="padding:8px 0">Pending review</td></tr>
  </table>
  <p>Your doctor will review within <strong>1–2 business days</strong>. You'll be contacted if anything else is needed.</p>
  <p style="color:#888;font-size:12px">— Kyron Medical Team</p>
</body></html>
"""
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))
    return msg


def _send_refill_sync(to_email, first_name, medication, dosage, prescriber):
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_password:
        logger.info(f"[STUB] Sending refill confirmation email to {to_email}")
        logger.info(f"  Patient: {first_name}, Medication: {medication} {dosage}, Prescriber: {prescriber}")
        return {"status": "stub"}

    msg = _build_refill_email(to_email, first_name, medication, dosage, prescriber, gmail_user)
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, to_email, msg.as_string())

    logger.info(f"[EMAIL] Sent refill confirmation to {to_email}")
    return {"status": "sent", "to": to_email}


async def send_refill_email(to_email, first_name, medication, dosage, prescriber):
    try:
        return await asyncio.to_thread(
            _send_refill_sync, to_email, first_name, medication, dosage, prescriber
        )
    except Exception as exc:
        logger.error(f"[EMAIL] Failed to send refill email to {to_email}: {exc}")
        return {"status": "error", "message": str(exc)}


async def send_confirmation_email(to_email, first_name, doctor_name, date, time, address):
    try:
        return await asyncio.to_thread(
            _send_sync, to_email, first_name, doctor_name, date, time, address
        )
    except Exception as exc:
        logger.error(f"[EMAIL] Failed to send to {to_email}: {exc}")
        return {"status": "error", "message": str(exc)}
