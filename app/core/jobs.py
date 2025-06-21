import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobInfo:
    def __init__(self, service: str, job_id: Optional[str] = None, openapi_url: Optional[str] = None):
        self.service = service
        self.job_id = job_id or str(uuid.uuid4())
        self.openapi_url = openapi_url
        self.status = JobStatus.PENDING
        self.submitted_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None
        self.progress = 0
        self.result = None
        self.error = None

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "service": self.service,
            "status": self.status.value,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
        }

class JobManager:
    def __init__(self):
        self._jobs: Dict[str, JobInfo] = {}
        self._processing = False
        self._stop_requested = False

    def enqueue_job(self, job_id: str, service: str, openapi_url: str):
        job = JobInfo(service=service, job_id=job_id, openapi_url=openapi_url)
        self._jobs[job_id] = job
        logger.info(f"Job enqueued: {job_id} for service {service}")

    def get_job_status(self, job_id: str) -> Optional[JobInfo]:
        return self._jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job and job.status not in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            logger.info(f"Job cancelled: {job_id}")
            return True
        return False

    async def process_jobs(self, max_jobs: int = 1):
        if self._processing:
            logger.debug("Job processing already running")
            return
        self._processing = True
        logger.info("Starting job processing")
        try:
            while not self._stop_requested and self._jobs:
                for job in list(self._jobs.values()):
                    if job.status == JobStatus.PENDING:
                        job.status = JobStatus.RUNNING
                        job.started_at = datetime.utcnow()
                        logger.info(f"Processing job {job.job_id} for service {job.service}")
                        # TODO: Implement actual client generation logic here
                        # Simulate quick completion for now:
                        job.status = JobStatus.COMPLETED
                        job.completed_at = datetime.utcnow()
                        job.progress = 100
                        job.result = f"Generated client for {job.service}"
                        logger.info(f"Completed job {job.job_id}")
                        max_jobs -= 1
                        if max_jobs <= 0:
                            break
                await asyncio.sleep(0.1)  # avoid tight loop
        finally:
            self._processing = False
            logger.info("Job processing loop stopped")

    def stop_processing(self):
        self._stop_requested = True
        logger.info("Job processing stop requested")

job_manager = JobManager()
