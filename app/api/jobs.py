from fastapi import APIRouter, BackgroundTasks, HTTPException, status
import uuid
from app.core.jobs import job_manager, JobStatus
from app.models.schemas import GenerateClientRequest, JobResponse

router = APIRouter()

@router.post("/clients/{service}/jobs", status_code=status.HTTP_202_ACCEPTED, response_model=JobResponse)
async def start_client_generation_job(
    service: str,
    request: GenerateClientRequest,
    background_tasks: BackgroundTasks,
):
    if service != request.service:
        raise HTTPException(status_code=400, detail="Service path and body mismatch")
    job_id = str(uuid.uuid4())
    job_manager.enqueue_job(job_id, service, request.openapi_url)
    background_tasks.add_task(job_manager.process_jobs)
    job_status = job_manager.get_job_status(job_id)
    if job_status is None:
        raise HTTPException(status_code=404, detail="Job not found after creation")
    return JobResponse(
        job_id=job_id,
        status=job_status.status.value,
        submitted_at=job_status.submitted_at.isoformat(),
    )

@router.get("/clients/{service}/jobs/{job_id}")
async def get_job_status(service: str, job_id: str):
    job_status = job_manager.get_job_status(job_id)
    if not job_status or job_status.service != service:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job_status.job_id,
        "service": job_status.service,
        "status": job_status.status.value,
        "submitted_at": job_status.submitted_at.isoformat(),
        "started_at": job_status.started_at.isoformat() if job_status.started_at else None,
        "completed_at": job_status.completed_at.isoformat() if job_status.completed_at else None,
        "progress": job_status.progress,
        "result": job_status.result,
        "error": job_status.error,
    }

@router.delete("/clients/{service}/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_client_generation_job(service: str, job_id: str):
    job_status = job_manager.get_job_status(job_id)
    if not job_status or job_status.service != service:
        raise HTTPException(status_code=404, detail="Job not found")
    cancelled = job_manager.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(status_code=409, detail="Job cannot be cancelled")
    return None
