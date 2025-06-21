import os
import logging

logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
CLIENTS_DIR = os.path.join(BASE_DIR, "clients")

def ensure_directory(path: str):
    if not os.path.exists(path):
        logger.info(f"Creating missing directory: {path}")
        os.makedirs(path, exist_ok=True)
    else:
        logger.debug(f"Directory exists: {path}")
    # Check write permission
    if not os.access(path, os.W_OK):
        logger.warning(f"Directory not writable: {path}")
    else:
        logger.debug(f"Directory writable: {path}")

def setup_directories(service_name: str):
    # Ensure base clients dir exists
    ensure_directory(CLIENTS_DIR)

    # Ensure service-specific dir exists
    service_dir = os.path.join(CLIENTS_DIR, service_name)
    ensure_directory(service_dir)
    return service_dir
