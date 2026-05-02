"""Endpoint health check di base per monitoraggio servizio.

Usati per probe liveness, controlli readiness, e monitoraggio uptime.
"""

from fastapi import APIRouter

# Router health: endpoint status minimali (senza prefix).
router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """Health check liveness del servizio.
    
    Returns:
        Dict stato per monitoraggio uptime e probe readiness.
    """
    return {"status": "ok", "service": "fdc-fantatorneo-api"}