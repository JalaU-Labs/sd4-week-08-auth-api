from fastapi.testclient import TestClient

from sd4_week_08_auth_api import __version__
from sd4_week_08_auth_api.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["environment"] in {"development", "production", "test"}


def test_ready_returns_ready() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_openapi_schema_exposes_expected_contract() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "SD4 Week 08 Auth API"
    assert schema["info"]["version"] == __version__
    assert schema["info"]["license"]["name"] == "MIT"
    assert "/health" in schema["paths"]
    assert "/ready" in schema["paths"]
    health_op = schema["paths"]["/health"]["get"]
    assert "200" in health_op["responses"]
    health_schema = schema["components"]["schemas"]["HealthResponse"]
    assert set(health_schema["required"]) == {"status", "version", "environment"}


def test_swagger_ui_is_served() -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
