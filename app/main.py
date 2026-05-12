"""Factory applicazione FastAPI e composizione route.

Configura app FastAPI principale con middleware CORS, rate limiting,
carica variabili ambiente, e include tutti i router versionati (auth, market, teams, etc.).

Protezione Hardening:
- CORS middleware: restringe origini CORS da configurazione
- Rate limiting: protegge endpoint da abuse (30 richieste/minuto su buy/sell)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from dotenv import load_dotenv
import os

# Rate limiter globale: max 30 richieste per minuto per IP client.
limiter = Limiter(key_func=get_remote_address)

# Carica variabili d'ambiente una sola volta all'avvio.
load_dotenv()

# Importa tutti i router API.
from .routers.health import router as health_router
from .routers.auth_test import router as auth_test_router
from .routers.auth import router as auth_router
from .routers.supabase_health import router as supabase_health_router
from .routers.participants import router as participants_router
from .routers.users import router as users_router
from .routers.teams import router as teams_router
from .routers.market import router as market_router
from .routers.market_test import router as market_test_router
from .routers.admin_panel import router as admin_panel_router
from .routers.debug_auth import router as debug_auth_router

# Istanza principale dell'applicazione FastAPI: tutti i router vengono inclusi qui.
app = FastAPI(
    title="FDC Fantatorneo API",
    description="Backend per gestione torneo fantasy FDC.",
    version="0.1.0"
)

# Aggiungi rate limiter all'app.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: {"detail": "Rate limit exceeded"})
app.add_middleware(SlowAPIMiddleware)

# Middleware CORS: consente richieste frontend da origini configurate (es. FlutterFlow, localhost).
# Origini configurate sono lette da variabile env CORS_ORIGINS (lista separata da virgole).
origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/", tags=["Root"])
def read_root():
    """Endpoint di check health per root.
    
    Returns:
        Conferma che API è online.
    """
    return {"status": "ok", "message": "Welcome to FDC Fantatorneo API!"}

# Route API versionate: tutti gli endpoint operativi sono sotto /api/v1.
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(supabase_health_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(teams_router, prefix="/api/v1")
app.include_router(participants_router, prefix="/api/v1")
app.include_router(market_router, prefix="/api/v1")
app.include_router(auth_test_router)  # Route playground (senza prefix).
app.include_router(market_test_router)  # Route playground mercato (senza prefix).
app.include_router(admin_panel_router)  # Route admin panel (senza prefix).
app.include_router(debug_auth_router)

# Log info all'avvio.
print("Server started. Allowed origins:", origins)
