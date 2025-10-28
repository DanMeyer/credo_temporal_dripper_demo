from __future__ import annotations
import argparse, asyncio, os
from temporalio.client import Client
from temporalio.worker import Worker

from . import config
from . import activities as act
from .workflows import PatientIngestWorkflow, DocEx_PollAndFetch, ConvertAll

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default="general")
    parser.add_argument("--max-activities", type=int, default=50)
    args = parser.parse_args()

    queues = [q.strip() for q in args.queue.split(",")]
    client = await Client.connect(config.TEMPORAL_ADDRESS)

    # Bind activities to queues by registration; Temporal routes based on task_queue in execute_activity
    for q in queues:
        acts = [
            act.get_patient_from_db,
            act.tasktracker_create,
            act.tasktracker_update_status,
            act.tasktracker_append_report,
            act.docex_search,
            act.docex_check_status,
            act.docex_download_and_extract,
            act.convert_file,
            act.put_to_storage,
            act.generate_report,
        ]
        w = Worker(
            client,
            task_queue=q,
            workflows=[PatientIngestWorkflow, DocEx_PollAndFetch, ConvertAll] if q == "general" else [],
            activities=acts,
            max_concurrent_activities=args.max_activities,
        )
        asyncio.create_task(w.run())

    # Keep alive
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
