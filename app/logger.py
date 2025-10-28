import csv, os, time
from . import config

# Ensure CSV file has headers
def _ensure_headers(path):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ts_start", "ts_end", "activity", "args"])

def log_activity(name: str, args: dict):
    path = config.CSV_PATH
    _ensure_headers(path)
    ts_start = time.time()
    # simulate some work sleeping proportional to a tiny factor
    time.sleep(0.1)
    ts_end = time.time()
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow([ts_start, ts_end, name, str(args)])
