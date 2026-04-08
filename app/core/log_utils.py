import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

def structured_log(logger: logging.Logger, level: int, event: str, **fields: Any):
    """
    Emits a consistent JSON-formatted log line across all layers.
    standardized fields: timestamp, event, channel, target, status, retry_count, latency_ms, error_message, task_id.
    """
    log_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields
    }
    
    # Clean up fields to ensure they are JSON serializable
    # (e.g., convert UUIDs to strings if necessary, though dicts/strings/ints are fine)
    
    logger.log(level, json.dumps(log_payload))
