from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.main import app


client = TestClient(app)


def setup_function():
    # Isola i test dal DB reale: le rotte devono esistere e rispondere anche senza Supabase.
    app.dependency_overrides[get_supabase_client] = lambda: None


def teardown_function():
    app.dependency_overrides.clear()


def test_market_team_roster_route_exists():
    # Senza client Supabase configurato la rotta deve comunque rispondere con lista.
    response = client.get("/api/v1/market/teams/1/roster")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_market_transactions_route_exists():
    # Senza client Supabase configurato la rotta deve comunque rispondere con lista.
    response = client.get("/api/v1/market/transactions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_market_transactions_route_accepts_limit_query_param():
    # La query limit deve essere accettata e non rompere la risposta.
    response = client.get("/api/v1/market/transactions?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
