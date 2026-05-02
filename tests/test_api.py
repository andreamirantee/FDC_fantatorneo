from fastapi.testclient import TestClient

from app.main import app


# Client HTTP in-memory per test veloci senza server esterno.
client = TestClient(app)


def test_root_endpoint():
    # Verifica disponibilita endpoint root.
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_endpoint():
    # Verifica endpoint health versionato.
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"