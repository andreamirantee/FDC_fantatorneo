"""Inizializzazione e configurazione del client database Supabase.

Gestisce caricamento variabili d'ambiente, normalizzazione URL, e creazione client
con strategie di fallback per chiavi service role e anonime.
"""

import os
from typing import Any
from dotenv import load_dotenv

# Carica variabili d'ambiente una sola volta all'avvio.
load_dotenv()

url: str | None = os.environ.get("SUPABASE_URL")
# Chiave service role: preferita per operazioni backend con accesso completo al DB.
service_role_key: str | None = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
# Chiave anonima: fallback se service role non configurata, rispetta RLS policy.
anon_key: str | None = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_KEY")

# Normalizza URL progetto: rimuove slash finali e suffisso /rest/v1 se presente.
# Assicura costruzione URL pulita per endpoint PostgREST e Auth.
supabase_project_url: str | None = None
if url:
    supabase_project_url = url.rstrip("/")
    if supabase_project_url.endswith("/rest/v1"):
        supabase_project_url = supabase_project_url[: -len("/rest/v1")]

# URL endpoint Auth per signup, login, e operazioni token.
supabase_auth_url: str | None = f"{supabase_project_url}/auth/v1" if supabase_project_url else None
# Redirect email confirmazione: dove Supabase reindirizza dopo click su link conferma.
supabase_email_redirect_to: str | None = os.environ.get("SUPABASE_EMAIL_REDIRECT_TO")

supabase: Any = None
# Traccia quale chiave API è in uso: service_role ha più privilegi, anon rispetta RLS.
supabase_key_source: str = "missing"

if supabase_project_url and (service_role_key or anon_key):
    try:
        from supabase import create_client  # pyright: ignore[reportMissingImports]

        # Priorità: usa service role per operazioni admin; fallback a anonima.
        selected_key = service_role_key or anon_key
        supabase_key_source = "service_role" if service_role_key else "anon"
        supabase = create_client(supabase_project_url, selected_key)
    except ModuleNotFoundError:
        # Degradazione corretta: server parte anche senza SDK Supabase.
        supabase = None


def get_supabase_client() -> Any:
    """Ritorna il client Supabase singleton creato all'avvio.
    
    Returns:
        Istanza client Supabase o None se non configurato/inizializzato.
    """
    return supabase


def get_supabase_status() -> dict[str, bool | str]:
    """Ritorna stato di connessione e configurazione Supabase.
    
    Returns:
        dict con chiavi: configured (bool), connected (bool), key_source (str).
    """
    return {
        "configured": supabase_project_url is not None and (service_role_key is not None or anon_key is not None),
        "connected": supabase is not None,
        "key_source": supabase_key_source,
    }


def get_supabase_auth_credentials() -> tuple[str | None, str | None]:
    """Ritorna URL endpoint Auth e chiave API per operazioni login/signup.
    
    Returns:
        Tupla di (auth_url, api_key) per chiamate endpoint Supabase Auth.
    """
    return supabase_auth_url, anon_key or service_role_key


def get_supabase_email_redirect_to() -> str | None:
    """Ritorna URL di redirect conferma email per Supabase.
    
    Returns:
        URL di redirect o None se non configurato in ambiente.
    """
    return supabase_email_redirect_to
