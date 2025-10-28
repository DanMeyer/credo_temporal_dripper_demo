from __future__ import annotations
import os, random, time, json
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI()
PORT = int(os.getenv("PORT", "9001"))

tasks = {}

class CreateReq(BaseModel):
    patient_id: str
    first: str
    last: str

class UpdateReq(BaseModel):
    task_id: str
    status: str

class AppendReq(BaseModel):
    task_id: str
    report: str

@app.post("/create")
def create(req: CreateReq):
    task_id = f"T{random.randint(1000,9999)}"
    tasks[task_id] = {"patient_id": req.patient_id, "status": "NEW", "notes": []}
    return {"task_id": task_id}

@app.post("/update")
def update(req: UpdateReq):
    tasks.setdefault(req.task_id, {"notes": []})
    tasks[req.task_id]["status"] = req.status
    return {"ok": True}

@app.post("/append")
def append(req: AppendReq):
    tasks.setdefault(req.task_id, {"notes": []})
    tasks[req.task_id]["notes"].append(req.report)
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
