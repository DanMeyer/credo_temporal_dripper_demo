from __future__ import annotations
from temporalio import activity
import asyncio, httpx, os, random
from . import config
from .limiter import Limiter
from .logger import log_activity

limiter = Limiter()

def _sleep(ms): 
    return asyncio.sleep(ms / 1000.0)

@activity.defn(name="GetPatientFromDB")
async def get_patient_from_db(patient_id: str) -> tuple[str, str]:
    log_activity("GetPatientFromDB", {"patient_id": patient_id})
    # Dummy: derive a fake name
    first = f"Pat{patient_id[-2:]}"
    last = "Example"
    await _sleep(50)
    return first, last

@activity.defn(name="TaskTracker_Create")
async def tasktracker_create(patient_id: str, first: str, last: str) -> str:
    limiter.admit_or_wait(config.KEY_TASKTRACKER_WRITES, timeout_s=3)
    log_activity("TaskTracker_Create", {"patient_id": patient_id, "first": first, "last": last})
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{config.TT_URL}/create", json={"patient_id": patient_id, "first": first, "last": last})
        r.raise_for_status()
        await _sleep(30)
        return r.json()["task_id"]

@activity.defn(name="TaskTracker_UpdateStatus")
async def tasktracker_update_status(task_id: str, status: str):
    limiter.admit_or_wait(config.KEY_TASKTRACKER_WRITES, timeout_s=3)
    log_activity("TaskTracker_UpdateStatus", {"task_id": task_id, "status": status})
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{config.TT_URL}/update", json={"task_id": task_id, "status": status})
        r.raise_for_status()
        await _sleep(30)

@activity.defn(name="TaskTracker_AppendReport")
async def tasktracker_append_report(task_id: str, report: str):
    limiter.admit_or_wait(config.KEY_TASKTRACKER_WRITES, timeout_s=3)
    log_activity("TaskTracker_AppendReport", {"task_id": task_id})
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{config.TT_URL}/append", json={"task_id": task_id, "report": report})
        r.raise_for_status()
        await _sleep(30)

@activity.defn(name="DocEx_Search")
async def docex_search(first: str, last: str) -> str:
    limiter.admit_or_wait(config.KEY_DOCX_SEARCH_DOWNLOAD, timeout_s=6)
    log_activity("DocEx_Search", {"first": first, "last": last})
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{config.DOCX_URL}/search", json={"first": first, "last": last})
        r.raise_for_status()
        await _sleep(100)
        return r.json()["job_id"]

@activity.defn(name="DocEx_CheckStatus")
async def docex_check_status(job_id: str) -> dict:
    limiter.admit_or_wait(config.KEY_DOCX_STATUS, timeout_s=1.5)
    log_activity("DocEx_CheckStatus", {"job_id": job_id})
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{config.DOCX_URL}/status", params={"job_id": job_id})
        r.raise_for_status()
        await _sleep(20)
        return r.json()

@activity.defn(name="DocEx_DownloadAndExtract")
async def docex_download_and_extract(archive_url: str) -> list[str]:
    limiter.admit_or_wait(config.KEY_DOCX_SEARCH_DOWNLOAD, timeout_s=6)
    log_activity("DocEx_DownloadAndExtract", {"archive_url": archive_url})
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{config.DOCX_URL}/download", params={"url": archive_url})
        r.raise_for_status()
        data = r.json()
        files = data.get("files", [])
        await _sleep(100)
        return files

@activity.defn(name="ConvertFile")
async def convert_file(path: str) -> str:
    # Simulate per-file RAM/CPU heavy work by sleeping
    log_activity("ConvertFile", {"path": path})
    await _sleep(random.randint(50, 150))  # 50–150ms
    # Return a "converted" filename
    return f"{path}.pdf"

@activity.defn(name="PutToStorage")
async def put_to_storage(path: str) -> None:
    log_activity("PutToStorage", {"path": path})
    await _sleep(20)
    return None

@activity.defn(name="GenerateReport")
async def generate_report(file_names: list[str]) -> str:
    log_activity("GenerateReport", {"count": len(file_names)})
    report = "\n".join(file_names)
    await _sleep(30)
    return report
