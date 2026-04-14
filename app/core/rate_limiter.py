import time
import redis
from app.config.settings import settings

class RateLimiter:
    """
    Redis-backed rate limiter using the Token Bucket / Window-based INCR + EXPIRE pattern.
    Atomically checks if a quota has been exceeded for a given key.
    """
    
    def __init__(self):
        # We reuse the REDIS_URL from settings
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self._connected = None # Lazy check

    def ping(self) -> bool:
        """Verifies Redis connection status."""
        try:
            self.redis_client.ping()
            self._connected = True
            return True
        except redis.RedisError:
            self._connected = False
            return False

    @property
    def is_connected(self) -> bool:
        if self._connected is None:
            self.ping()
        return self._connected

    def check(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        """Legacy single check."""
        allowed, results = self.check_multi([(key, limit, window_seconds)])
        return allowed, results[0][1]

    def check_multi(self, checks: list[tuple[str, int, int]]) -> tuple[bool, list[tuple[bool, int]]]:
        """
        Atomically checks multiple rate limits.
        checks: list of (key, limit, window_seconds)
        Returns: (overall_allowed, list of (is_allowed, remaining))
        """
        if not self.is_connected:
            # Fail-open if Redis is down
            return True, [(True, -1)] * len(checks)

        try:
            pipe = self.redis_client.pipeline()
            for key, _, window in checks:
                full_key = f"ratelimit:{key}"
                pipe.incr(full_key)
                pipe.expire(full_key, window, nx=True)
            
            results = pipe.execute()
            
            check_results = []
            overall_allowed = True
            
            for i, (key, limit, _) in enumerate(checks):
                count = results[i*2] # INCR result
                remaining = max(0, limit - count)
                is_allowed = count <= limit
                if not is_allowed:
                    overall_allowed = False
                check_results.append((is_allowed, remaining))
                
            return overall_allowed, check_results
            
        except redis.RedisError:
            self._connected = False # Mark as disconnected to trigger fail-open next time
            return True, [(True, -1)] * len(checks)

rate_limiter = RateLimiter()
