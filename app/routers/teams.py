"""Endpoint di gestione team.

Fornisce operazioni CRUD per team fantasy. Ritorna liste vuote su errori
database per degradazione corretta.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header

from ..database import get_supabase_client
from ..auth import get_current_user
from ..policies import verify_team_ownership
from ..schemas import TeamCreate, TeamRead, UpdateTeamName, UpdateTeamScore

# Router team: gestisce listing e creazione team.
router = APIRouter(prefix="/teams", tags=["Teams"])


def verify_admin_token(x_admin_token: str = Header(None)) -> bool:
    """Verifica token admin da header X-Admin-Token.
    
    Per demo: token fisso 'a3f9c4b8de'. In produzione usare JWT dedicato.
    """
    return x_admin_token == "a3f9c4b8de"


@router.get("", response_model=list[TeamRead])
def list_teams(client=Depends(get_supabase_client)):
    """Elenca tutti i team fantasy.
    
    Returns:
        Lista team ordinati per ID, o lista vuota su errore database.
    """
    if client is None:
        return []

    try:
        response = (
            client.table("teams")
            .select("id, name, owner_user_id, total_cost, score, balance_credits")
            .order("id")
            .execute()
        )
        rows = response.data or []
        for row in rows:
            current_balance = row.get("balance_credits")
            total_cost = int(row.get("total_cost") or 0)
            if current_balance is None or (int(current_balance or 0) == 0 and total_cost == 0):
                try:
                    client.table("teams").update({"balance_credits": 100}).eq("id", row.get("id")).execute()
                    row["balance_credits"] = 100
                except Exception:
                    pass
        return rows
    except Exception:
        # Degradazione corretta: se database o policy non pronti, ritorna lista vuota.
        return []


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
def create_team(payload: TeamCreate, client=Depends(get_supabase_client)):
    """Crea nuovo team fantasy.
    
    Args:
        payload: Dati creazione team (name, owner_user_id).
        client: Dipendenza client Supabase.
    
    Returns:
        Record team creato.
    
    Raises:
        HTTPException: 503 se Supabase indisponibile, 500 se insert fallisce.
    """
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    response = client.table("teams").insert(
        {"name": payload.name, "owner_user_id": payload.owner_user_id, "balance_credits": 100}
    ).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to create team")

    return response.data[0]


@router.patch("/{team_id}/score", status_code=status.HTTP_200_OK)
def update_team_score(
    team_id: int,
    payload: UpdateTeamScore,
    client=Depends(get_supabase_client),
    x_admin_token: str = Header(None)
):
    """Aggiorna score (classifica) di un team.
    
    Protezione: richiede X-Admin-Token header.
    
    Args:
        team_id: ID team.
        payload: Nuovo valore score.
        client: Dipendenza client Supabase.
    
    Returns:
        Team aggiornato.
    
    Raises:
        HTTPException: 403 unauthorized, 404 not found, 503 se Supabase indisponibile.
    """
    if not verify_admin_token(x_admin_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token required")
    
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    # Verifica team esiste
    check_response = client.table("teams").select("id").eq("id", team_id).limit(1).execute()
    if not check_response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    # Aggiorna score
    response = client.table("teams").update({"score": payload.score}).eq("id", team_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to update team")

    return response.data[0]


@router.patch("/{team_id}/name", status_code=status.HTTP_200_OK)
def update_team_name(
    team_id: int,
    payload: UpdateTeamName,
    current_user=Depends(get_current_user),
    client=Depends(get_supabase_client),
):
    """Aggiorna il nome del team per l'utente proprietario."""
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    # Verifica che l'utente sia proprietario del team.
    verify_team_ownership(current_user, team_id, client)

    new_name = (payload.name or "").strip()
    if not new_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Team name is required")

    try:
        response = client.table("teams").update({"name": new_name}).eq("id", team_id).execute()
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to update team")

    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    return response.data[0]
