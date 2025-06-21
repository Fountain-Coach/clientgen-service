import os
import pytest

CLIENTS_ROOT = "/srv/fountainai/services/clientgen-service/clients"
SERVICE_NAME = "clientgen-service"
SERVICE_DIR = os.path.join(CLIENTS_ROOT, SERVICE_NAME)

def test_clients_directory_exists():
    assert os.path.isdir(CLIENTS_ROOT), f"Clients root directory does not exist: {CLIENTS_ROOT}"

def test_clients_directory_writable():
    assert os.access(CLIENTS_ROOT, os.W_OK), f"Clients root directory is not writable: {CLIENTS_ROOT}"

def test_service_directory_exists():
    assert os.path.isdir(SERVICE_DIR), f"Service directory does not exist: {SERVICE_DIR}"

def test_service_directory_writable():
    assert os.access(SERVICE_DIR, os.W_OK), f"Service directory is not writable: {SERVICE_DIR}"
