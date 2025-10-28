from __future__ import annotations
import os, random, time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI()
PORT = int(os.getenv("PORT", "9000"))

# simple in-memory store
jobs = {}

class SearchReq(BaseModel):
    first: str
    last: str

@app.post("/search")
def search(req: SearchReq):
    job_id = f"J{random.randint(1000,9999)}"
    # queued → running → finished after a few checks
    jobs[job_id] = {"state": "queued", "checks": 0}
    return {"job_id": job_id}

@app.get("/status")
def status(job_id: str):
    if job_id not in jobs:
        return {"state": "not_found"}
    entry = jobs[job_id]
    entry["checks"] += 1
    if entry["checks"] == 1:
        entry["state"] = "queued"
    elif entry["checks"] == 2:
        entry["state"] = "running"
    elif entry["checks"] >= 3:
        entry["state"] = "finished"
        entry["archive_url"] = f"http://stub-docx:{PORT}/archive/{job_id}"
    return entry

@app.get("/download")
def download(url: str):
    # Return list of "files" (strings) instead of real content
    count = random.randint(0, 30)  # keep it small for local
    files = [f"doc_{i:04d}" for i in range(count)]
    return {"files": files}

@app.get("/archive/{job_id}")
def archive(job_id: str):
    # Non-functional placeholder; returned URL is used as an opaque token
    return {"ok": True, "job_id": job_id}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
