import os

TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
LIMITER_MODE = os.getenv("LIMITER_MODE", "none")  # none|dripper
CSV_PATH = os.getenv("CSV_PATH", "./data/activity_log.csv")

# fake services
DOCX_URL = os.getenv("STUB_DOCX_URL", "http://localhost:9000")
TT_URL   = os.getenv("STUB_TT_URL", "http://localhost:9001")

# Rates (only used by dripper clients for key names)
RATE_DOCX_STATUS = os.getenv("DOCEX_STATUS_RATE", "10/sec")
RATE_DOCX_SEARCH = os.getenv("DOCEX_SEARCH_RATE", "10/min")
RATE_TASKTRACKER = os.getenv("TASKTRACKER_RATE", "10/sec")

# Token stream keys
KEY_DOCX_STATUS = "docx:status"
KEY_DOCX_SEARCH_DOWNLOAD = "docx:search_download"
KEY_TASKTRACKER_WRITES = "tasktracker:writes"
