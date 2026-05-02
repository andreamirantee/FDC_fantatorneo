"""Endpoint profilo utente.

Fornisce accesso autenticato a informazioni profilo utente corrente.
"""

from fastapi import APIRouter, Depends

from ..auth import get_current_user

# Router utente: endpoint informazioni utente autenticato.
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
def read_me(current_user=Depends(get_current_user)):
    """Ottieni profilo utente autenticato corrente.
    
    Returns:
        Dati utente corrente da token JWT e profilo arricchito da database.
    """
    return current_user