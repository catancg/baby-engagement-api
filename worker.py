import os
import time
import smtplib
from pathlib import Path
from email.message import EmailMessage

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import text

from app.db.session import SessionLocal

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Tienda")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")
BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")
EMAIL_SEND_MODE = os.getenv("EMAIL_SEND_MODE", "TEST").upper()
TEST_TO_EMAIL = os.getenv("TEST_TO_EMAIL", "").strip()
DRY_RUN_SEEN = set()
DRY_RUN_SLEEP_SECONDS = int(os.getenv("DRY_RUN_SLEEP_SECONDS", "10"))

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "app/templates"

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

MAPS_URL = "https://www.google.com/maps/place/Pika+pika/@-33.0094136,-58.5212939,17z/data=!3m1!4b1!4m6!3m5!1s0x95baa96e7a3c9b9b:0xe3dcf248c61b47ba!8m2!3d-33.0094136!4d-58.5212939!16s%2Fg%2F11s5zh8086?entry=ttu&g_ep=EgoyMDI2MDIyNS4wIKXMDSoASAFQAw%3D%3D"
WHATSAPP_URL = "https://wa.me/5493446586123"
INSTAGRAM_URL = "https://instagram.com/pikapikagchu"
INSTAGRAM_HANDLE = "@pikapikagchu"
FACEBOOK_URL = "https://www.facebook.com/pika.pika.73295"
ADDRESS = "Rocamora 35, Gualeguaychu, Entre Rios"
HOURS = "Lunes a Sabado"
TERMS_LINE = "Válido presentando este email en el local Pika Pika"


def render_email(template_key: str, payload: dict) -> tuple[str, str, str]:
    email = (payload.get("email") or "").strip()
    base_url = BASE_URL.rstrip("/")
    unsubscribe_url = f"{base_url}/unsubscribe?channel=email&value={email}"

    if template_key == "weekly_promo_v1":
        logo_url = f"{base_url}/static/logo.png"
        subject = "Beneficios exclusivos para vos en Pika Pika"
        text_body = (
            "Hola!\n\n"
            "Queremos invitarte a nuestro local. Presentando este email tenes un descuento especial.\n\n"
            f"Ubicacion: {MAPS_URL}\n"
            f"WhatsApp: {WHATSAPP_URL}\n"
            f"Instagram: {INSTAGRAM_URL}\n\n"
            f"Darte de baja:\n{unsubscribe_url}\n"
        )
        template = jinja_env.get_template("pika_pika_weekly.html")
        html_body = template.render(
            logo_url=logo_url,
            maps_url=MAPS_URL,
            whatsapp_url=WHATSAPP_URL,
            address=ADDRESS,
            hours=HOURS,
            terms_line=TERMS_LINE,
            instagram_url=INSTAGRAM_URL,
            instagram_handle=INSTAGRAM_HANDLE,
            facebook_url=FACEBOOK_URL,
            unsubscribe_url=unsubscribe_url,
        )
        return subject, text_body, html_body

    if template_key == "ai_variant_v1":
        subject = payload.get("subject_line", "Novedades de Pika Pika")
        headline = payload.get("headline", "")
        highlight_phrase = payload.get("highlight_phrase", "descuento especial")
        body_intro = payload.get("body_intro", "")
        closing_message = payload.get("closing_message", "")
        text_body = (
            f"{headline}\n\n"
            f"{highlight_phrase}\n\n"
            f"{body_intro}\n\n"
            f"{closing_message}\n\n"
            f"Darte de baja:\n{unsubscribe_url}\n"
        )
        template = jinja_env.get_template("ai_variant_email.html")
        html_body = template.render(
            logo_url=f"{base_url}/static/logo.png",
            headline=headline,
            highlight_phrase=highlight_phrase,
            body_intro=body_intro,
            block_1_emoji=payload.get("block_1_emoji", "🎁"),
            block_1_title=payload.get("block_1_title", ""),
            block_1_text=payload.get("block_1_text", ""),
            block_2_emoji=payload.get("block_2_emoji", "👶"),
            block_2_title=payload.get("block_2_title", ""),
            block_2_text=payload.get("block_2_text", ""),
            closing_message=closing_message,
            promo_image_url=payload.get("promo_image_url") or None,
            terms_line=TERMS_LINE,
            maps_url=MAPS_URL,
            whatsapp_url=WHATSAPP_URL,
            address=ADDRESS,
            hours=HOURS,
            instagram_url=INSTAGRAM_URL,
            instagram_handle=INSTAGRAM_HANDLE,
            facebook_url=FACEBOOK_URL,
            unsubscribe_url=unsubscribe_url,
        )
        return subject, text_body, html_body

    if template_key == "welcome_v1":
        name = payload.get("name", "")
        subject = f"¡Te damos la bienvenida a Pika Pika, {name}! 🐣" if name else "¡Bienvenida/o a Pika Pika! 🐣"
        logo_url = f"{base_url}/static/logo.png"
        text_body = (
            f"¡Hola {name}!\n\n"
            "Nos alegra que te hayas sumado a Pika Pika, tu tienda de artículos para bebés y juguetes en Gualeguaychu.\n\n"
            "A partir de ahora vas a recibir:\n"
            "- Descuentos exclusivos para clientes registrados\n"
            "- Novedades y nuevos productos\n"
            "- Ofertas especiales\n\n"
            f"WhatsApp: {WHATSAPP_URL}\n"
            f"Instagram: {INSTAGRAM_URL}\n\n"
            f"Si no querés recibir más correos:\n{unsubscribe_url}\n"
        )
        template = jinja_env.get_template("welcome_email.html")
        html_body = template.render(
            name=name,
            logo_url=logo_url,
            maps_url=MAPS_URL,
            whatsapp_url=WHATSAPP_URL,
            instagram_url=INSTAGRAM_URL,
            instagram_handle=INSTAGRAM_HANDLE,
            facebook_url=FACEBOOK_URL,
            unsubscribe_url=unsubscribe_url,
        )
        return subject, text_body, html_body

    if template_key == "news_v1":
        subject = payload.get("subject_line", "Novedades en Pika Pika 🛍️")
        products = payload.get("products", [])
        intro_text = payload.get("intro_text", "")
        promo_text = payload.get("promo_text", "")
        text_body = f"{intro_text}\n\n"
        for p in products:
            text_body += f"- {p.get('name', '')}"
            if p.get("price"):
                text_body += f" — {p['price']}"
            text_body += "\n"
        if promo_text:
            text_body += f"\n{promo_text}\n"
        text_body += f"\nWhatsApp: {WHATSAPP_URL}\nInstagram: {INSTAGRAM_URL}\n\nDarte de baja:\n{unsubscribe_url}\n"
        template = jinja_env.get_template("news_email.html")
        html_body = template.render(
            logo_url=f"{base_url}/static/logo.png",
            intro_text=intro_text,
            products=products,
            promo_text=promo_text,
            closing_message=payload.get("closing_message", ""),
            maps_url=MAPS_URL,
            whatsapp_url=WHATSAPP_URL,
            instagram_url=INSTAGRAM_URL,
            instagram_handle=INSTAGRAM_HANDLE,
            facebook_url=FACEBOOK_URL,
            unsubscribe_url=unsubscribe_url,
        )
        return subject, text_body, html_body

    return "Novedades", "Hola!", "<p>Hola!</p>"


