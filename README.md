# Credo Temporal Dripper Demo

This is a runnable reference implementation of the approach we discussed:
- **Temporal** workflows with **child workflows** (`DocEx_PollAndFetch`, `ConvertAll`)
- **Dripper** strategy for API rate limiting (Redis Streams or no-op)
- **Sharded task queues** (`general`, `status`, `convert`)
- **Docker Compose** for local runs
- **HTTP fakes** for DocumentExchange and TaskTracker
- Dummy Activities that **sleep and CSV-log** start/finish and args

> Note: Activities simulate I/O only; they don't require real storage or DB.

## Quickstart

```bash
# 1) Build and start the stack (Temporal+Redis+workers+stubs)
docker compose up --build

# 2) Kick off a sample run (from another terminal window)
docker compose run --rm demo python app/demo_run.py --patient-id P123
```

Default **LIMITER_MODE** is `none`. To enable the **dripper** limiter:
- Set `LIMITER_MODE=dripper` on the worker services in `docker-compose.yml`
- Keep the `dripper` service enabled

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

## Notes

- Dripper uses Redis Streams with **no backlog** catch-up (avoids bursts).
- Each external call blocks on a token before executing when limiter enabled.
- Conversion queue is **bulkheaded** with low concurrency to respect RAM (single-threaded converts).