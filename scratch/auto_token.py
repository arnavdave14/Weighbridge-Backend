import requests
import time
import os

# 1. Trigger Login
login_url = "http://127.0.0.1:8000/admin/auth/login"
data = {"username": "admin@weighbridge.com", "password": "Admin123!"}
requests.post(login_url, data=data)

# 2. Wait for Log to be written
time.sleep(3)

# 3. Read Log for NEW OTP
otp = None
try:
    with open("app_output.log", "r") as f:
        lines = f.readlines()
        for line in reversed(lines):
            if "[DEV MODE] OTP for admin@weighbridge.com:" in line:
                otp = line.split(":")[-1].strip()
                break
except Exception as e:
    print(f"ERROR: {e}")

if otp:
    # 4. Verify OTP to get Token
    verify_url = "http://127.0.0.1:8000/admin/auth/verify-otp"
    payload = {"email": "admin@weighbridge.com", "otp": otp}
    resp = requests.post(verify_url, json=payload)
    if resp.status_code == 200:
        print(f"TOKEN_START:{resp.json().get('access_token')}:TOKEN_END")
    else:
        print(f"VERIFY_FAILED: {resp.status_code} - {resp.text}")
else:
    print("OTP_NOT_FOUND")
