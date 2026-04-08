import logging
import redis
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config.settings import settings
from app.models.admin_models import MachineNonce

logger = logging.getLogger(__name__)

# Singleton-style Redis connection
_redis_client = None

def get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            _redis_client.ping()
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            return None
    return _redis_client

class NonceManager:
    @staticmethod
    async def is_nonce_used(db: AsyncSession, machine_id: str, nonce: str, ttl_seconds: int = 86400) -> bool:
        """
        Checks if a nonce has been used before for this specific machine.
        Strategy: Redis-First, DB-Fallback.
        """
        redis_key = f"nonce:{machine_id}:{nonce}"
        r = get_redis()
        
        # 1. Try Redis
        if r:
            try:
                if r.get(redis_key):
                    return True
                # Mark as used in Redis
                r.setex(redis_key, ttl_seconds, "1")
                # Even if Redis works, we still want to save to DB for long-term audit/fallback
            except Exception as e:
                logger.warning(f"Redis error during nonce check: {e}")

        # 2. Check Database (Fallback and Audit)
        stmt = select(MachineNonce).where(
            MachineNonce.machine_id == machine_id,
            MachineNonce.nonce == nonce
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            return True

        # 3. Save to Database (Atomic uniqueness ensured by DB constraint)
        try:
            new_nonce = MachineNonce(
                machine_id=machine_id,
                nonce=nonce,
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            )
            db.add(new_nonce)
            await db.flush() # Ensure it's part of transaction
        except Exception as e:
            # If we get a UniqueConstraint error here, it means another request just used it
            logger.error(f"Duplicate nonce detected via DB fallback: {e}")
            return True
            
        return False

    @staticmethod
    def get_throttle_delay(machine_id: str) -> float:
        """
        Returns a delay in seconds for progressive throttling based on recent failures.
        Uses Redis to track failure count.
        """
        r = get_redis()
        if not r:
            return 0.0
            
        fail_key = f"throttle:{machine_id}:fail_count"
        try:
            count = int(r.get(fail_key) or 0)
            if count == 0:
                return 0.0
            # Exponential backoff: 2^count * 0.5s, max 30s
            delay = min(pow(2, count) * 0.5, 30.0)
            return delay
        except Exception:
            return 0.0

    @staticmethod
    def record_failure(machine_id: str):
        """Increments failure count for throttling."""
        r = get_redis()
        if not r: return
        fail_key = f"throttle:{machine_id}:fail_count"
        try:
            r.incr(fail_key)
            r.expire(fail_key, 3600) # Reset after 1 hour of no failures
        except Exception:
            pass

    @staticmethod
    def clear_failures(machine_id: str):
        """Clears failure count on successful auth."""
        r = get_redis()
        if not r: return
        fail_key = f"throttle:{machine_id}:fail_count"
        try:
            r.delete(fail_key)
        except Exception:
            pass
