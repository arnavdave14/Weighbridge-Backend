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

    def check(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        """
        Checks if the rate limit is exceeded for the key.
        Returns: (is_allowed, remaining_quota)
        """
        # Key format: ratelimit:{key}
        full_key = f"ratelimit:{key}"
        
        try:
            # Use pipeline for atomic increment and expire
            pipe = self.redis_client.pipeline()
            pipe.incr(full_key)
            pipe.expire(full_key, window_seconds, nx=True) # set expire only if key is new
            results = pipe.execute()
            
            count = results[0]
            remaining = max(0, limit - count)
            
            if count > limit:
                return False, 0
                
            return True, remaining
            
        except redis.RedisError:
            # On redis error, we default to allowing to avoid blocking critical notifications
            # but log the failure in the calling service.
            return True, -1

rate_limiter = RateLimiter()
