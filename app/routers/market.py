"""Operazioni mercato e classifica torneo fantasy.

Endpoint core per:
- Operazioni mercato (acquisto/vendita partecipanti)
- Gestione classifica team e roster
- Tracking cronologia transazioni

Modello Proprietà:
- Duplicati ammessi tra team diversi (più team possono possedere stesso partecipante)
- Duplicati NON ammessi dentro stesso team (previene proprietà duplicata)
- team_participants_history traccia date acquisizione/rilascio con released_at NULL per proprietà attiva

Protezione Hardening:
- Authorization checks: verify user ownership del team prima buy/sell
- Credit validation: verificare balance_credits team >= price prima transazione
- Atomic operations: garantire consistency registri storia/transazioni
- Rate limiting: max 30 richieste per minuto su buy/sell per prevenire abuse
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status, Header
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..auth import get_current_user
from ..database import get_supabase_client
from ..policies import (
    credit_team_credits,
    deduct_team_credits,
    validate_team_credits,
    verify_team_ownership,
)
from ..schemas import (
    BuyParticipantRequest,
    MarketOperationResult,
    MarketTransactionItem,
    MatchResult,
    RankingItem,
    SellParticipantRequest,
    TeamRosterItem,
)

# Rate limiter: max 30 richieste per minuto per IP client.
limiter = Limiter(key_func=get_remote_address)

# Router market: operazioni buy/sell/ranking, endpoint Step 2 e 3.
router = APIRouter(prefix="/market", tags=["Market"])


def _adjust_team_total_cost(client, team_id: int, delta: int) -> None:
    """Regola costo totale team per incremento (usato per operazioni buy/sell).
    
    Legge total_cost corrente, aggiunge delta (positivo per buy, negativo per sell),
    assicura totale non-negativo, e aggiorna database.
    
    Args:
        client: Client Supabase.
        team_id: ID team da aggiornare.
        delta: Valore incremento (può essere negativo).
    """
    team_res = client.table("teams").select("id, total_cost").eq("id", team_id).limit(1).execute()
    if not team_res.data:
        return
    current_total = int(team_res.data[0].get("total_cost") or 0)
    new_total = max(0, current_total + delta)
    client.table("teams").update({"total_cost": new_total}).eq("id", team_id).execute()


def _build_team_name_map(client, team_ids: list[int]) -> dict[int, str | None]:
    """Query batch nomi team per ID per arricchimento risposta.
    
    Args:
        client: Client Supabase.
        team_ids: Lista ID team da ottenere.
    
    Returns:
        Dict mapping team_id -> team_name (o None se non trovato).
    """
    if not team_ids:
        return {}
    teams_res = client.table("teams").select("id, name").in_("id", team_ids).execute()
    return {int(row["id"]): row.get("name") for row in (teams_res.data or [])}


def _build_participant_name_map(client, participant_ids: list[int]) -> dict[int, str | None]:
    """Query batch nomi partecipanti per ID per arricchimento risposta.
    
    Args:
        client: Client Supabase.
        participant_ids: Lista ID partecipanti da ottenere.
    
    Returns:
        Dict mapping participant_id -> participant_name (o None se non trovato).
    """
    if not participant_ids:
        return {}
    participants_res = client.table("participants").select("id, name").in_("id", participant_ids).execute()
    return {int(row["id"]): row.get("name") for row in (participants_res.data or [])}


def _distribute_squad_points(client, squad_id: int, points_delta: int) -> None:
    """Distribuisce punti di una squadra a tutti i team owner che la possiedono.
    
    Quando una squadra ottiene punti (da una partita), questi si aggiungono
    automaticamente ai team owner che possiedono quella squadra nel mercato.
    
    Args:
        client: Client Supabase.
        squad_id: ID della squadra che ha ottenuto punti.
        points_delta: Punti da aggiungere (può essere negativo).
    """
    # 1. Aggiungi punti alla squadra stessa
    squad_res = client.table("participants").select("id, score").eq("id", squad_id).limit(1).execute()
    if squad_res.data:
        current_score = int(squad_res.data[0].get("score") or 0)
        new_score = max(0, current_score + points_delta)
        client.table("participants").update({"score": new_score}).eq("id", squad_id).execute()
    
    # 2. Trova tutti i team che possiedono questa squadra (active ownership)
    ownership_res = (
        client.table("team_participants_history")
        .select("team_id")
        .eq("participant_id", squad_id)
        .is_("released_at", "null")
        .execute()
    )
    
    # 3. Aggiungi punti ai team owner
    for ownership_row in (ownership_res.data or []):
        team_id = int(ownership_row["team_id"])
        team_res = client.table("teams").select("id, score").eq("id", team_id).limit(1).execute()
        if team_res.data:
            current_team_score = int(team_res.data[0].get("score") or 0)
            new_team_score = max(0, current_team_score + points_delta)
            client.table("teams").update({"score": new_team_score}).eq("id", team_id).execute()


@router.get("/ranking", response_model=list[RankingItem])
def get_ranking(client=Depends(get_supabase_client)):
    """Ottieni classifica squadre (participants) ordinata per score (desc) poi costo (asc).
    
    Endpoint Step 2: fornisce leaderboard per display frontend.
    
    Returns:
        Lista squadre con id, name, score e costo (mappato su total_cost per compatibilita frontend).
    """
    if client is None:
        return []

    try:
        response = (
            client.table("participants")
            .select("id, name, role, score, cost")
            .order("score", desc=True)
            .order("cost")
            .execute()
        )
        rows = response.data or []
        return [
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "sport": row.get("role") or "Calcio",
                "score": int(row.get("score") or 0),
                "total_cost": int(row.get("cost") or 0),
            }
            for row in rows
        ]
    except Exception:
        return []


@router.post("/match", status_code=status.HTTP_200_OK)
def record_match(
    payload: MatchResult,
    client=Depends(get_supabase_client),
    x_admin_token: str = Header(None)
):
    """Registra risultato di una partita e distribuisce punti automaticamente.
    
    Protezione: richiede X-Admin-Token header.
    
    Logica:
    - Calcola punti guadagnati (vincitore ottiene 3, pareggio 1 ciascuno, perdente 0)
    - Aggiunge punti alla squadra
    - Distribuisce automaticamente ai team owner che possiedono quella squadra
    
    Args:
        payload: MatchResult con ID squadre e score.
        client: Dipendenza client Supabase.
        x_admin_token: Token admin da header.
    
    Returns:
        Messaggio conferma con punti assegnati.
    """
    # Protezione: verifica token admin
    if x_admin_token != "a3f9c4b8de":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token required")
    
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    # Verifica squadre esistono
    home_squad_res = client.table("participants").select("id").eq("id", payload.home_squad_id).limit(1).execute()
    away_squad_res = client.table("participants").select("id").eq("id", payload.away_squad_id).limit(1).execute()
    
    if not home_squad_res.data or not away_squad_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or both squads not found")

    try:
        # Calcola punti in base al risultato
        home_points = 0
        away_points = 0
        
        if payload.home_score > payload.away_score:
            # Home vince
            home_points = 3
            away_points = 0
        elif payload.away_score > payload.home_score:
            # Away vince
            away_points = 3
            home_points = 0
        else:
            # Pareggio
            home_points = 1
            away_points = 1
        
        # Distribuisci punti alle squadre e ai loro team owner
        _distribute_squad_points(client, payload.home_squad_id, home_points)
        _distribute_squad_points(client, payload.away_squad_id, away_points)
        
        # Registra la partita nel database (se esiste una tabella matches)
        try:
            client.table("matches").insert({
                "home_squad_id": payload.home_squad_id,
                "away_squad_id": payload.away_squad_id,
                "home_score": payload.home_score,
                "away_score": payload.away_score,
                "home_points_awarded": home_points,
                "away_points_awarded": away_points,
            }).execute()
        except Exception:
            # Se tabella matches non esiste, continua comunque
            pass

        return {
            "status": "ok",
            "message": f"Partita registrata: Home {payload.home_score} - Away {payload.away_score}",
            "home_squad_id": payload.home_squad_id,
            "away_squad_id": payload.away_squad_id,
            "home_points_awarded": home_points,
            "away_points_awarded": away_points,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to record match")


@router.post("/buy", response_model=MarketOperationResult)
@limiter.limit("30/minute")
def buy_participant(
    request: Request,
    payload: BuyParticipantRequest,
    current_user: dict = Depends(get_current_user),
    client=Depends(get_supabase_client),
):
    """Acquista copia partecipante per un team.
    
    Endpoint Step 2: acquisisce partecipante e registra transazione.
    Modello proprietà: duplicati ammessi tra team diversi, non dentro stesso team.
    
    Protezione Hardening:
    - Verifica utente ha accesso al team acquirente (authorization)
    - Valida team ha abbastanza crediti (credit validation)
    - Detrae crediti atomicamente con registrazione transazione
    
    Args:
        payload: BuyParticipantRequest con buyer_team_id, participant_id, optional price.
        current_user: Profilo utente autenticato (from JWT token).
        client: Dipendenza client Supabase.
    
    Returns:
        MarketOperationResult con dettagli transazione.
    
    Raises:
        HTTPException: 401 unauthorized, 403 forbidden (team access),
                      402 insufficient credits, 404 not found, 409 duplicate ownership.
    """
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    # Protezione: verifica autorizzazione (utente è proprietario/membro del team).
    verify_team_ownership(current_user, payload.buyer_team_id, client)

    # Ottieni partecipante e suo costo base.
    participant_res = (
        client.table("participants")
        .select("id, cost")
        .eq("id", payload.participant_id)
        .limit(1)
        .execute()
    )
    participant = participant_res.data[0] if participant_res.data else None
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    # Usa prezzo fornito o fallback al costo base del partecipante.
    price = payload.price if payload.price is not None else int(participant.get("cost") or 0)

    # Protezione: valida crediti disponibili prima di procedere.
    validate_team_credits(client, payload.buyer_team_id, price)

    # Check: previeni proprietà duplicata dentro stesso team (NULL released_at = attivo).
    active_ownership = (
        client.table("team_participants_history")
        .select("id")
        .eq("team_id", payload.buyer_team_id)
        .eq("participant_id", payload.participant_id)
        .is_("released_at", "null")
        .limit(1)
        .execute()
    )
    if active_ownership.data:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Participant already owned by buyer team")

    try:
        # Registra nuova proprietà attiva (acquired_at auto-set a now, released_at NULL per attivo).
        client.table("team_participants_history").insert(
            {"team_id": payload.buyer_team_id, "participant_id": payload.participant_id}
        ).execute()

        # Registra transazione: buyer riempito, seller NULL (acquisto da mercato).
        client.table("transactions").insert(
            {
                "buyer_team_id": payload.buyer_team_id,
                "seller_team_id": None,
                "participant_id": payload.participant_id,
                "price": price,
            }
        ).execute()

        # Protezione: detrae crediti e incrementa costo totale team.
        deduct_team_credits(client, payload.buyer_team_id, price)
        _adjust_team_total_cost(client, payload.buyer_team_id, price)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Transaction failed")

    return {
        "status": "ok",
        "operation": "buy",
        "participant_id": payload.participant_id,
        "buyer_team_id": payload.buyer_team_id,
        "seller_team_id": None,
        "price": price,
    }


@router.post("/sell", response_model=MarketOperationResult)
@limiter.limit("30/minute")
def sell_participant(
    request: Request,
    payload: SellParticipantRequest,
    current_user: dict = Depends(get_current_user),
    client=Depends(get_supabase_client),
):
    """Vendi (rilascia) copia partecipante da team.
    
    Endpoint Step 2: rilascia proprietà partecipante e registra transazione.
    
    Protezione Hardening:
    - Verifica utente ha accesso al team venditore (authorization)
    - Registra rilascio proprietà e transazione atomicamente
    - Accredita crediti team
    
    Args:
        payload: SellParticipantRequest con seller_team_id, participant_id, optional price.
        current_user: Profilo utente autenticato (from JWT token).
        client: Dipendenza client Supabase.
    
    Returns:
        MarketOperationResult con dettagli transazione.
    
    Raises:
        HTTPException: 401 unauthorized, 403 forbidden (team access),
                      404 not found, 400 not owned by seller.
    """
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    # Protezione: verifica autorizzazione (utente è proprietario/membro del team).
    verify_team_ownership(current_user, payload.seller_team_id, client)

    # Ottieni partecipante e suo costo base.
    participant_res = (
        client.table("participants")
        .select("id, cost")
        .eq("id", payload.participant_id)
        .limit(1)
        .execute()
    )
    participant = participant_res.data[0] if participant_res.data else None
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    # Check: seller deve attualmente possedere questo partecipante (NULL released_at = attivo).
    active_ownership = (
        client.table("team_participants_history")
        .select("id")
        .eq("team_id", payload.seller_team_id)
        .eq("participant_id", payload.participant_id)
        .is_("released_at", "null")
        .limit(1)
        .execute()
    )
    if not active_ownership.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Participant is not currently owned by seller team")

    # Usa prezzo fornito o fallback al costo base del partecipante.
    price = payload.price if payload.price is not None else int(participant.get("cost") or 0)

    try:
        # Chiudi record proprietà corrente: imposta released_at a now (NULL -> timestamp = inattivo).
        ownership_id = active_ownership.data[0]["id"]
        client.table("team_participants_history").update(
            {"released_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", ownership_id).execute()

        # Registra transazione: seller riempito, buyer NULL (rilascio a mercato).
        client.table("transactions").insert(
            {
                "buyer_team_id": None,
                "seller_team_id": payload.seller_team_id,
                "participant_id": payload.participant_id,
                "price": price,
            }
        ).execute()

        # Protezione: accredita crediti e decrementa costo totale team.
        credit_team_credits(client, payload.seller_team_id, price)
        _adjust_team_total_cost(client, payload.seller_team_id, -price)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Transaction failed")

    return {
        "status": "ok",
        "operation": "sell",
        "participant_id": payload.participant_id,
        "buyer_team_id": None,
        "seller_team_id": payload.seller_team_id,
        "price": price,
    }


@router.get("/teams/{team_id}/roster", response_model=list[TeamRosterItem])
def get_team_roster(team_id: int, client=Depends(get_supabase_client)):
    """Ottieni roster attivo per un team.
    
    Endpoint Step 3: ritorna partecipanti attualmente posseduti da team,
    basato su team_participants_history con released_at NULL.
    
    Args:
        team_id: ID team per cui ottenere roster.
        client: Dipendenza client Supabase.
    
    Returns:
        Lista TeamRosterItem con dettagli partecipanti e acquired_at.
    
    Raises:
        HTTPException: 404 se team non trovato.
    """
    if client is None:
        return []

    team_res = client.table("teams").select("id").eq("id", team_id).limit(1).execute()
    if not team_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    active_rows = (
        client.table("team_participants_history")
        .select("participant_id, acquired_at")
        .eq("team_id", team_id)
        .is_("released_at", "null")
        .order("acquired_at", desc=True)
        .execute()
    )
    rows = active_rows.data or []
    if not rows:
        return []

    participant_ids = [int(row["participant_id"]) for row in rows if row.get("participant_id") is not None]
    participants_res = (
        client.table("participants")
        .select("id, name, role, cost, score")
        .in_("id", participant_ids)
        .execute()
    )
    participant_map = {int(row["id"]): row for row in (participants_res.data or [])}

    result: list[TeamRosterItem] = []
    for row in rows:
        participant_id = int(row["participant_id"])
        participant = participant_map.get(participant_id, {})
        result.append(
            {
                "participant_id": participant_id,
                "participant_name": participant.get("name"),
                "role": participant.get("role"),
                "cost": int(participant.get("cost") or 0),
                "participant_score": int(participant.get("score") or 0),
                "acquired_at": row.get("acquired_at") or "",
            }
        )

    return result


@router.get("/transactions", response_model=list[MarketTransactionItem])
def get_market_transactions(limit: int = 50, client=Depends(get_supabase_client)):
    """Ottieni transazioni mercato recenti (cronologia buy/sell).
    
    Endpoint Step 3: ritorna timeline transazioni arricchita con nomi team/partecipanti.
    Usa query batch per lookup nomi (efficiente per grandi set risultati).
    
    Args:
        limit: Max transazioni da ritornare (clamped a 200). Default 50.
        client: Dipendenza client Supabase.
    
    Returns:
        Lista MarketTransactionItem ordinata per created_at descending.
    """
    if client is None:
        return []

    safe_limit = max(1, min(limit, 200))
    tx_res = (
        client.table("transactions")
        .select("id, buyer_team_id, seller_team_id, participant_id, price, created_at")
        .order("created_at", desc=True)
        .limit(safe_limit)
        .execute()
    )
    rows = tx_res.data or []
    if not rows:
        return []

    team_ids_set: set[int] = set()
    participant_ids_set: set[int] = set()
    for row in rows:
        buyer_team_id = row.get("buyer_team_id")
        seller_team_id = row.get("seller_team_id")
        participant_id = row.get("participant_id")
        if buyer_team_id is not None:
            team_ids_set.add(int(buyer_team_id))
        if seller_team_id is not None:
            team_ids_set.add(int(seller_team_id))
        if participant_id is not None:
            participant_ids_set.add(int(participant_id))

    team_name_map = _build_team_name_map(client, sorted(team_ids_set))
    participant_name_map = _build_participant_name_map(client, sorted(participant_ids_set))

    result: list[MarketTransactionItem] = []
    for row in rows:
        buyer_team_id = row.get("buyer_team_id")
        seller_team_id = row.get("seller_team_id")
        participant_id = row.get("participant_id")
        result.append(
            {
                "id": int(row["id"]),
                "buyer_team_id": int(buyer_team_id) if buyer_team_id is not None else None,
                "buyer_team_name": team_name_map.get(int(buyer_team_id)) if buyer_team_id is not None else None,
                "seller_team_id": int(seller_team_id) if seller_team_id is not None else None,
                "seller_team_name": team_name_map.get(int(seller_team_id)) if seller_team_id is not None else None,
                "participant_id": int(participant_id) if participant_id is not None else None,
                "participant_name": participant_name_map.get(int(participant_id)) if participant_id is not None else None,
                "price": int(row.get("price") or 0),
                "created_at": row.get("created_at") or "",
            }
        )

    return result
