import asyncio
import subprocess
import shutil
import os
import json
import uuid
from datetime import datetime
from typing import Optional

from app.core.jobs import Job, JobStatus, job_queue

CLIENTS_DIR = os.getenv("CLIENTGEN_CLIENTS_DIR", "/app/clients")
STATUS_DIR = os.getenv("CLIENTGEN_STATUS_DIR", "/data/status")

async def generate_client_job(service: str, openapi_url: str, job_id: str):
    job = await job_queue.get_job(job_id)
    if not job:
        return

    job.status = JobStatus.RUNNING
    job.started_at = datetime.utcnow()

    target_path = os.path.join(CLIENTS_DIR, service)
    status_path = os.path.join(STATUS_DIR, f"{service}.json")

    # Clean existing client folder if exists
    if os.path.exists(target_path):
        shutil.rmtree(target_path)

    # Ensure status dir exists
    os.makedirs(STATUS_DIR, exist_ok=True)

    try:
        # Run openapi-python-client generate command
        process = await asyncio.create_subprocess_exec(
            "openapi-python-client",
            "generate",
            "--url", openapi_url,
            "--meta", "none",
            "--output-path", target_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Wait for process while checking cancellation
        while True:
            if job.status == JobStatus.CANCELLED:
                process.terminate()
                job.completed_at = datetime.utcnow()
                job.progress = 0
                await save_job_status(job, status_path)
                return

            retcode = await process.wait()
            if retcode is not None:
                break
            await asyncio.sleep(0.5)

        stdout, stderr = await process.communicate()

        if retcode != 0:
            job.status = JobStatus.FAILED
            job.error = stderr.decode().strip() or "Unknown error"
            job.progress = 0
        else:
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.result = {
                "service": service,
                "version": "0.1.0",
                "import_path": service.replace("-", "_"),
                "local_path": target_path
            }

        job.completed_at = datetime.utcnow()
        await save_job_status(job, status_path)

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.completed_at = datetime.utcnow()
        await save_job_status(job, status_path)

async def save_job_status(job: Job, status_path: str):
    data = {
        "job_id": job.job_id,
        "service": job.service,
        "status": job.status.value,
        "submitted_at": job.submitted_at.isoformat() + "Z",
        "started_at": job.started_at.isoformat() + "Z" if job.started_at else None,
        "completed_at": job.completed_at.isoformat() + "Z" if job.completed_at else None,
        "progress": job.progress,
        "result": job.result,
        "error": job.error
    }
    # Save job status to JSON file
    with open(status_path, "w") as f:
        json.dump(data, f, indent=2)

async def enqueue_client_generation(service: str, openapi_url: str) -> str:
    job_id = str(uuid.uuid4())
    job = Job(
        job_id=job_id,
        service=service,
        openapi_url=openapi_url,
        status=JobStatus.PENDING,
        submitted_at=datetime.utcnow(),
        progress=0
    )
    await job_queue.add_job(job)
    # Schedule background generation
    asyncio.create_task(generate_client_job(service, openapi_url, job_id))
    return job_id
