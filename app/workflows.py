from __future__ import annotations
from temporalio import workflow
from temporalio.common import RetryPolicy
from typing import Optional, List

with workflow.unsafe.imports_passed_through():
    from . import activities as act

@workflow.defn
class PatientIngestWorkflow:
    @workflow.run
    async def run(self, patient_id: str) -> str:
        first, last = await workflow.execute_activity(
            act.get_patient_from_db, patient_id,
            schedule_to_close_timeout=timedelta(seconds=10),
        )

        task_id = await workflow.execute_activity(
            act.tasktracker_create, patient_id, first, last,
            schedule_to_close_timeout=timedelta(seconds=10),
        )

        job_id = await workflow.execute_activity(
            act.docex_search, first, last,
            schedule_to_close_timeout=timedelta(seconds=15),
            retry_policy=RetryPolicy(initial_interval=timedelta(seconds=1), maximum_interval=timedelta(seconds=10), maximum_attempts=10),
        )

        archive_url = await workflow.execute_child_workflow(DocEx_PollAndFetch, job_id)

        if not archive_url:
            await workflow.execute_activity(
                act.tasktracker_update_status, task_id, "DOCUMENTS_NOT_FOUND",
                schedule_to_close_timeout=timedelta(seconds=10),
            )
            report = await workflow.execute_activity(
                act.generate_report, [], schedule_to_close_timeout=timedelta(seconds=10),
            )
            await workflow.execute_activity(
                act.tasktracker_append_report, task_id, report,
                schedule_to_close_timeout=timedelta(seconds=10),
            )
            return "NOT_FOUND"

        files = await workflow.execute_activity(
            act.docex_download_and_extract, archive_url,
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(initial_interval=timedelta(seconds=1), maximum_interval=timedelta(seconds=10), maximum_attempts=5),
        )

        converted = await workflow.execute_child_workflow(ConvertAll, files)

        await workflow.execute_activity(
            act.tasktracker_update_status, task_id, "DOCUMENTS_FOUND",
            schedule_to_close_timeout=timedelta(seconds=10),
        )
        report = await workflow.execute_activity(
            act.generate_report, converted,
            schedule_to_close_timeout=timedelta(seconds=10),
        )
        await workflow.execute_activity(
            act.tasktracker_append_report, task_id, report,
            schedule_to_close_timeout=timedelta(seconds=10),
        )
        return "FOUND"

@workflow.defn
class DocEx_PollAndFetch:
    @workflow.run
    async def run(self, job_id: str) -> Optional[str]:
        backoff = 0.5
        while True:
            status = await workflow.execute_activity(
                act.docex_check_status, job_id,
                schedule_to_close_timeout=timedelta(seconds=5),
                retry_policy=RetryPolicy(initial_interval=timedelta(seconds=0.5), maximum_interval=timedelta(seconds=5), maximum_attempts=3),
                task_queue="status",
            )
            if status.get("state") == "finished":
                return status.get("archive_url")
            if status.get("state") in {"failed", "not_found"}:
                return None
            await workflow.sleep(backoff + workflow.random().random() * 0.25)
            backoff = min(backoff * 2, 10.0)

@workflow.defn
class ConvertAll:
    @workflow.run
    async def run(self, files: List[str]) -> List[str]:
        # bounded concurrency via workflow semaphore
        sem = workflow.Semaphore(6)
        results: List[str] = []

        async def one(f: str):
            async with sem:
                pdf = await workflow.execute_activity(
                    act.convert_file, f,
                    schedule_to_close_timeout=timedelta(seconds=30),
                    task_queue="convert",
                )
                await workflow.execute_activity(
                    act.put_to_storage, pdf,
                    schedule_to_close_timeout=timedelta(seconds=10),
                    task_queue="convert",
                )
                results.append(pdf)

        await workflow.wait_for_all([one(f) for f in files])
        return results

from datetime import timedelta
