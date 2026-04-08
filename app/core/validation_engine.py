import re
import json
import logging
import hashlib
from datetime import datetime
from functools import lru_cache
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Standard Regex Patterns
PATTERNS = {
    "alphanumeric": r"^[a-zA-Z0-9 ]{1,100}$",
    "alphabetical": r"^[a-zA-Z ]{1,100}$",
    "numeric": r"^[0-9]+$",
    "text": r"^.{1,500}$",
}

@lru_cache(maxsize=128)
def compile_regex(pattern: str):
    """Cached compilation of regex patterns for high performance."""
    try:
        return re.compile(pattern)
    except re.error as e:
        logger.error(f"Invalid regex pattern: {pattern} - {e}")
        return None

def canonicalize_json(data: Dict[str, Any]) -> str:
    """
    Standardizes JSON to a single string format for consistent HMAC signing.
    - Sorted keys
    - No extra whitespace (separators=(',', ':'))
    - Enforces UTF-8
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def get_etag(data: Any) -> str:
    """Generates a stable ETag for configuration data."""
    canon = canonicalize_json(data)
    return hashlib.md5(canon.encode("utf-8")).hexdigest()

class ValidationEngine:
    @staticmethod
    def validate_receipt(receipt_data: Dict[str, Any], labels_config: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, str]]:
        """
        Validates a single receipt unit against the provided labels configuration.
        Atomic: Returns True only if ALL fields pass.
        Returns (is_valid, error_map).
        """
        errors = {}
        custom_data = receipt_data.get("custom_data", {})

        for config in labels_config:
            name = config.get("name")
            field_type = config.get("type", "text")
            is_required = config.get("required", False)
            custom_regex = config.get("regex")

            # 1. Existence / Required Check
            value = custom_data.get(name)
            
            # Normalize: Trim string values
            if isinstance(value, str):
                value = value.strip()
            
            if is_required and (value is None or value == ""):
                errors[name] = "Field is required and cannot be empty"
                continue

            if value is None or value == "":
                # Field is empty but optional, skip further checks
                continue

            # 2. Type-Specific Validation
            if field_type == "date":
                try:
                    # Proper date parsing instead of just regex
                    if isinstance(value, str):
                        datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    errors[name] = "Invalid date format. Expected ISO 8601 (YYYY-MM-DD)"
                continue

            # 3. Regex Validation
            pattern_str = custom_regex or PATTERNS.get(field_type, PATTERNS["text"])
            
            # Defensive check: limit regex complexity/length
            if len(pattern_str) > 200:
                logger.warning(f"Rejecting over-complex regex for field {name}")
                pattern_str = PATTERNS["text"]

            reg = compile_regex(pattern_str)
            if reg and not reg.match(str(value)):
                errors[name] = f"Value does not match validation pattern for {field_type}"

        return len(errors) == 0, errors

    @staticmethod
    def normalize_custom_data(data: Dict[str, Any], labels_config: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Applies normalization rules (casing, trimming) to the input data.
        """
        normalized = data.copy()
        for config in labels_config:
            name = config.get("name")
            field_type = config.get("type", "text")
            
            if name in normalized and isinstance(normalized[name], str):
                val = normalized[name].strip()
                
                # Special casing: Alphanumeric and Numeric often benefit from uppercase
                if field_type in ["alphanumeric", "alphabetical"]:
                    val = val.upper()
                
                normalized[name] = val
        
        return normalized