def send_smtp(to_email: str, subject: str, text_body: str, html_body: str | None = None):
    msg = EmailMessage()
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(text_body)

    if html_body:
        msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)


def fetch_next_batch(db, batch_size: int = 25):
    rows = db.execute(text("""
        select mo.id, mo.template_key, ci.value as to_email, mo.payload
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


def main():
    missing = [k for k in ["SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM_EMAIL"] if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing SMTP env vars: {missing}")
    print(BASE_DIR, TEMPLATES_DIR)
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

            test_sample_sent = False
            for outbox_id, template_key, to_email, payload in batch:
                original_to = to_email
                try:
                    render_payload = dict(payload or {})
                    render_payload["email"] = original_to
                    subject, text_body, html_body = render_email(template_key, render_payload)

                    if EMAIL_SEND_MODE == "DRY_RUN":
                        print("DRY_RUN -> Would send", outbox_id, "to:", original_to, "template:", template_key)
                        DRY_RUN_SEEN.add(outbox_id)
                        continue

                    if EMAIL_SEND_MODE == "TEST":
                        if not TEST_TO_EMAIL:
                            raise RuntimeError("EMAIL_SEND_MODE=TEST but TEST_TO_EMAIL is not set")

                        if test_sample_sent:
                            mark_sent(db, outbox_id)
                            print("TEST SKIP (sample already sent) ->", original_to)
                            continue

                        to_email = TEST_TO_EMAIL
                        subject = f"[TEST] {subject}"
                        text_body = (
                            "MODO PRUEBA\n"
                            f"Este email originalmente iba dirigido a: {original_to}\n\n"
                            + text_body
                        )

                        if html_body:
                            html_body = (
                                "<div style='padding:12px;background:#fff3cd;border:1px solid #ffeeba;"
                                "border-radius:8px;font-family:Arial,Helvetica,sans-serif;font-size:12px;'>"
                                f"MODO PRUEBA<br>Original: {original_to}"
                                "</div>"
                                + html_body
                            )

                    send_smtp(to_email, subject, text_body, html_body=html_body)
                    mark_sent(db, outbox_id)
                    print("SENT", outbox_id, "->", to_email, "(original:", original_to, ")")
                    if EMAIL_SEND_MODE == "TEST":
                        test_sample_sent = True

                except Exception as e:
                    mark_failed(db, outbox_id, repr(e))
                    print("FAILED", outbox_id, "->", original_to, "error:", repr(e))

            db.commit()
            if EMAIL_SEND_MODE == "DRY_RUN":
                time.sleep(DRY_RUN_SLEEP_SECONDS)

        except Exception as e:
            db.rollback()
            print("WORKER LOOP ERROR:", repr(e))
        finally:
            db.close()


if __name__ == "__main__":
    main()
