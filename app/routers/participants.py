"""Endpoint di gestione partecipanti (giocatori).

Fornisce operazioni CRUD per partecipanti fantasy. Ritorna liste vuote su
errori database per degradazione corretta.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header

from ..database import get_supabase_client
from ..schemas import ParticipantCreate, ParticipantRead, UpdateParticipantPoints

# Router partecipanti: gestisce listing e creazione giocatori.
router = APIRouter(prefix="/participants", tags=["Participants"])


def verify_admin_token(x_admin_token: str = Header(None)) -> bool:
    """Verifica token admin da header X-Admin-Token.
    
    Per demo: token fisso 'a3f9c4b8de'. In produzione usare JWT dedicato.
    """
    return x_admin_token == "a3f9c4b8de"


@router.get("", response_model=list[ParticipantRead])
def list_participants(client=Depends(get_supabase_client)):
    """Elenca tutti i partecipanti fantasy.
    
    Returns:
        Lista partecipanti ordinati per ID, o lista vuota su errore database.
    """
    if client is None:
        return []

    try:
        response = client.table("participants").select("id, name, role, cost, score, owner_user_ids, composed_of").order("id").execute()
        participants = response.data or []
        for participant in participants:
            participant["owner_user_ids"] = participant.get("owner_user_ids") or []
            participant["available"] = participant.get("available", True)
        return participants
    except Exception:
        try:
            response = client.table("participants").select("id, name, role, cost, owner_user_ids, composed_of").order("id").execute()
            participants = response.data or []
            for participant in participants:
                participant["score"] = 0
                participant["owner_user_ids"] = participant.get("owner_user_ids") or []
                participant["available"] = participant.get("available", True)
            return participants
        except Exception:
            # Degradazione corretta: se database o policy non pronti, ritorna lista vuota.
            return []


@router.post("", response_model=ParticipantRead, status_code=status.HTTP_201_CREATED)
def create_participant(
    payload: ParticipantCreate, 
    client=Depends(get_supabase_client),
    x_admin_token: str = Header(None)
):
    """Crea nuovo partecipante fantasy.
    
    Protezione: richiede X-Admin-Token header.
    
    Args:
        payload: Dati creazione partecipante (name, role, cost, etc.).
        client: Dipendenza client Supabase.
    
    Returns:
        Record partecipante creato.
    
    Raises:
        HTTPException: 403 unauthorized, 503 se Supabase indisponibile, 500 se insert fallisce.
    """
    if not verify_admin_token(x_admin_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token required")
    
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    participant_payload = {
        "name": payload.name,
        "role": payload.role,
        "cost": payload.cost or 0,
        "composed_of": payload.composed_of,
    }
    response = client.table("participants").insert(participant_payload).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to create participant")

    return response.data[0]


@router.delete("/{participant_id}", status_code=status.HTTP_200_OK)
def delete_participant(
    participant_id: int,
    client=Depends(get_supabase_client),
    x_admin_token: str = Header(None)
):
    """Elimina partecipante dal torneo.
    
    Protezione: richiede X-Admin-Token header.
    
    Args:
        participant_id: ID partecipante da eliminare.
        client: Dipendenza client Supabase.
    
    Returns:
        Messaggio conferma eliminazione.
    
    Raises:
        HTTPException: 403 unauthorized, 404 not found, 503 se Supabase indisponibile.
    """
    if not verify_admin_token(x_admin_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token required")
    
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    # Verifica partecipante esiste
    check_response = client.table("participants").select("id").eq("id", participant_id).limit(1).execute()
    if not check_response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    # Elimina partecipante
    client.table("participants").delete().eq("id", participant_id).execute()

    return {"status": "ok", "message": f"Partecipante {participant_id} eliminato"}


@router.patch("/{participant_id}/points", status_code=status.HTTP_200_OK)
def update_participant_points(
    participant_id: int,
    payload: UpdateParticipantPoints,
    client=Depends(get_supabase_client),
    x_admin_token: str = Header(None)
):
    """Aggiorna punti (score) di un partecipante.
    
    Protezione: richiede X-Admin-Token header.
    
    Args:
        participant_id: ID partecipante.
        payload: Nuovo valore punti.
        client: Dipendenza client Supabase.
    
    Returns:
        Partecipante aggiornato.
    
    Raises:
        HTTPException: 403 unauthorized, 404 not found, 503 se Supabase indisponibile.
    """
    if not verify_admin_token(x_admin_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token required")
    
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    # Verifica partecipante esiste
    check_response = client.table("participants").select("id").eq("id", participant_id).limit(1).execute()
    if not check_response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    # Aggiorna punti
    try:
        response = client.table("participants").update({"score": payload.points}).eq("id", participant_id).execute()
    except Exception as error:
        error_message = str(error)
        if "score" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Schema Supabase non allineato: esegui 004_participant_score.sql per aggiungere la colonna score a participants",
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to update participant") from error
    
    if not response.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to update participant")

    return response.data[0]
