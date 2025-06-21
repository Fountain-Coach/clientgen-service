from fastapi import APIRouter

from app.api import clients, webhooks

api_router = APIRouter()
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
