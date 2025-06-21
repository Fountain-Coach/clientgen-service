import asyncio
import logging
import time
from functools import wraps
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any
from app.core.webhooks import webhook_manager
import async_timeout

logger = logging.getLogger(__name__)

def log_job_execution(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        try:
            logger.info(f"Starting job processing: args={args}, kwargs={kwargs}")
            result = await func(*args, **kwargs)
            logger.info(f"Job processing completed in {time.time() - start:.2f}s")
            return result
        except Exception as e:
            logger.error(f"Job processing failed after {time.time() - start:.2f}s: {e}", exc_info=True)
            raise
    return wrapper

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobInfo:
    def __init__(self, job_id: str, service: str, openapi_url: str):
        self.job_id = job_id
        self.service = service
        self.openapi_url = openapi_url
        self.status = JobStatus.PENDING
        self.submitted_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.progress: int = 0
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self._process: Optional[asyncio.subprocess.Process] = None
        self._cancel_event = asyncio.Event()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "service": self.service,
            "status": self.status.value,
            "submitted_at": self.submitted_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
        }

    def cancel(self):
        self._cancel_event.set()

    async def is_cancelled(self):
        return self._cancel_event.is_set()

class JobManager:
    def __init__(self, test_mode: bool = False):
        self._jobs: Dict[str, JobInfo] = {}
        self._queue = asyncio.Queue()
        self._running = True
        self.test_mode = test_mode

    def enqueue_job(self, job_id: str, service: str, openapi_url: str):
        job = JobInfo(job_id, service, openapi_url)
        self._jobs[job_id] = job
        self._queue.put_nowait(job_id)
        logger.info(f"Job enqueued: {job_id} for service {service}")

    def get_job_status(self, job_id: str) -> Optional[JobInfo]:
        return self._jobs.get(job_id)

    @log_job_execution
    async def process_jobs(self, max_jobs: Optional[int] = None, job_timeout: int = 60):
        processed = 0
        while self._running:
            if self._queue.empty():
                await asyncio.sleep(0.1)
                continue
            job_id = await self._queue.get()
            job = self._jobs.get(job_id)
            if not job:
                self._queue.task_done()
                continue
            if await job.is_cancelled():
                self._queue.task_done()
                logger.info(f"Skipping cancelled job {job_id}")
                continue

            logger.info(f"Processing job {job_id} (service: {job.service})")
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            job.progress = 10

            try:
                if self.test_mode:
                    # Deterministic fast test mode: immediate completion
                    await asyncio.sleep(0.1)  # simulate tiny delay
                    if await job.is_cancelled():
                        job.status = JobStatus.CANCELLED
                        job.error = "Cancelled in test mode"
                    else:
                        job.status = JobStatus.COMPLETED
                        job.progress = 100
                        job.result = {
                            "service": job.service,
                            "version": "test-0.1.0",
                            "import_path": f"{job.service.replace('-', '_')}_client",
                            "local_path": f"/srv/fountainai/clients/{job.service}"
                        }
                    job.completed_at = datetime.utcnow()
                else:
                    # Real mode: run actual subprocess with timeout
                    async with async_timeout.timeout(job_timeout):
                        cmd = [
                            "openapi-python-client",
                            "generate",
                            "--path",
                            job.openapi_url,
                            "--output",
                            f"/srv/fountainai/clients/{job.service}"
                        ]
                        process = await asyncio.create_subprocess_exec(
                            *cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        job._process = process

                        while True:
                            if await job.is_cancelled():
                                process.terminate()
                                job.status = JobStatus.CANCELLED
                                job.error = "Job cancelled by user"
                                job.completed_at = datetime.utcnow()
                                job.progress = 0
                                logger.info(f"Job {job_id} cancelled by user")
                                break

                            retcode = await process.wait()
                            stdout, stderr = await process.communicate()

                            if retcode == 0:
                                job.status = JobStatus.COMPLETED
                                job.progress = 100
                                job.result = {
                                    "service": job.service,
                                    "version": "0.1.0",
                                    "import_path": f"{job.service.replace('-', '_')}_client",
                                    "local_path": f"/srv/fountainai/clients/{job.service}"
                                }
                                job.completed_at = datetime.utcnow()
                                logger.info(f"Job {job_id} completed successfully")
                            else:
                                job.status = JobStatus.FAILED
                                job.error = f"Generation failed: {stderr.decode().strip()}"
                                job.completed_at = datetime.utcnow()
                                logger.error(f"Job {job_id} failed: {job.error}")
                            break

            except asyncio.TimeoutError:
                job.status = JobStatus.FAILED
                job.error = f"Job timed out after {job_timeout} seconds"
                job.completed_at = datetime.utcnow()
                logger.error(f"Job {job_id} timed out")

            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
                job.completed_at = datetime.utcnow()
                logger.error(f"Exception in job {job_id}: {e}", exc_info=True)

            finally:
                job._process = None
                self._queue.task_done()

                try:
                    asyncio.create_task(
                        webhook_manager.notify_webhooks({
                            "job_id": job.job_id,
                            "service": job.service,
                            "status": job.status.value,
                            "submitted_at": job.submitted_at.isoformat(),
                            "started_at": job.started_at.isoformat() if job.started_at else None,
                            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                            "progress": job.progress,
                            "result": job.result,
                            "error": job.error,
                        })
                    )
                except Exception as notify_exc:
                    logger.error(f"Failed to notify webhooks for job {job.job_id}: {notify_exc}")

            processed += 1
            if max_jobs is not None and processed >= max_jobs:
                logger.info(f"Processed max_jobs={max_jobs}, stopping job processor loop")
                break

    def stop_processing(self):
        self._running = False
        logger.info("Job processing loop stopped")

    def cancel_job(self, job_id: str):
        job = self._jobs.get(job_id)
        if not job:
            logger.warning(f"Attempted to cancel nonexistent job {job_id}")
            return
        job.cancel()
        if job._process:
            job._process.terminate()
            logger.info(f"Job {job_id} process terminated")

job_manager = JobManager(test_mode=False)  # default is real mode

def cancel_job(job_id: str):
    job_manager.cancel_job(job_id)
