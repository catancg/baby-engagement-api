import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

host = os.getenv("SMTP_HOST")
port = int(os.getenv("SMTP_PORT", "587"))
username = os.getenv("SMTP_USERNAME")
password = os.getenv("SMTP_PASSWORD")
from_name = os.getenv("SMTP_FROM_NAME", "Tienda")
from_email = os.getenv("SMTP_FROM_EMAIL")
to_email = os.getenv("TEST_TO_EMAIL") or from_email

print("Connecting to:", host)

msg = EmailMessage()
msg["From"] = f"{from_name} <{from_email}>"
msg["To"] = to_email
msg["Subject"] = "Test del sistema automático 🍼"
msg.set_content("¡Hola! Este es un correo de prueba del sistema automático.")

try:
    with smtplib.SMTP(host, port, timeout=20) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(msg)

    print("EMAIL SENT SUCCESSFULLY ✔")

except Exception as e:
    print("ERROR SENDING EMAIL ❌")
    print(type(e).__name__, str(e))
