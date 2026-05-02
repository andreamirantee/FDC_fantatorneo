"""Endpoint health check connessione database Supabase.

Fornisce informazioni disponibilità Supabase Auth e PostgREST
senza eseguire query database.
"""

from fastapi import APIRouter

from ..database import get_supabase_status

# Router health Supabase: status connettività database (sotto prefix /health).
router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/db")
def health_db():
    """Controlla stato connessione database Supabase.
    
    Ritorna status veloce senza query al database:
    - configured: bool (variabili env presenti)
    - connected: bool (client creato con successo)
    - key_source: str (service_role o anon)
    """
    return {"status": "ok", "supabase": get_supabase_status()}