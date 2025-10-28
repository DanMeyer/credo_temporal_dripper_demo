from __future__ import annotations
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from typing import Optional, List

with workflow.unsafe.imports_passed_through():
    import activities as act

@workflow.defn
class PatientIngestWorkflow:
    @workflow.run
    async def run(self, patient_id: str) -> str:
        workflow.logger.info("PatientIngestWorkflow started", extra={"patient_id": patient_id})
        first, last = await workflow.execute_activity(
            act.get_patient_from_db,
            args=[patient_id],
            schedule_to_close_timeout=timedelta(seconds=10),
        )
        workflow.logger.info("Retrieved patient data", extra={"first": first, "last": last})

        task_id = await workflow.execute_activity(
            act.tasktracker_create,
            args=[patient_id, first, last],
            schedule_to_close_timeout=timedelta(seconds=10),
        )
        workflow.logger.info("Created task", extra={"task_id": task_id})
        
        job_id = await workflow.execute_activity(
            act.docex_search,
            args=[first, last],
            schedule_to_close_timeout=timedelta(seconds=15),
            retry_policy=RetryPolicy(initial_interval=timedelta(seconds=1), maximum_interval=timedelta(seconds=10), maximum_attempts=10),
        )
        workflow.logger.info("Started DocEx search", extra={"job_id": job_id})

        archive_url = await workflow.execute_child_workflow(DocEx_PollAndFetch, job_id)
        workflow.logger.info("DocEx polling completed", extra={"archive_url": archive_url})

        if not archive_url:
            await workflow.execute_activity(
                act.tasktracker_update_status,
                args=[task_id, "DOCUMENTS_NOT_FOUND"],
                schedule_to_close_timeout=timedelta(seconds=10),
            )
            report = await workflow.execute_activity(
                act.generate_report,
                args=[[]],
                schedule_to_close_timeout=timedelta(seconds=10),
            )
            await workflow.execute_activity(
                act.tasktracker_append_report,
                args=[task_id, report],
                schedule_to_close_timeout=timedelta(seconds=10),
            )
            return "NOT_FOUND"

        files = await workflow.execute_activity(
            act.docex_download_and_extract,
            args=[archive_url],
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(initial_interval=timedelta(seconds=1), maximum_interval=timedelta(seconds=10), maximum_attempts=5),
        )
        workflow.logger.info("Downloaded files", extra={"file_count": len(files)})
        
        converted = await workflow.execute_child_workflow(ConvertAll, files)

        await workflow.execute_activity(
            act.tasktracker_update_status,
            args=[task_id, "DOCUMENTS_FOUND"],
            schedule_to_close_timeout=timedelta(seconds=10),
        )
        report = await workflow.execute_activity(
            act.generate_report,
            args=[converted],
            schedule_to_close_timeout=timedelta(seconds=10),
        )
        await workflow.execute_activity(
            act.tasktracker_append_report,
            args=[task_id, report],
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
                act.docex_check_status,
                args=[job_id],
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
                    act.convert_file,
                    args=[f],
                    schedule_to_close_timeout=timedelta(seconds=30),
                    task_queue="convert",
                )
                await workflow.execute_activity(
                    act.put_to_storage,
                    args=[pdf],
                    schedule_to_close_timeout=timedelta(seconds=10),
                    task_queue="convert",
                )
                results.append(pdf)

        await workflow.wait_for_all([one(f) for f in files])
        return results
