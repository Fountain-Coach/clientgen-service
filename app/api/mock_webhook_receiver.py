from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

# In-memory store for received webhook events (for testing)
received_events = []

@router.post("/mock-webhook")
async def receive_webhook(request: Request):
    payload = await request.json()
    received_events.append(payload)
    return JSONResponse(content={"received": True})
