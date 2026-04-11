import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict

def mask_phone(phone: str) -> str:
    if not phone: return ""
    clean = "".join(filter(str.isdigit, phone))
    if len(clean) < 4: return "****"
    return f"{clean[:4]}****{clean[-2:]}"

def mask_email(email: str) -> str:
    if not email or "@" not in email: return "***"
    user, domain = email.split("@", 1)
    if len(user) <= 1: return f"*@{domain}"
    return f"{user[0]}***@{domain}"

def structured_log(logger: logging.Logger, level: int, event: str, **fields: Any):
    """
    Emits a consistent JSON-formatted log line across all layers.
    standardized fields: timestamp, event, channel, target, status, retry_count, latency_ms, error_message, task_id.
    Automatically masks 'target' if it looks like an email or phone number.
    """
    processed_fields = {}
    for k, v in fields.items():
        # Masking PII
        if k == "target" and isinstance(v, str):
            if "@" in v:
                processed_fields[k] = mask_email(v)
            elif any(c.isdigit() for c in v):
                processed_fields[k] = mask_phone(v)
            else:
                processed_fields[k] = v
        else:
            processed_fields[k] = v

    log_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **processed_fields
    }
    
    logger.log(level, json.dumps(log_payload))

def generate_idempotency_key(activation_key_id: str, target: str, message: str) -> str:
    """Combines key params into a stable hash."""
    raw = f"{activation_key_id}:{target}:{message}"
    return hashlib.sha256(raw.encode()).hexdigest()
