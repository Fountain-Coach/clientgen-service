from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, HttpUrl
import uuid
from app.core.webhooks import webhook_manager

router = APIRouter()

class WebhookRegistrationRequest(BaseModel):
    callback_url: HttpUrl

class WebhookRegistrationResponse(BaseModel):
    webhook_id: str

@router.post("/webhooks", response_model=WebhookRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_webhook(request: WebhookRegistrationRequest):
    webhook_id = str(uuid.uuid4())
    webhook_manager.add_webhook(webhook_id, request.callback_url)
    return WebhookRegistrationResponse(webhook_id=webhook_id)

@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_webhook(webhook_id: str):
    removed = webhook_manager.remove_webhook(webhook_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return
