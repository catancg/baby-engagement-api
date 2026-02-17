import os
import time
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone

from sqlalchemy import text
from app.db.session import SessionLocal

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Tienda")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")

def render_email(template_key: str, payload: dict) -> tuple[str, str]:
    # payload will contain dynamic values (like email later)

    email = payload.get("email", "")

    if template_key == "weekly_promo_v1":
        subject = "Beneficios exclusivos para vos en Pika Pika 🎁"

        body = f"""¡Hola! 👋

Esta semana tenemos beneficios especiales pensados para vos y tu bebé 💕

🎁 Presentando este email en el local accedés a descuentos exclusivos
y recomendaciones personalizadas según la etapa de tu bebé.

Nos encanta recibirte, ayudarte a elegir y que puedas ver los productos en persona.
¡Te esperamos en la tienda!

📍 Podés pasar cuando quieras dentro del horario habitual.

— — — — — — — — — — — — — — — —
Si preferís no recibir más mensajes, podés darte de baja acá:
http://127.0.0.1:8000/unsubscribe?channel=email&value={email}
"""

        return subject, body

    return "Novedades", "Hola!"

def send_smtp(to_email: str, subject: str, body: str):
    msg = EmailMessage()
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)

def fetch_next_batch(db, batch_size: int = 25):
    # Lock rows so multiple workers can run safely.
    rows = db.execute(text("""
        select mo.id, mo.template_key, ci.value as to_email
        from message_outbox mo
        join customer_identities ci on ci.id = mo.to_identity_id
        where mo.status = 'queued'
          and mo.channel = 'email'
          and mo.scheduled_for <= now()
        order by mo.created_at
        for update skip locked
        limit :limit
    """), {"limit": batch_size}).fetchall()
    return rows

def mark_sent(db, outbox_id):
    db.execute(text("""
        update message_outbox
        set status = 'sent',
            sent_at = now()
        where id = :id
    """), {"id": outbox_id})

def mark_failed(db, outbox_id, reason: str):
    db.execute(text("""
        update message_outbox
        set status = 'failed'
        where id = :id
    """), {"id": outbox_id})
    # Optional: add message_delivery table later for detailed errors/logs.

def main():
    missing = [k for k in ["SMTP_HOST","SMTP_USERNAME","SMTP_PASSWORD","SMTP_FROM_EMAIL"] if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing SMTP env vars: {missing}")

    print("Worker started. Polling outbox...")

    while True:
        db = SessionLocal()
        try:
            db.begin()
            batch = fetch_next_batch(db, batch_size=25)

            if not batch:
                db.commit()
                time.sleep(3)
                continue

            for outbox_id, template_key, to_email in batch:
                try:
                    subject, body = render_email(template_key, {"email": to_email})
                    send_smtp(to_email, subject, body)
                    mark_sent(db, outbox_id)
                    print("SENT", outbox_id, "->", to_email)
                except Exception as e:
                    mark_failed(db, outbox_id, repr(e))
                    print("FAILED", outbox_id, "->", to_email, "error:", repr(e))

            db.commit()
        except Exception as e:
            db.rollback()
            print("WORKER LOOP ERROR:", repr(e))
        finally:
            db.close()

if __name__ == "__main__":
    main()
