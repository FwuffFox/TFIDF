import os
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_version_endpoint(client, monkeypatch):
    # Test default version
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"version": "1.0.0"}
    
    # Test with custom version in environment variable
    monkeypatch.setenv("APP_VERSION", "2.3.4")
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"version": "2.3.4"}

def test_status_endpoint(client):
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    
def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    # Check if the response contains expected keys
    data = response.json()
    assert "files_processed" in data
    assert "min_processing_time" in data
    assert "max_processing_time" in data
    assert "average_processing_time" in data
    assert "last_processing_time" in data
    assert "latest_file_processed_timestamp" in data