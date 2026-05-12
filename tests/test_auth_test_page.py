from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_auth_test_page_exists():
    # La pagina di prova serve per verificare login e registrazione dal browser.
    response = client.get("/auth")
    assert response.status_code == 200
    # UI uses Italian text; verify heading exists
    assert "Accedi" in response.text