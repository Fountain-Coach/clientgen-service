from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, HttpUrl
import uuid
from app.core.webhooks import webhook_manager

router = APIRouter()

# Request model for registering a webhook
class WebhookRegistrationRequest(BaseModel):
    callback_url: HttpUrl  # Validated URL where notifications will be sent

# Response model for webhook registration
class WebhookRegistrationResponse(BaseModel):
    webhook_id: str  # Unique identifier assigned to the registered webhook

@router.post("/webhooks", response_model=WebhookRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_webhook(request: WebhookRegistrationRequest):
    """
    Register a webhook callback URL to receive notifications when client generation jobs complete.
    """
    # Create a new webhook ID
    webhook_id = str(uuid.uuid4())
    # Store the webhook URL in the manager
    webhook_manager.add_webhook(webhook_id, request.callback_url)
    # Return the assigned webhook ID
    return WebhookRegistrationResponse(webhook_id=webhook_id)

@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_webhook(webhook_id: str):
    """
    Unregister a webhook, stopping notifications to the associated callback URL.
    """
    # Attempt to remove the webhook; if not found, raise 404
    removed = webhook_manager.remove_webhook(webhook_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Webhook not found")
    # Return 204 No Content on successful deletion
    return
