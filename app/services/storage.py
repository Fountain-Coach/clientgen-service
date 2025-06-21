import os

def get_clients_dir() -> str:
    return os.getenv("CLIENTGEN_CLIENTS_DIR", "/srv/fountainai/clients")

def get_status_dir() -> str:
    return os.getenv("CLIENTGEN_STATUS_DIR", "/srv/fountainai/clients/status")
