import logging
import sys
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.jobs import job_manager
from app.api import jobs, clients, webhooks, mock_webhook_receiver
from app.utils.directory_setup import setup_directories

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)8s | %(name)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

SERVICE_NAME = "clientgen-service"

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Ensuring necessary directories exist")
    setup_directories(SERVICE_NAME)

    logger.info("Starting job processor task on startup")
    task = asyncio.create_task(job_manager.process_jobs())
    app.state.job_processor_task = task
    yield
    logger.info("Stopping job processor task on shutdown")
    job_manager.stop_processing()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Job processor task cancelled cleanly")

app = FastAPI(
    title="FountainAI Client Generator Service",
    version="1.0.0",
    description="Asynchronously generate Python SDK clients from OpenAPI specs.",
    lifespan=lifespan
)

app.include_router(jobs.router)
app.include_router(clients.router)
app.include_router(webhooks.router)
app.include_router(mock_webhook_receiver.router)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def landing_page():
    return {"message": "Welcome to the Client Generator Service"}
