import requests
import time
import subprocess

# Trigger a new login
login_url = "http://127.0.0.1:8000/admin/auth/login"
# OAuth2PasswordRequestForm uses form data
data = {
    "username": "admin@weighbridge.com",
    "password": "Admin123!"
}
requests.post(login_url, data=data)

# Wait a bit for logs to update
time.sleep(2)

# Read the last few lines of app_output.log to find the NEW OTP
try:
    with open("app_output.log", "r") as f:
        lines = f.readlines()
        for line in reversed(lines):
            if "[DEV MODE] OTP for admin@weighbridge.com:" in line:
                otp = line.split(":")[-1].strip()
                print(f"FOUND_OTP:{otp}")
                break
except Exception as e:
    print(f"Error reading logs: {e}")
