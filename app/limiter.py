from __future__ import annotations
import os, time, random
from typing import Optional
import config

try:
    import redis
except ImportError:
    redis = None

class Limiter:
    def __init__(self, mode: str = None, redis_url: str | None = None):
        self.mode = (mode or config.LIMITER_MODE).lower()
        self.redis_url = redis_url or config.REDIS_URL
        self._r = None
        if self.mode == "dripper":
            if redis is None:
                raise RuntimeError("Limiter in dripper mode requires redis-py installed")
            self._r = redis.Redis.from_url(self.redis_url, decode_responses=True)

    def admit_or_wait(self, key: str, timeout_s: float = 5.0):
        if self.mode == "none":
            return
        elif self.mode == "dripper":
            # Read one token from a Redis Stream/List. We'll use XREAD on a stream.
            # We read from the tail ($), BLOCK until the next token arrives.
            # timeout in milliseconds
            block_ms = int(max(0.0, timeout_s) * 1000)
            stream = key
            # Use a consumer group-less XREAD starting from latest '$'
            # We want to block until a new entry is added.
            res = self._r.xread({stream: "$"}, block=block_ms, count=1)
            if not res:
                raise TimeoutError(f"Limiter timeout waiting for token on '{key}'")
            # Tiny jitter to avoid phase alignment
            time.sleep(random.uniform(0, 0.02))
            return
        else:
            raise ValueError(f"Unknown limiter mode: {self.mode}")
