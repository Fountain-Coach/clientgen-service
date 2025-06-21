from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Literal, Dict
from datetime import datetime

class GenerateClientRequest(BaseModel):
    service: str
    openapi_url: HttpUrl

class JobResponse(BaseModel):
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    submitted_at: datetime

class ClientGenerationResult(BaseModel):
    service: str
    version: Optional[str]
    import_path: str
    local_path: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    submitted_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    progress: Optional[int]
    result: Optional[ClientGenerationResult]
    error: Optional[str]

class ClientListResponse(BaseModel):
    clients: List[ClientGenerationResult]
    page: int
    page_size: int
    total: int

class WebhookRegistrationRequest(BaseModel):
    callback_url: HttpUrl

class WebhookRegistrationResponse(BaseModel):
    webhook_id: str

class ErrorResponse(BaseModel):
    detail: str
