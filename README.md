# FountainAI Client Generator Service

[![FountainAI Logo](./assets/fountainai-logo.png)](#) <!-- Placeholder for logo -->

## Overview

The **FountainAI Client Generator Service** is a microservice designed to asynchronously generate Python SDK clients from OpenAPI specifications. This enables dynamic creation and updating of client SDKs for other services, allowing seamless integration and automation within the FountainAI ecosystem.

## Features

- **Asynchronous job-based client generation**: Submit OpenAPI specs and get notified upon client SDK generation.
- **Job management API**: Create, track status, and cancel client generation jobs.
- **Webhook notifications**: Register webhooks to get notified when jobs complete.
- **Client listing and import path retrieval**: Query available generated clients and their import paths.
- **Health endpoint**: Monitor service status.

## Getting Started

### Prerequisites

- Python 3.10+
- Virtual environment recommended (`venv`)
- Docker (optional, if you want containerized deployment)

### Installation

1. Clone the repository:

   git clone <your-repo-url>
   cd clientgen-service

2. Create and activate a virtual environment:

   python -m venv venv
   source venv/bin/activate

3. Install dependencies:

   pip install -r requirements.txt

### Running Locally

Start the service using Uvicorn:

   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

### API Documentation

Once running, access the interactive Swagger UI at:

   http://127.0.0.1:8000/docs

### Service Endpoints Overview

| Endpoint                             | Method | Description                                      |
|------------------------------------|--------|------------------------------------------------|
| /clients/{service}/jobs             | POST   | Start a new client generation job               |
| /clients/{service}/jobs/{job_id}   | GET    | Get status of a client generation job           |
| /clients/{service}/jobs/{job_id}   | DELETE | Cancel a client generation job                   |
| /clients/                          | GET    | List generated clients with pagination           |
| /clients/{service}/import-path     | GET    | Get import path for generated client SDK         |
| /webhooks                         | POST   | Register webhook URL for job completion notifications |
| /webhooks/{webhook_id}             | DELETE | Unregister webhook                               |
| /health                           | GET    | Health check endpoint                            |

## Testing

Run the comprehensive pytest suite with:

   pytest -v --capture=no tests/

---

## Contribution

Contributions and feedback are welcome! Please open issues or pull requests on GitHub.

---

## License

MIT License © FountainAI

---

## Contact

Contexter – main@benedikt-eickhoff.de

---
