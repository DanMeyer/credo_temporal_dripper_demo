from __future__ import annotations
import argparse, asyncio, random, string
from temporalio.client import Client

async def main(n: int, rate: float, address: str):
    from app.workflows import PatientIngestWorkflow
    client = await Client.connect(address)
    async def one(i):
        pid = "P" + "".join(random.choices(string.digits, k=5))
        h = await client.start_workflow(PatientIngestWorkflow.run, pid, id=f"patient-{pid}", task_queue="general")
        print("started", h.id)
    delay = 1.0 / rate if rate > 0 else 0
    for i in range(n):
        await one(i)
        await asyncio.sleep(delay)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=25)
    p.add_argument("--rate", type=float, default=2.0, help="workflows per second")
    p.add_argument("--address", default="localhost:7233")
    args = p.parse_args()
    asyncio.run(main(args.n, args.rate, args.address))
