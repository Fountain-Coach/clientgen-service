# Import necessary FastAPI modules and typing helpers
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid
from app.core.jobs import job_manager, JobStatus, cancel_job

# Create an API router instance for grouping jobs-related endpoints
router = APIRouter()

# Pydantic model for the client generation request body
class GenerateClientRequest(BaseModel):
    service: str           # Name of the service for which client is generated
    openapi_url: str       # URL to the OpenAPI spec JSON file

# Pydantic model for the response when a job is accepted
class JobResponse(BaseModel):
    job_id: str            # Unique job identifier (UUID string)
    status: str            # Current job status (pending, running, etc.)
    submitted_at: str      # ISO8601 timestamp when job was submitted

# POST endpoint to start a client generation job asynchronously
@router.post("/clients/{service}/jobs", status_code=status.HTTP_202_ACCEPTED, response_model=JobResponse)
async def start_client_generation_job(
    service: str,
    request: GenerateClientRequest,
    background_tasks: BackgroundTasks,  # FastAPI facility for scheduling async background work
):
    # Ensure path parameter and body service name match
    if service != request.service:
        raise HTTPException(status_code=400, detail="Service path and body mismatch")

    # Generate a new unique job ID using UUID4
    job_id = str(uuid.uuid4())

    # Add the new job to the job manager queue with necessary info
    job_manager.enqueue_job(job_id, service, request.openapi_url)

    # Schedule the async background job processor to run soon (non-blocking)
    background_tasks.add_task(job_manager.process_jobs)

    # Retrieve initial job status object to return
    job_status = job_manager.get_job_status(job_id)

    # Return accepted response with job details
    return JobResponse(
        job_id=job_id,
        status=job_status.status.value,
        submitted_at=job_status.submitted_at.isoformat(),
    )

# GET endpoint to retrieve status and result of a given job
@router.get("/clients/{service}/jobs/{job_id}")
async def get_job_status(service: str, job_id: str):
    # Fetch job info from job manager
    job_status = job_manager.get_job_status(job_id)

    # Validate job exists and belongs to requested service
    if not job_status or job_status.service != service:
        raise HTTPException(status_code=404, detail="Job not found")

    # Return job status and result serialized as dictionary
    return job_status.to_dict()

# DELETE endpoint to cancel a running job
@router.delete("/clients/{service}/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_client_generation_job(service: str, job_id: str):
    # Fetch job status
    job_status = job_manager.get_job_status(job_id)

    # Validate job existence and ownership
    if not job_status or job_status.service != service:
        raise HTTPException(status_code=404, detail="Job not found")

    # If job is already completed or failed, cancellation is not possible
    if job_status.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
        raise HTTPException(status_code=409, detail="Cannot cancel completed or failed job")

    # Call cancel logic in job manager to terminate job processing
    cancel_job(job_id)

    # Return 204 No Content to indicate successful cancellation
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)
