import requests
import json
import uuid
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
ACTIVATION_KEY = "TEST-SYNC-KEY-3B3A9E9A"
LOCAL_SECRET = "default_local_secret_change_me"

def test_sync_push():
    print(f"\n--- Testing Sync Push with Key: {ACTIVATION_KEY} ---")
    
    url = f"{BASE_URL}/push"
    headers = {
        "X-Activation-Key": ACTIVATION_KEY,
        "X-Local-Secret": LOCAL_SECRET,
        "Content-Type": "application/json"
    }
    
    # Dummy payload following the push logic in sync.py
    payload = [
        {
            "id": 101,
            "updated_at": datetime.utcnow().isoformat(),
            "payload_json": {
                "data": {
                    "truck_no": "MH12AB1234",
                    "gross": 45000.0,
                    "tare": 15000.0,
                    "material": "Iron Ore",
                    "operator": "Sync Tester"
                }
            },
            "machine_id": "TEST-DEVICE-001"
        },
        {
            "id": 102,
            "updated_at": datetime.utcnow().isoformat(),
            "payload_json": {
                "data": {
                    "truck_no": "KA01XY9876",
                    "gross": 38000.0,
                    "tare": 12000.0,
                    "material": "Bauxite",
                    "operator": "Validation Bot"
                }
            },
            "machine_id": "TEST-DEVICE-001"
        }
    ]
    
    params = {
        "table_name": "receipts" # Using receipts as it likely exists
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, params=params)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Sync Push Test Passed!")
        else:
            print("❌ Sync Push Test Failed!")
            
    except Exception as e:
        print(f"❌ Error during sync push: {e}")

def test_sync_pull():
    print(f"\n--- Testing Sync Pull with Key: {ACTIVATION_KEY} ---")
    
    url = f"{BASE_URL}/pull"
    headers = {
        "X-Activation-Key": ACTIVATION_KEY,
        "X-Local-Secret": LOCAL_SECRET
    }
    
    params = {
        "table_name": "receipts",
        "last_sync_time": datetime.utcnow().isoformat()
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Sync Pull Test Passed!")
        else:
            print("❌ Sync Pull Test Failed!")
            
    except Exception as e:
        print(f"❌ Error during sync pull: {e}")

if __name__ == "__main__":
    test_sync_push()
    test_sync_pull()
