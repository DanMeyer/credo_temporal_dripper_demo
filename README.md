# Reflection

## Highlights:
- **Temporal** workflows with **child workflows** (`DocEx_PollAndFetch`, `ConvertAll`)
- **Dripper** strategy for API rate limiting via tokens (via Redis Streams)
- **Sharded task queues** (`general`, `status`, `convert`)
    - `CONVERT_MAX` env variable limits the number of `convert` tasks
- **Docker Compose** for local runs
- **HTTP fakes** for DocumentExchange and TaskTracker
- Dummy Activities that **sleep and CSV-log** start/finish and args

## Future work: External service outages
> DocumentExchange and TaskTracker will occasionally have outages, describe (don’t code) how you would handle that

Some strategies:
- broadly, let Temporal handle as much of this as possible
- smart backoff strategies
    - we want to keep retrying the service forever (so we can self-heal) BUT at increasing intervals (so we don't try every N seconds for 2 straight hours for every workflow)
- circuit breaker around the external resource (stop trying for M minutes after N failures)
    - ideally can resume smartly for everyone after a success

## Notes
- Initially, I fed the prompt into ChatGPT and "negotiated" a solution plan
    - e.g. I interrogated it about different rate limiting options before settling on the `dripper`
- I let ChatGPT take a crack at building the whole thing. It did a pretty decent job - including suggesting setting up the fake little HTTP endpoints. That's probably something I wouldn't have necessarily hand-coded, but was happy to have generated for me (because it was a throwaway for development)
- Then, I moved into cursor to code review, debug, etc
- I spent at least an hour (maybe two?) wrestling with Docker/Temporal/Postgres settings. The root cause, I think, was that the `temporalio/auto-setup` image has changed a bit recently. It dropped support for SQLite, and some variable names changed. So Cursor and ChatGPT weren't super helpful with the ultimate solution: I had to find a canonical docker compose file from Temporal and work from that. Cursor was very helpful, though, at running Docker commands to spin things up, tear things down, and look at logs (all stuff that would eventually just be in my fingers)
- ChatGPT hallucinated a few minor things, e.g. that `sleep` lived on the `workflow` instead of being an `asyncio` function. But there was pretty minimal debugging to do to get things running.

# How to Configure and Run

## Quickstart

### Standard Startup
```bash
# 1) Build and start the stack (Temporal+Redis+workers+stubs)
docker compose up --build

# 2) Kick off a sample run (from another terminal window)
docker compose run --rm demo python app/demo_run.py --patient-id P123
```

### Complete Docker Environment Reset

If you need to completely clean your Docker environment and start fresh:

```bash
# 1) Nuclear option - remove ALL Docker resources
docker system prune -a --volumes --force

# 2) Stop and remove any existing containers/volumes
docker compose down --volumes --remove-orphans

# 3) Rebuild everything from scratch (no cache)
docker compose build --no-cache

# 4) Start all services
docker compose up -d

# 5) Verify all services are running
docker compose ps

# 6) Check demo logs
docker compose logs demo

# 7) Run the demo
docker compose run --rm demo python app/demo_run.py --patient-id P123

# 8) Check activity log
cat data/activity_log.csv
```

### Verification Steps

After starting the services, verify everything is working:

```bash
# Check all containers are healthy
docker compose ps

# View demo execution logs
docker compose logs demo

# View dripper activity
docker compose logs dripper

# View worker activity
docker compose logs worker-general worker-convert worker-status

# Run the demo to verify workflow execution
docker compose run --rm demo python app/demo_run.py --patient-id P123

# Check the activity log for workflow execution
tail -f data/activity_log.csv

# Access Temporal UI (optional)
open http://localhost:8080
```

**Expected Output**: You should see patient processing with activities like:
- `GetPatientFromDB`
- `TaskTracker_Create`
- `DocEx_Search`
- `DocEx_CheckStatus` (multiple times with rate limiting)
- `DocEx_DownloadAndExtract`
- Multiple `ConvertFile` operations
- Multiple `PutToStorage` operations
- `TaskTracker_UpdateStatus`
- `GenerateReport`
- `TaskTracker_AppendReport`

Default **LIMITER_MODE** is `dripper`. To disable the limiter:
- Set `LIMITER_MODE=none` on the worker services in `docker-compose.yml`

## Structure

- `app/workflows.py` – main & child workflows
- `app/activities.py` – all Activities (each logs CSV on start/finish)
- `app/limiter.py` – pluggable `Limiter`: `none` or `dripper`
- `app/run_worker.py` – worker entrypoint; binds queues and Activities
- `app/demo_run.py` – simple CLI to start a workflow run
- `stubs/docx_stub.py` – fake DocumentExchange HTTP service
- `stubs/tasktracker_stub.py` – fake TaskTracker HTTP service
- `tools/dripper.py` – token emitter for Redis Streams
- `data/activity_log.csv` – CSV log sink (mounted volume)

## Environment

- **Temporal**: `temporalio/auto-setup` (dev server) at `temporal:7233`
- **Redis**: `redis:7`
- **Python**: 3.11 (image built from `Dockerfile`)

## Configuration

Environment variables (see `docker-compose.yml`):
- `LIMITER_MODE`: `none` or `dripper`
- `CONVERT_MAX`: parallel conversion per worker host (default 2 for laptops)
- `DOCEX_STATUS_RATE`: e.g., `10/sec`
- `DOCEX_SEARCH_RATE`: e.g., `10/min`
- `TASKTRACKER_RATE`: e.g., `10/sec`
- `REDIS_URL`, `TEMPORAL_ADDRESS`, `STUB_DOCX_URL`, `STUB_TT_URL`