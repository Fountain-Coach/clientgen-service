import logging
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.core.jobs import job_manager
from app.api import jobs, clients, webhooks, mock_webhook_receiver

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)8s | %(name)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
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

# Include routers with correct prefixes
app.include_router(jobs.router, prefix="/jobs")
app.include_router(webhooks.router, prefix="/webhooks")
app.include_router(clients.router, prefix="/clients")
app.include_router(mock_webhook_receiver.router, prefix="/mock-webhook")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def landing_page():
    return """
    <html>
        <head>
            <title>FountainAI Client Generator Service</title>
            <style>
                body { font-family: monospace; background: #0d1117; color: #c9d1d9; padding: 2rem; }
                h1 { color: #58a6ff; }
                a { color: #58a6ff; text-decoration: none; margin-right: 1rem; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1>FountainAI Client Generator</h1>
            <p>Welcome to the FountainAI Client Generator Service.</p>
            <nav>
                <a href="/docs" target="_blank" rel="noopener">API Docs</a>
                <a href="https://github.com/your-org/clientgen-service" target="_blank" rel="noopener">GitHub Repo</a>
                <a href="/health">Health Check</a>
            </nav>
        </body>
    </html>
    """
