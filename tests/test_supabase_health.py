from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_supabase_health_endpoint():
    # Controlla che il backend esponga lo stato del collegamento Supabase.
    response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "supabase" in payload