from fastapi import APIRouter

router = APIRouter(prefix="/mock-webhook")

@router.post("/mock-webhook")
async def receive_webhook():
    return {"message": "Webhook received"}
