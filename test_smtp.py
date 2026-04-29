import os
from dotenv import load_dotenv
import smtplib

load_dotenv()

host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
port = int(os.environ.get("SMTP_PORT", 587))
user = os.environ.get("SMTP_USER")
password = os.environ.get("SMTP_PASS")
print(f"Password being used: {repr(password)}")

try:
    print(f"Connecting to {host}:{port} as {user}...")
    server = smtplib.SMTP(host, port)
    server.starttls()
    server.login(user, password)
    print("SUCCESS: SMTP Authentication successful!")
    server.quit()
except smtplib.SMTPAuthenticationError as e:
    print(f"ERROR: Authentication failed. {e}")
except Exception as e:
    print(f"ERROR: An unexpected error occurred. {e}")
