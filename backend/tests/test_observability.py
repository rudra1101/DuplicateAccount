from fastapi.testclient import TestClient

from app.database.session import SessionLocal
from app.main import app
from app.services.monitoring_service import get_system_status


client = TestClient(app)


def test_liveness_is_public_and_echoes_request_id():
    request_id = "phase13-liveness-test"
    response = client.get(
        "/api/health/live",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    assert response.headers["X-Request-ID"] == request_id


def test_readiness_checks_database():
    response = client.get("/api/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["checks"]["database"]["status"] == "healthy"
    assert "X-Request-ID" in response.headers


def test_system_status_snapshot_contains_runtime_and_domain_metrics():
    with SessionLocal() as db:
        payload = get_system_status(db)

    assert payload["database"]["status"] == "healthy"
    assert "backend" in payload["database"]
    assert "pool" in payload["database"]
    assert "registeredJobs" in payload["scheduler"]
    assert "integrations" in payload["application"]
    assert "executions" in payload["application"]
    assert isinstance(payload["application"]["accounts"], int)
    assert isinstance(payload["application"]["duplicateCandidates"], int)


def test_metrics_endpoint_exposes_identityai_http_and_operational_metrics():
    client.get("/api/health/live")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "identityai_http_requests_total" in response.text
    assert "identityai_http_request_duration_seconds" in response.text
    assert "identityai_http_requests_in_progress" in response.text
    assert "identityai_scheduler_running" in response.text
    assert "identityai_integrations" in response.text
    assert "identityai_job_executions" in response.text
    assert "identityai_accounts_total_current" in response.text
    assert "identityai_duplicate_candidates_total_current" in response.text


def test_unauthenticated_api_response_still_has_request_id():
    request_id = "phase13-auth-test"
    response = client.get(
        "/api/dashboard",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 401
    assert response.headers["X-Request-ID"] == request_id
