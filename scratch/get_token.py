import requests

# Step 1: Login to trigger OTP (if needed, but logs show it's already triggered)
# Step 2: Verify OTP
url = "http://127.0.0.1:8000/admin/auth/verify-otp"
payload = {
    "email": "admin@weighbridge.com",
    "otp": "831957"
}

try:
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print(response.json().get("access_token"))
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Failed to connect: {e}")
