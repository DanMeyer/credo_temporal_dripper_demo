from __future__ import annotations
import argparse, asyncio, os
from temporalio.client import Client
from . import config
from .workflows import PatientIngestWorkflow

async def run(patient_id: str):
    client = await Client.connect(config.TEMPORAL_ADDRESS)
    handle = await client.start_workflow(
        PatientIngestWorkflow.run,
        patient_id,
        id=f"patient-{patient_id}",
        task_queue="general",
    )
    print("Started", handle.id)
    result = await handle.result()
    print("Result:", result)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--patient-id", required=True)
    args = p.parse_args()
    asyncio.run(run(args.patient_id))

if __name__ == "__main__":
    main()
