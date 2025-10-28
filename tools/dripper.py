from __future__ import annotations
import os, time, math, random
from typing import Dict, Tuple

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RATES = os.getenv("RATES", "docx:status=10/sec,docx:search_download=10/min,tasktracker:writes=10/sec")
NO_BACKLOG = os.getenv("NO_BACKLOG", "true").lower() == "true"

def parse_rates(s: str) -> Dict[str, float]:
    # returns interval seconds per token per key
    out = {}
    for part in s.split(","):
        key, rate = part.split("=")
        val, unit = rate.split("/")
        val = float(val)
        if unit == "sec":
            interval = 1.0 / val
        elif unit == "min":
            interval = 60.0 / val
        else:
            raise ValueError("unit must be sec or min")
        out[key] = interval
    return out

def main():
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    schedule = parse_rates(RATES)
    # next eligible time per key
    next_t: Dict[str, float] = {k: time.time() for k in schedule.keys()}
    print("Dripper started with keys:", schedule)
    while True:
        now = time.time()
        for key, interval in schedule.items():
            # No backlog: only emit if now >= next_t; then set next_t+=interval
            if now >= next_t[key]:
                # jitter a touch to prevent phase alignment
                next_t[key] = now + interval + random.uniform(0, interval * 0.05)
                # Emit one token at current time
                r.xadd(key, {"token": "1"})
        time.sleep(0.02)

if __name__ == "__main__":
    main()
