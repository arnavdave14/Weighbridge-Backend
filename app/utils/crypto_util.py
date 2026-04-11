import hashlib
import json
from typing import Any, Dict
from decimal import Decimal
from datetime import datetime

def normalize_for_hash(val: Any) -> Any:
    """
    Normalizes values for deterministic hashing.
    """
    if val is None:
        return None
    if isinstance(val, (int, float, Decimal)):
        return format(val, ".3f")
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, dict):
        return {str(k): normalize_for_hash(v) for k, v in val.items()}
    if isinstance(val, list):
        return [normalize_for_hash(i) for i in val]
    return str(val)

def generate_receipt_hash(receipt_data: Dict[str, Any], previous_hash: str, version: int = 1) -> str:
    """
    Generates a deterministic SHA256 hash for a receipt record.
    Uses strict normalization and stable JSON serialization.
    Payload: previous_hash || version || normalized_json
    """
    if version == 1:
        # 1. Normalize and filter fields
        # Exclude metadata/transient fields
        clean_data = {
            str(k): normalize_for_hash(v) for k, v in receipt_data.items() 
            if k not in ("id", "current_hash", "previous_hash", "created_at", "updated_at", "is_synced", "synced_at", "sync_attempts", "last_error", "hash_version")
        }
        
        # 2. Stable JSON serialization
        # - sort_keys=True: deterministic order
        # - separators=(",", ":"): no whitespace
        # - ensure_ascii=False: handle unicode correctly
        normalized_payload = json.dumps(
            clean_data, 
            sort_keys=True, 
            separators=(",", ":"), 
            ensure_ascii=False
        )
        
        # 3. Concatenate with previous hash and version
        # Using a stable delimiter
        payload = f"{previous_hash}||v{version}||{normalized_payload}"
        
        # 4. Compute SHA256
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
    
    raise ValueError(f"Unsupported hash version: {version}")

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"
