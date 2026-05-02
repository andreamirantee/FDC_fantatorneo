"""Test per pagina mercato con classifica e filtri."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_market_test_page_exists():
    """Verifica che pagina /market-test carica con successo."""
    response = client.get("/market-test")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Mercato Fantasy" in response.text
    assert "Classifica" in response.text
    assert "Partecipanti Disponibili" in response.text


def test_market_test_page_has_tabs():
    """Verifica che pagina ha tab per classifica e mercato."""
    response = client.get("/market-test")
    assert response.status_code == 200
    assert "tab-btn" in response.text
    assert "ranking" in response.text
    assert "market" in response.text


def test_market_test_page_has_filters():
    """Verifica che pagina ha form per filtri."""
    response = client.get("/market-test")
    assert response.status_code == 200
    assert "filterName" in response.text
    assert "filterRole" in response.text
    assert "filterCost" in response.text
    assert "filterTeam" in response.text


def test_market_test_page_has_buy_sell_buttons():
    """Verifica che pagina ha bottoni buy/sell."""
    response = client.get("/market-test")
    assert response.status_code == 200
    assert "btn-buy" in response.text
    assert "btn-sell" in response.text
    assert "buyParticipant" in response.text
    assert "sellParticipant" in response.text
