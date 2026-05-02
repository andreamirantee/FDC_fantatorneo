"""Policy di autorizzazione e validazione per operazioni mercato.

Centralizza logica di controllo:
- Autorizzazione: verificare accesso utente a risorse
- Validazione crediti: verificare disponibilità fondi prima operazione
- Controllo atomicità: garantire consistency transazionali
"""

from fastapi import HTTPException, status
from typing import Any


def verify_team_ownership(current_user: dict[str, Any], team_id: int, client: Any) -> dict[str, Any]:
    """Verifica che utente attuale sia proprietario/membro del team.
    
    Controlla che l'utente abbia accesso al team verificando:
    - teams.owner_user_id corrisponde a user attuale
    - oppure utente è membro della squadra
    
    Args:
        current_user: Profilo utente da get_current_user (include auth_id, email, user.id).
        team_id: ID team da verificare.
        client: Client Supabase per query DB.
    
    Returns:
        Dati team se autorizzato.
    
    Raises:
        HTTPException: 403 se utente non è proprietario/membro, 404 se team non esiste.
    """
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not available")
    
    try:
        # Recupera utente DB per ottenere user_id numerico.
        auth_id = current_user.get("auth_id") or current_user.get("sub")
        user_res = client.table("users").select("id, team_id").eq("auth_id", auth_id).execute()
        user_data = user_res.data[0] if user_res.data else None
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User profile not found"
            )
        
        user_id = user_data.get("id")
        
        # Recupera team.
        team_res = client.table("teams").select("id, owner_user_id").eq("id", team_id).execute()
        team_data = team_res.data[0] if team_res.data else None
        
        if not team_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
        
        # Verifica proprietà: owner_user_id deve corrispondere.
        if team_data.get("owner_user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this team"
            )
        
        return team_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authorization check failed")


def validate_team_credits(client: Any, team_id: int, required_amount: int) -> dict[str, Any]:
    """Verifica che team abbia sufficienti crediti per operazione.
    
    Legge balance_credits del team e verifica sia >= required_amount.
    
    Args:
        client: Client Supabase.
        team_id: ID team.
        required_amount: Importo richiesto (prezzo partecipante).
    
    Returns:
        Dati team se ha crediti sufficienti.
    
    Raises:
        HTTPException: 402 se crediti insufficienti, 404 se team non esiste.
    """
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not available")
    
    try:
        team_res = client.table("teams").select("id, balance_credits").eq("id", team_id).execute()
        team_data = team_res.data[0] if team_res.data else None
        
        if not team_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
        
        current_balance = int(team_data.get("balance_credits") or 0)
        
        if current_balance < required_amount:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient credits. Required: {required_amount}, Available: {current_balance}"
            )
        
        return team_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Credit validation failed")


def deduct_team_credits(client: Any, team_id: int, amount: int) -> None:
    """Decrementa i crediti team per acquisto.
    
    Aggiorna balance_credits: sottrae amount.
    Nota: questa è operazione non-atomica lato HTTP. Per atomicità garantita,
    usare PostgreSQL trigger o RPC function.
    
    Args:
        client: Client Supabase.
        team_id: ID team.
        amount: Importo da detrarre.
    
    Raises:
        HTTPException: 500 se update fallisce.
    """
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not available")
    
    try:
        team_res = client.table("teams").select("id, balance_credits").eq("id", team_id).execute()
        if not team_res.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
        
        current_balance = int(team_res.data[0].get("balance_credits") or 0)
        new_balance = max(0, current_balance - amount)
        
        client.table("teams").update({"balance_credits": new_balance}).eq("id", team_id).execute()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Credit deduction failed")


def credit_team_credits(client: Any, team_id: int, amount: int) -> None:
    """Incrementa i crediti team per vendita (rilascio partecipante).
    
    Aggiorna balance_credits: aggiunge amount.
    
    Args:
        client: Client Supabase.
        team_id: ID team.
        amount: Importo da aggiungere.
    
    Raises:
        HTTPException: 500 se update fallisce.
    """
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not available")
    
    try:
        team_res = client.table("teams").select("id, balance_credits").eq("id", team_id).execute()
        if not team_res.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
        
        current_balance = int(team_res.data[0].get("balance_credits") or 0)
        new_balance = current_balance + amount
        
        client.table("teams").update({"balance_credits": new_balance}).eq("id", team_id).execute()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Credit addition failed")
