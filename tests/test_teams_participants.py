from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_teams_list_route_exists():
    # Se il route e registrato, senza client Supabase ritorna una lista vuota.
    response = client.get("/api/v1/teams")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_participants_list_route_exists():
    # Se il route e registrato, senza client Supabase ritorna una lista vuota.
    response = client.get("/api/v1/participants")
    assert response.status_code == 200
    assert isinstance(response.json(), list)