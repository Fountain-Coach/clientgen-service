from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from app.core.jobs import job_manager, JobStatus

router = APIRouter()

class ClientInfo(BaseModel):
    service: str
    version: Optional[str] = None
    import_path: Optional[str] = None
    local_path: Optional[str] = None

class ClientListResponse(BaseModel):
    clients: List[ClientInfo]
    page: int
    page_size: int
    total: int

@router.get("/clients/", response_model=ClientListResponse)
async def list_clients(
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
):
    all_clients = [
        ClientInfo(
            service=job.service,
            version=job.result.get("version") if job.result else None,
            import_path=job.result.get("import_path") if job.result else None,
            local_path=job.result.get("local_path") if job.result else None,
        )
        for job in job_manager._jobs.values()
        if job.status == JobStatus.COMPLETED
    ]

    total = len(all_clients)
    start = (page - 1) * page_size
    end = start + page_size
    paged_clients = all_clients[start:end]

    return ClientListResponse(
        clients=paged_clients,
        page=page,
        page_size=page_size,
        total=total,
    )

@router.get("/clients/{service}/import-path")
async def get_import_path(service: str):
    for job in job_manager._jobs.values():
        if job.service == service and job.status == JobStatus.COMPLETED:
            if job.result:
                return {
                    "import_path": job.result.get("import_path"),
                    "local_path": job.result.get("local_path"),
                }
            else:
                raise HTTPException(status_code=404, detail="Client data incomplete")
    raise HTTPException(status_code=404, detail="Client SDK not found")
