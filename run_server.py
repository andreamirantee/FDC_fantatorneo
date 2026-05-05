"""Entrypoint per avviare l'app FastAPI con Uvicorn.
Usare questo file come target per PyInstaller (es. pyinstaller --onefile run_server.py).
"""

import os

if __name__ == "__main__":
    # Import ritardato per evitare overhead durante la build
    import uvicorn
    try:
        from app.main import app
    except Exception as e:
        raise SystemExit(f"Errore import app: {e}")

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host=host, port=port, log_level="info")
