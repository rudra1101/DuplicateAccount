from fastapi.testclient import TestClient

from app.main import app


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


def test_metrics_endpoint_exposes_identityai_http_metrics():
    client.get("/api/health/live")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "identityai_http_requests_total" in response.text
    assert "identityai_http_request_duration_seconds" in response.text
    assert "identityai_http_requests_in_progress" in response.text


def test_unauthenticated_api_response_still_has_request_id():
    request_id = "phase13-auth-test"
    response = client.get(
        "/api/dashboard",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 401
    assert response.headers["X-Request-ID"] == request_id
