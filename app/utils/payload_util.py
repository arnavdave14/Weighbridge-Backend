import json
import re
from typing import Any, Dict, List

# Production Safety Limits
MAX_PAYLOAD_SIZE = 10 * 1024  # 10KB
MAX_IMAGE_COUNT = 10
TRUCK_NO_REGEX = r'^[A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4}$'

def flatten_payload_to_values(obj: Any) -> str:
    """
    Flattens all values from a nested dict/list into a single space-separated string.
    Used for the universal 'smart search' system.
    Strictly includes VALUES only (no keys).
    """
    if isinstance(obj, dict):
        # Recursively get values from dict
        return " ".join(filter(None, [flatten_payload_to_values(v) for v in obj.values()]))
    elif isinstance(obj, list):
        # Recursively get items from list
        return " ".join(filter(None, [flatten_payload_to_values(i) for i in obj]))
    elif obj is None or obj == "":
        return ""
    else:
        # Convert to string and strip
        return str(obj).strip()

def normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Silently corrects common key variations and ensures consistent formatting.
    """
    if not payload or "data" not in payload:
        return payload

    data = payload["data"]
    variations = [
        "truckNo", "Truck_No", "vehicle_no", "Vehicle_No",
        "vehicleNumber", "trucknumber", "Truck_Number", 
        "Vehicle_Number", "truck_number"
    ]

    # Map variations to canonical 'truck_no'
    for var in variations:
        if var in data:
            val = data.pop(var)
            if "truck_no" not in data:
                data["truck_no"] = val

    # Force Uppercase for truck number
    if "truck_no" in data and isinstance(data["truck_no"], str):
        data["truck_no"] = data["truck_no"].upper()

    return payload

def validate_payload_fallback(payload: Dict[str, Any], image_urls: List[str]) -> None:
    """
    Lightweight backend fallback validation to protect system integrity.
    Rejects requests exceeding limits or failing critical format checks.
    """
    # 1. Size Check
    payload_str = json.dumps(payload)
    if len(payload_str) > MAX_PAYLOAD_SIZE:
        raise ValueError(f"Payload size exceeds limit of {MAX_PAYLOAD_SIZE // 1024}KB")

    # 2. Image Count Check
    if len(image_urls) > MAX_IMAGE_COUNT:
        raise ValueError(f"Image count exceeds limit of {MAX_IMAGE_COUNT}")

    if not payload or "data" not in payload:
        return

    data = payload["data"]

    # 3. Truck Number Format (Selective)
    if "truck_no" in data and data["truck_no"]:
        val = str(data["truck_no"])
        if not re.match(TRUCK_NO_REGEX, val):
            raise ValueError(f"Invalid Truck Number format: '{val}'. Expected format: MP09AB1234")

    # 4. Numeric Weights (Selective)
    for weight_field in ["gross", "tare", "net"]:
        if weight_field in data and data[weight_field] is not None:
            val = data[weight_field]
            try:
                # This handles numeric strings as well
                float(val)
            except (ValueError, TypeError):
                raise ValueError(f"Weight field '{weight_field}' must be numeric, got: '{val}'")
