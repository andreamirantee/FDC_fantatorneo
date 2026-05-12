from fastapi import APIRouter
from fastapi.responses import JSONResponse
import os

router = APIRouter(tags=["Debug"])


@router.get("/debug/auth")
def debug_auth():
    """Returns presence/validation of auth-related env vars (masks values).

    Useful for remote debugging without exposing secrets.
    """
    def mask(v: str):
        if not v:
            return None
        if len(v) <= 8:
            return "****"
        return v[:4] + "..." + v[-4:]

    keys = [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_JWT_SECRET",
        "SUPABASE_EMAIL_REDIRECT_TO",
        "CORS_ORIGINS",
    ]

    payload = {"env": {k: mask(os.getenv(k, "")) for k in keys}}
    # Derive a small health summary
    payload["summary"] = {
        "supabase_configured": bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY")),
        "service_role_present": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "email_redirect": bool(os.getenv("SUPABASE_EMAIL_REDIRECT_TO")),
        "cors_origins": os.getenv("CORS_ORIGINS", "")[:200],
    }
    return JSONResponse(payload)
