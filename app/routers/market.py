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

from fastapi import APIRouter, Depends, HTTPException, Request, status, Header, Body
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
    AdminUpdateParticipantRequest,
    AdminUpdateTeamRequest,
    AdminAssignBonusRequest,
    AdminRemoveBonusRequest,
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
    """Distribuisce punti di una squadra ai team owner che la possiedono.
    
    Quando una squadra ottiene punti (da una partita), questi si aggiungono
    automaticamente ai team owner che possiedono quella squadra nel mercato.
    
    Args:
        client: Client Supabase.
        squad_id: ID della squadra che ha ottenuto punti.
        points_delta: Punti da aggiungere (può essere negativo).
    """
    # 1. Trova tutti i team che possiedono questa squadra (active ownership)
    ownership_res = (
        client.table("team_participants_history")
        .select("team_id")
        .eq("participant_id", squad_id)
        .is_("released_at", "null")
        .execute()
    )
    
    # 2. Aggiungi punti ai team owner
    for ownership_row in (ownership_res.data or []):
        team_id = int(ownership_row["team_id"])
        team_res = client.table("teams").select("id, score").eq("id", team_id).limit(1).execute()
        if team_res.data:
            current_team_score = int(team_res.data[0].get("score") or 0)
            new_team_score = max(0, current_team_score + points_delta)
            client.table("teams").update({"score": new_team_score}).eq("id", team_id).execute()


def _get_active_team_ids_for_participant(client, participant_id: int) -> list[int]:
    """Restituisce i team che possiedono attivamente la squadra (released_at NULL)."""
    ownership_res = (
        client.table("team_participants_history")
        .select("team_id")
        .eq("participant_id", participant_id)
        .is_("released_at", "null")
        .execute()
    )
    return [int(row.get("team_id")) for row in (ownership_res.data or []) if row.get("team_id") is not None]


def _insert_bonus_rows(
    client,
    team_ids: list[int],
    participant_id: int,
    bonus_name: str,
    points: int,
    reason: str | None,
    sport: str | None,
) -> list[int]:
    """Inserisce bonus per ogni team_id e ritorna gli ID delle righe inserite."""
    if not team_ids:
        return []

    now_iso = datetime.now(timezone.utc).isoformat()
    payload = [
        {
            "team_id": team_id,
            "participant_id": participant_id,
            "name": bonus_name,
            "points": points,
            "reason": reason,
            "sport": sport,
            "awarded_at": now_iso,
            "is_active": True,
        }
        for team_id in team_ids
    ]
    try:
        print(f"[_insert_bonus_rows] Inserting {len(payload)} bonus rows for participant {participant_id}, teams {team_ids}")
        res = client.table("bonus").insert(payload).execute()
        inserted_ids = [int(row.get("id")) for row in (res.data or []) if row.get("id") is not None]
        print(f"[_insert_bonus_rows] Inserted {len(inserted_ids)} rows, res.data: {res.data}")
        return inserted_ids
    except Exception as e:
        print(f"[_insert_bonus_rows] Insert failed: {e}")
        raise


def _apply_match_stats(client, squad_id: int, sport: str | None, points_delta: int, scored: int, conceded: int, result: str = "win", stat_delta: int = 1) -> None:
    """Aggiorna statistiche squadra (participants) e punti classifica.
    
    result: "win", "loss", o "draw"
    Per Calcio: goals_for/goals_against.
    Per Pallavolo/Padel: sets_won/sets_lost (usa scored/conceded).
    """
    squad_res = (
        client.table("participants")
        .select("id, score, matches_played, goals_for, goals_against, sets_won, sets_lost, wins, losses, draws")
        .eq("id", squad_id)
        .limit(1)
        .execute()
    )
    if not squad_res.data:
        return

    row = squad_res.data[0]
    current_score = int(row.get("score") or 0)
    matches_played = max(0, int(row.get("matches_played") or 0) + stat_delta)
    update_payload = {
        "score": max(0, current_score + points_delta),
        "matches_played": matches_played,
    }

    # Traccia vittorie/sconfitte/pareggi
    if result == "win":
        update_payload["wins"] = max(0, int(row.get("wins") or 0) + stat_delta)
    elif result == "loss":
        update_payload["losses"] = max(0, int(row.get("losses") or 0) + stat_delta)
    elif result == "draw":
        update_payload["draws"] = max(0, int(row.get("draws") or 0) + stat_delta)

    sport_key = (sport or "").strip().lower()
    if sport_key == "calcio":
        update_payload["goals_for"] = max(0, int(row.get("goals_for") or 0) + scored)
        update_payload["goals_against"] = max(0, int(row.get("goals_against") or 0) + conceded)
    else:
        update_payload["sets_won"] = max(0, int(row.get("sets_won") or 0) + scored)
        update_payload["sets_lost"] = max(0, int(row.get("sets_lost") or 0) + conceded)

    try:
        client.table("participants").update(update_payload).eq("id", squad_id).execute()
    except Exception:
        pass


def _volley_match_points(home_score: int, away_score: int) -> tuple[int, int]:
    if home_score > away_score:
        return 3, 1
    if away_score > home_score:
        return 1, 3
    return 2, 2


def _compute_head_to_head_points(matches: list[dict], team_ids: set[int]) -> dict[int, int]:
    points_map = {team_id: 0 for team_id in team_ids}
    for match in matches:
        home_id = match.get("home_squad_id")
        away_id = match.get("away_squad_id")
        if home_id in team_ids and away_id in team_ids:
            home_score = int(match.get("home_score") or 0)
            away_score = int(match.get("away_score") or 0)
            home_points, away_points = _volley_match_points(home_score, away_score)
            points_map[home_id] = points_map.get(home_id, 0) + home_points
            points_map[away_id] = points_map.get(away_id, 0) + away_points
    return points_map


def _sort_group_teams(teams: list[dict], matches: list[dict]) -> list[dict]:
    grouped: dict[int, list[dict]] = {}
    for team in teams:
        grouped.setdefault(int(team.get("points") or 0), []).append(team)

    sorted_points = sorted(grouped.keys(), reverse=True)
    ordered: list[dict] = []
    for points in sorted_points:
        tied = grouped[points]
        if len(tied) == 1:
            ordered.extend(tied)
            continue

        tied_ids = {int(t.get("id")) for t in tied if t.get("id") is not None}
        head_to_head = _compute_head_to_head_points(matches, tied_ids)
        tied_sorted = sorted(
            tied,
            key=lambda t: (
                -head_to_head.get(int(t.get("id")), 0),
                -int(t.get("sets_won") or 0),
                int(t.get("sets_lost") or 0),
                (t.get("name") or ""),
            ),
        )
        ordered.extend(tied_sorted)

    return ordered


def _find_final_match(matches: list[dict], home_id: int | None, away_id: int | None) -> dict | None:
    if home_id is None or away_id is None:
        return None
    for match in matches:
        m_home = match.get("home_squad_id")
        m_away = match.get("away_squad_id")
        if {m_home, m_away} == {home_id, away_id}:
            return match
    return None


def _normalize_sport_key(sport: str | None) -> str:
    sport_key = (sport or "").strip().lower()
    if sport_key == "volley":
        return "pallavolo"
    return sport_key


def _sport_structure_config(sport: str | None) -> dict:
    sport_key = _normalize_sport_key(sport)
    return {
        "calcio": {"label": "Calcio", "role": "calcio", "group_size": 3, "final_pairs": 3},
        "pallavolo": {"label": "Pallavolo", "role": "pallavolo", "group_size": 3, "final_pairs": 3},
        "padel": {"label": "Padel", "role": "padel", "group_size": 6, "final_pairs": 6},
    }.get(sport_key, {"label": "Pallavolo", "role": "pallavolo", "group_size": 3, "final_pairs": 3})


def _final_label(index: int) -> str:
    start = index * 2 + 1
    end = start + 1
    return f"Finale {start}/{end}"


def _sort_group_teams(teams: list[dict], matches: list[dict], sport: str | None) -> list[dict]:
    grouped: dict[int, list[dict]] = {}
    for team in teams:
        grouped.setdefault(int(team.get("points") or 0), []).append(team)

    sport_key = _normalize_sport_key(sport)
    ordered: list[dict] = []
    for points in sorted(grouped.keys(), reverse=True):
        tied = grouped[points]
        if len(tied) == 1:
            ordered.extend(tied)
            continue

        tied_ids = {int(t.get("id")) for t in tied if t.get("id") is not None}
        head_to_head = _compute_head_to_head_points(matches, tied_ids)

        def tie_break_key(team: dict) -> tuple:
            team_id = int(team.get("id") or 0)
            if sport_key == "calcio":
                goal_diff = int(team.get("goals_for") or 0) - int(team.get("goals_against") or 0)
                return (
                    -head_to_head.get(team_id, 0),
                    -goal_diff,
                    -int(team.get("goals_for") or 0),
                    (team.get("name") or ""),
                )

            return (
                -head_to_head.get(team_id, 0),
                -int(team.get("sets_won") or 0),
                int(team.get("sets_lost") or 0),
                (team.get("name") or ""),
            )

        ordered.extend(sorted(tied, key=tie_break_key))

    return ordered


def _build_sport_structure(client, sport: str | None) -> dict:
    config = _sport_structure_config(sport)
    empty = {
        "sport": config["label"],
        "groups": {"A": [], "B": []},
        "finals": [],
    }
    if client is None:
        return empty

    try:
        participants_res = (
            client.table("participants")
            .select("id, name, role, score, group_code, matches_played, wins, losses, draws, goals_for, goals_against, sets_won, sets_lost, composed_of")
            .ilike("role", config["role"])
            .execute()
        )
        participants = participants_res.data or []
    except Exception:
        return empty

    teams = []
    for row in participants:
        teams.append(
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "sport": row.get("role") or config["label"],
                "group_code": (row.get("group_code") or "").upper() or None,
                "points": int(row.get("score") or 0),
                "matches_played": int(row.get("matches_played") or 0),
                "wins": int(row.get("wins") or 0),
                "losses": int(row.get("losses") or 0),
                "draws": int(row.get("draws") or 0),
                "goals_for": int(row.get("goals_for") or 0),
                "goals_against": int(row.get("goals_against") or 0),
                "sets_won": int(row.get("sets_won") or 0),
                "sets_lost": int(row.get("sets_lost") or 0),
                "composed_of": row.get("composed_of"),
            }
        )

    try:
        matches_res = (
            client.table("matches")
            .select("home_squad_id, away_squad_id, home_score, away_score, stage, group_code, created_at")
            .ilike("sport", config["role"])
            .order("created_at", desc=True)
            .execute()
        )
        matches = matches_res.data or []
    except Exception:
        matches = []

    group_matches = [m for m in matches if (m.get("stage") or "group") == "group"]
    final_matches = [m for m in matches if (m.get("stage") or "") == "final"]

    def build_group(code: str) -> list[dict]:
        group_code = code.upper()
        group_teams = [t for t in teams if (t.get("group_code") or "") == group_code]
        group_match_list = [m for m in group_matches if (m.get("group_code") or "").upper() == group_code]
        return _sort_group_teams(group_teams, group_match_list, config["role"])

    group_a = build_group("A")
    group_b = build_group("B")

    if not group_a and not group_b and teams:
        ordered_teams = _sort_group_teams(teams, [], config["role"])
        group_a = ordered_teams[: config["group_size"]]
        group_b = ordered_teams[config["group_size"] : config["group_size"] * 2]

    # Build finals: prefer cross-group pairs (A vs B). If a group slot is missing,
    # fill it from overall placement ordering so finals always include teams based
    # on their piazzamenti.
    finals: list[dict] = []
    # overall ordering used to fill missing slots (exclude matches head-to-head within groups)
    ordered_teams = _sort_group_teams(teams, group_matches, config["role"]) if teams else []
    # track used ids to avoid duplicates when filling
    used_ids: set[int] = {int(t.get("id")) for t in (group_a + group_b) if t and t.get("id") is not None}

    for index in range(config["final_pairs"]):
        home = group_a[index] if len(group_a) > index else None
        away = group_b[index] if len(group_b) > index else None

        # fill missing home/away from ordered_teams (by placement)
        def _pick_next(exclude: set[int]) -> dict | None:
            for cand in ordered_teams:
                cid = int(cand.get("id") or 0)
                if cid and cid not in exclude:
                    exclude.add(cid)
                    return cand
            return None

        if home is None:
            home = _pick_next(used_ids)
        else:
            used_ids.add(int(home.get("id") or 0))

        if away is None:
            away = _pick_next(used_ids)
        else:
            used_ids.add(int(away.get("id") or 0))

        match = _find_final_match(
            final_matches,
            home.get("id") if home else None,
            away.get("id") if away else None,
        )

        finals.append({"label": _final_label(index), "home": home, "away": away, "match": match})

    return {"sport": config["label"], "groups": {"A": group_a, "B": group_b}, "finals": finals}


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
            .select("id, name, role, score, cost, composed_of")
            .order("score", desc=True)
            .order("cost")
            .execute()
        )
        rows = response.data or []
        
        # Recupera statistiche se disponibili
        participant_ids = [row.get("id") for row in rows]
        stats_map = {}
        if participant_ids:
            try:
                stats_res = client.table("participants").select(
                    "id, group_code, matches_played, goals_for, goals_against, sets_won, sets_lost, wins, losses, draws"
                ).in_("id", participant_ids).execute()
                stats_map = {int(s["id"]): s for s in (stats_res.data or [])}
            except Exception:
                pass
        
        return [
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "sport": row.get("role") or "Calcio",
                "role": row.get("role") or "Calcio",
                "group_code": stats_map.get(row.get("id"), {}).get("group_code"),
                "score": int(row.get("score") or 0),
                "points": int(row.get("score") or 0),
                "total_cost": int(row.get("cost") or 0),
                "matches_played": int(stats_map.get(row.get("id"), {}).get("matches_played") or 0),
                "wins": int(stats_map.get(row.get("id"), {}).get("wins") or 0),
                "losses": int(stats_map.get(row.get("id"), {}).get("losses") or 0),
                "draws": int(stats_map.get(row.get("id"), {}).get("draws") or 0),
                "goals_for": int(stats_map.get(row.get("id"), {}).get("goals_for") or 0),
                "goals_against": int(stats_map.get(row.get("id"), {}).get("goals_against") or 0),
                "sets_won": int(stats_map.get(row.get("id"), {}).get("sets_won") or 0),
                "sets_lost": int(stats_map.get(row.get("id"), {}).get("sets_lost") or 0),
                "composed_of": row.get("composed_of"),
            }
            for row in rows
        ]
    except Exception as e:
        print(f"Errore ranking: {e}")
        return []


@router.get("/structure/{sport_key}")
def get_sport_structure(sport_key: str, client=Depends(get_supabase_client)):
    """Ritorna struttura gironi e finali per lo sport richiesto."""
    return _build_sport_structure(client, sport_key)


@router.get("/volley/structure")
def get_volley_structure(client=Depends(get_supabase_client)):
    """Compatibilità retroattiva per la struttura pallavolo."""
    return _build_sport_structure(client, "pallavolo")


@router.post("/admin/bonus")
def admin_assign_bonus(
    payload: AdminAssignBonusRequest,
    client=Depends(get_supabase_client),
    x_admin_token: str = Header(None),
):
    """Assegna un bonus/malus: aggiorna score squadra e registra in tabella bonus."""
    if x_admin_token != "a3f9c4b8de":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token required")

    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    participant_res = (
        client.table("participants")
        .select("id, score, role")
        .eq("id", payload.participant_id)
        .limit(1)
        .execute()
    )
    if not participant_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    participant = participant_res.data[0]
    team_ids = _get_active_team_ids_for_participant(client, payload.participant_id)
    print(f"[admin_assign_bonus] Team IDs for participant {payload.participant_id}: {team_ids}")
    if not team_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No team owns this participant; bonus not recorded",
        )

    current_score = int(participant.get("score") or 0)
    new_score = max(0, current_score + int(payload.points))
    bonus_name = (payload.name or "Bonus").strip() or "Bonus"
    bonus_reason = payload.reason or bonus_name
    bonus_sport = payload.sport or participant.get("role")

    inserted_ids: list[int] = []
    try:
        inserted_ids = _insert_bonus_rows(
            client,
            team_ids,
            payload.participant_id,
            bonus_name,
            int(payload.points),
            bonus_reason,
            bonus_sport,
        )
        print(
            f"[admin_assign_bonus] Inserted {len(inserted_ids)} bonus rows for participant {payload.participant_id}"
        )
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to insert bonus rows")

    if not inserted_ids:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No bonus rows inserted - check team ownership")

    try:
        client.table("participants").update({"score": new_score}).eq("id", payload.participant_id).execute()
    except Exception:
        # Rollback bonus rows if score update fails.
        try:
            client.table("bonus").delete().in_("id", inserted_ids).execute()
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update participant score")

    return {
        "status": "ok",
        "participant_id": payload.participant_id,
        "updated_score": new_score,
        "team_ids": team_ids,
        "bonus_rows": len(inserted_ids),
        "bonus_ids": inserted_ids,
    }


@router.get("/admin/bonus")
def admin_list_bonus(
    participant_id: int,
    client=Depends(get_supabase_client),
    x_admin_token: str = Header(None),
):
    """Lista bonus/malus attivi per una squadra (admin)."""
    if x_admin_token != "a3f9c4b8de":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token required")

    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    try:
        res = (
            client.table("bonus")
            .select("id, team_id, participant_id, name, points, reason, sport, awarded_at, is_active")
            .eq("participant_id", participant_id)
            .eq("is_active", True)
            .order("awarded_at", desc=True)
            .execute()
        )
        return res.data or []
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load bonuses")


@router.post("/admin/bonus/remove")
def admin_remove_bonus(
    payload: AdminRemoveBonusRequest,
    client=Depends(get_supabase_client),
    x_admin_token: str = Header(None),
):
    """Rimuove un bonus/malus: aggiorna score e cancella il bonus dalla tabella."""
    if x_admin_token != "a3f9c4b8de":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token required")

    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    removed_ids: list[int] = []

    if payload.bonus_id is not None:
        bonus_res = (
            client.table("bonus")
            .select("id, participant_id, points, is_active")
            .eq("id", payload.bonus_id)
            .limit(1)
            .execute()
        )
        if not bonus_res.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bonus not found")

        bonus_row = bonus_res.data[0]
        participant_id = int(bonus_row.get("participant_id") or 0)
        points = int(bonus_row.get("points") or 0)

        participant_res = (
            client.table("participants")
            .select("id, score")
            .eq("id", participant_id)
            .limit(1)
            .execute()
        )
        if not participant_res.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

        current_score = int(participant_res.data[0].get("score") or 0)
        new_score = max(0, current_score - points)

        try:
            delete_res = client.table("bonus").delete().eq("id", payload.bonus_id).execute()
            if not delete_res.data:
                # Verifica esplicita: se la riga esiste ancora, la cancellazione non e' riuscita
                check_res = (
                    client.table("bonus")
                    .select("id")
                    .eq("id", payload.bonus_id)
                    .limit(1)
                    .execute()
                )
                if check_res.data:
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Bonus not removed")
            removed_ids.append(int(payload.bonus_id))
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete bonus")

        try:
            client.table("participants").update({"score": new_score}).eq("id", participant_id).execute()
        except Exception:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update participant score")

        return {
            "status": "ok",
            "participant_id": participant_id,
            "updated_score": new_score,
            "removed_bonus": len(removed_ids),
        }

    if payload.participant_id is None or payload.name is None or payload.points is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing bonus removal data")

    participant_res = (
        client.table("participants")
        .select("id, score")
        .eq("id", payload.participant_id)
        .limit(1)
        .execute()
    )
    if not participant_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    participant = participant_res.data[0]
    current_score = int(participant.get("score") or 0)
    new_score = max(0, current_score - int(payload.points))

    team_ids = _get_active_team_ids_for_participant(client, payload.participant_id)
    bonus_name = (payload.name or "Bonus").strip() or "Bonus"

    for team_id in team_ids:
        try:
            bonus_query = (
                client.table("bonus")
                .select("id, is_active")
                .eq("team_id", team_id)
                .eq("participant_id", payload.participant_id)
                .eq("name", bonus_name)
                .eq("points", int(payload.points))
                .eq("is_active", True)
            )
            if payload.reason:
                bonus_query = bonus_query.eq("reason", payload.reason)

            bonus_res = bonus_query.order("awarded_at", desc=True).limit(1).execute()
            if bonus_res.data:
                bonus_id = bonus_res.data[0].get("id")
                if bonus_id is not None:
                    try:
                        delete_res = client.table("bonus").delete().eq("id", bonus_id).execute()
                        if delete_res.data:
                            removed_ids.append(int(bonus_id))
                    except Exception:
                        continue
        except Exception:
            continue

    try:
        client.table("participants").update({"score": new_score}).eq("id", payload.participant_id).execute()
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update participant score")

    return {
        "status": "ok",
        "participant_id": payload.participant_id,
        "updated_score": new_score,
        "removed_bonus": len(removed_ids),
    }


@router.post("/ranking/reset", status_code=status.HTTP_200_OK)
def reset_ranking(
    client=Depends(get_supabase_client),
    x_admin_token: str = Header(None)
):
    """Resetta punteggi e statistiche delle classifiche.

    Protezione: richiede X-Admin-Token header.
    """
    if x_admin_token != "a3f9c4b8de":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token required")

    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    try:
        client.table("participants").update(
            {
                "score": 0,
                "matches_played": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "goals_for": 0,
                "goals_against": 0,
                "sets_won": 0,
                "sets_lost": 0,
            }
        ).execute()
        client.table("teams").update({"score": 0}).execute()
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to reset ranking")

    return {"status": "ok", "message": "Ranking reset"}


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
    home_squad_res = (
        client.table("participants")
        .select("id, role, group_code")
        .eq("id", payload.home_squad_id)
        .limit(1)
        .execute()
    )
    away_squad_res = (
        client.table("participants")
        .select("id, role, group_code")
        .eq("id", payload.away_squad_id)
        .limit(1)
        .execute()
    )
    
    if not home_squad_res.data or not away_squad_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or both squads not found")

    try:
        # Calcola punti in base al risultato e sport
        home_points = 0
        away_points = 0

        home_role = (home_squad_res.data[0].get("role") or "Calcio").strip().lower()
        away_role = (away_squad_res.data[0].get("role") or "Calcio").strip().lower()
        requested_sport = (payload.sport or "").strip().lower() if hasattr(payload, "sport") else ""
        sport_key = requested_sport or home_role or away_role or "calcio"

        if sport_key == "calcio":
            if payload.home_score > payload.away_score:
                home_points = 3
            elif payload.away_score > payload.home_score:
                away_points = 3
            else:
                home_points = 1
                away_points = 1
        elif sport_key == "pallavolo":
            if payload.home_score > payload.away_score:
                home_points = 3
                away_points = 1
            elif payload.away_score > payload.home_score:
                home_points = 1
                away_points = 3
            else:
                home_points = 2
                away_points = 2
        elif sport_key == "padel":
            if payload.home_score > payload.away_score:
                home_points = 3
                away_points = 1
            elif payload.away_score > payload.home_score:
                home_points = 1
                away_points = 3
            else:
                home_points = 2
                away_points = 2
        else:
            if payload.home_score > payload.away_score:
                home_points = 1
                away_points = 0
            elif payload.away_score > payload.home_score:
                home_points = 0
                away_points = 1
            else:
                home_points = 1
                away_points = 1

        if payload.home_score > payload.away_score:
            home_result = "win"
            away_result = "loss"
        elif payload.away_score > payload.home_score:
            home_result = "loss"
            away_result = "win"
        else:
            home_result = "draw"
            away_result = "draw"
        
        stage = (payload.stage or "group").strip().lower()
        if stage not in {"group", "final"}:
            stage = "group"

        home_group = home_squad_res.data[0].get("group_code")
        away_group = away_squad_res.data[0].get("group_code")
        match_group = None
        if stage == "group" and home_group and home_group == away_group:
            match_group = home_group

        # Aggiorna statistiche squadre e punti classifica
        _apply_match_stats(
            client,
            payload.home_squad_id,
            sport_key,
            home_points,
            payload.home_score,
            payload.away_score,
            home_result,
        )
        _apply_match_stats(
            client,
            payload.away_squad_id,
            sport_key,
            away_points,
            payload.away_score,
            payload.home_score,
            away_result,
        )

        # Distribuisci punti ai team owner
        _distribute_squad_points(client, payload.home_squad_id, home_points)
        _distribute_squad_points(client, payload.away_squad_id, away_points)
        
        # Registra la partita nel database (se esiste una tabella matches)
        try:
            client.table("matches").insert({
                "sport": sport_key,
                "stage": stage,
                "group_code": match_group,
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

    # Usa sempre il costo base del partecipante (server-side).
    price = int(participant.get("cost") or 0)
    if price <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid participant cost")

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

    # Usa sempre il costo base del partecipante (server-side).
    price = int(participant.get("cost") or 0)
    if price <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid participant cost")

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


@router.post("/admin/participants/{participant_id}")
def admin_update_participant(
    participant_id: int,
    payload: AdminUpdateParticipantRequest,
    client=Depends(get_supabase_client),
    x_admin_token: str = Header(None)
):
    """Aggiorna dati partecipante (admin only).
    
    Protezione: richiede X-Admin-Token header.
    
    Args:
        participant_id: ID partecipante da aggiornare.
        payload: Dati da aggiornare (parziali).
        client: Dipendenza client Supabase.
        x_admin_token: Token admin da header.
    
    Returns:
        Messaggio conferma.
    """
    if x_admin_token != "a3f9c4b8de":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token required")
    
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")
    
    # Verifica partecipante esiste
    participant_res = (
        client.table("participants")
        .select("id")
        .eq("id", participant_id)
        .limit(1)
        .execute()
    )
    if not participant_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    
    # Costruisci update payload (solo campi forniti)
    update_data = {}
    if payload.name is not None:
        update_data["name"] = payload.name
    if payload.role is not None:
        update_data["role"] = payload.role
    if payload.cost is not None:
        update_data["cost"] = max(0, payload.cost)
    if payload.score is not None:
        update_data["score"] = max(0, payload.score)
    if payload.matches_played is not None:
        update_data["matches_played"] = max(0, payload.matches_played)
    if payload.wins is not None:
        update_data["wins"] = max(0, payload.wins)
    if payload.losses is not None:
        update_data["losses"] = max(0, payload.losses)
    if payload.draws is not None:
        update_data["draws"] = max(0, payload.draws)
    # Allow clearing group_code by setting it to None or empty string
    if payload.group_code is not None:
        group_value = payload.group_code.strip().upper() if payload.group_code else None
        update_data["group_code"] = group_value
    elif hasattr(payload, 'group_code'):
        # If group_code field exists but is None, explicitly clear it
        update_data["group_code"] = None
    if payload.goals_for is not None:
        update_data["goals_for"] = max(0, payload.goals_for)
    if payload.goals_against is not None:
        update_data["goals_against"] = max(0, payload.goals_against)
    if payload.sets_won is not None:
        update_data["sets_won"] = max(0, payload.sets_won)
    if payload.sets_lost is not None:
        update_data["sets_lost"] = max(0, payload.sets_lost)
    if payload.composed_of is not None:
        update_data["composed_of"] = payload.composed_of
    
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    
    try:
        client.table("participants").update(update_data).eq("id", participant_id).execute()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Update failed")
    
    return {"status": "ok", "participant_id": participant_id, "updated": list(update_data.keys())}


@router.post("/admin/teams/{team_id}")
def admin_update_team(
    team_id: int,
    payload: AdminUpdateTeamRequest,
    client=Depends(get_supabase_client),
    x_admin_token: str = Header(None)
):
    """Aggiorna dati team (admin only).
    
    Protezione: richiede X-Admin-Token header.
    
    Args:
        team_id: ID team da aggiornare.
        payload: Dati da aggiornare (parziali).
        client: Dipendenza client Supabase.
        x_admin_token: Token admin da header.
    
    Returns:
        Messaggio conferma.
    """
    if x_admin_token != "a3f9c4b8de":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token required")
    
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")
    
    # Verifica team esiste
    team_res = (
        client.table("teams")
        .select("id")
        .eq("id", team_id)
        .limit(1)
        .execute()
    )
    if not team_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    # Costruisci update payload (solo campi forniti)
    update_data = {}
    if payload.score is not None:
        update_data["score"] = max(0, payload.score)
    if payload.balance_credits is not None:
        update_data["balance_credits"] = max(0, payload.balance_credits)
    
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    
    try:
        client.table("teams").update(update_data).eq("id", team_id).execute()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Update failed")
    
    return {"status": "ok", "team_id": team_id, "updated": list(update_data.keys())}


@router.get("/admin/matches")
def admin_list_matches(limit: int = 100, client=Depends(get_supabase_client), x_admin_token: str = Header(None)):
    """Lista partite registrate (admin)."""
    if x_admin_token != "a3f9c4b8de":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token required")
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    safe_limit = max(1, min(int(limit), 300))
    rows = (
        client.table("matches")
        .select("id, sport, stage, group_code, home_squad_id, away_squad_id, home_score, away_score, home_points_awarded, away_points_awarded, created_at")
        .order("id", desc=True)
        .limit(safe_limit)
        .execute()
    )
    data = rows.data or []

    ids = set()
    for r in data:
        if r.get("home_squad_id") is not None:
            ids.add(int(r["home_squad_id"]))
        if r.get("away_squad_id") is not None:
            ids.add(int(r["away_squad_id"]))

    name_map = _build_participant_name_map(client, sorted(ids)) if ids else {}

    return [
        {
            **row,
            "home_squad_name": name_map.get(int(row["home_squad_id"])) if row.get("home_squad_id") is not None else None,
            "away_squad_name": name_map.get(int(row["away_squad_id"])) if row.get("away_squad_id") is not None else None,
        }
        for row in data
    ]


@router.post("/admin/matches/{match_id}")
def admin_update_match(
    match_id: int,
    payload: dict = Body(default={}),
    client=Depends(get_supabase_client),
    x_admin_token: str = Header(None),
):
    """Aggiorna una partita registrata (admin) con rollback automatico di punti."""
    if x_admin_token != "a3f9c4b8de":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token required")
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    # Ottieni la partita attuale (con ALL i dati che servono)
    current = client.table("matches").select(
        "id, sport, stage, home_squad_id, away_squad_id, home_score, away_score, home_points_awarded, away_points_awarded"
    ).eq("id", match_id).limit(1).execute()
    if not current.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    row = current.data[0]
    
    # Estrai i dati ATTUALI della partita
    old_home_squad_id = int(row.get("home_squad_id"))
    old_away_squad_id = int(row.get("away_squad_id"))
    old_home_score = int(row.get("home_score") or 0)
    old_away_score = int(row.get("away_score") or 0)
    old_home_points = int(row.get("home_points_awarded") or 0)
    old_away_points = int(row.get("away_points_awarded") or 0)
    old_sport = (row.get("sport") or "calcio").strip().lower()
    
    # Determina i vecchi risultati (per rollback)
    if old_home_score > old_away_score:
        old_home_result = "win"
        old_away_result = "loss"
    elif old_away_score > old_home_score:
        old_home_result = "loss"
        old_away_result = "win"
    else:
        old_home_result = "draw"
        old_away_result = "draw"
    
    # ROLLBACK: sottrai i punti vecchi
    _apply_match_stats(client, old_home_squad_id, old_sport, -old_home_points, -old_home_score, -old_away_score, old_home_result, -1)
    _apply_match_stats(client, old_away_squad_id, old_sport, -old_away_points, -old_away_score, -old_home_score, old_away_result, -1)
    _distribute_squad_points(client, old_home_squad_id, -old_home_points)
    _distribute_squad_points(client, old_away_squad_id, -old_away_points)

    # Calcola i NUOVI punti e risultati
    sport_key = str(payload.get("sport") or row.get("sport") or "calcio").strip().lower()
    stage = str(payload.get("stage") or row.get("stage") or "group").strip().lower()
    home_score = int(payload.get("home_score") if payload.get("home_score") is not None else (row.get("home_score") or 0))
    away_score = int(payload.get("away_score") if payload.get("away_score") is not None else (row.get("away_score") or 0))

    home_points = 0
    away_points = 0
    if sport_key == "calcio":
        if home_score > away_score:
            home_points, away_points = 3, 0
        elif away_score > home_score:
            home_points, away_points = 0, 3
        else:
            home_points, away_points = 1, 1
    elif sport_key == "pallavolo":
        if home_score > away_score:
            home_points, away_points = 3, 1
        elif away_score > home_score:
            home_points, away_points = 1, 3
        else:
            home_points, away_points = 2, 2
    else:
        if home_score > away_score:
            home_points, away_points = 1, 0
        elif away_score > home_score:
            home_points, away_points = 0, 1
        else:
            home_points, away_points = 1, 1

    # Determina i nuovi risultati
    if home_score > away_score:
        home_result = "win"
        away_result = "loss"
    elif away_score > home_score:
        home_result = "loss"
        away_result = "win"
    else:
        home_result = "draw"
        away_result = "draw"

    # APPLICA i NUOVI punti
    _apply_match_stats(client, old_home_squad_id, sport_key, home_points, home_score, away_score, home_result, 1)
    _apply_match_stats(client, old_away_squad_id, sport_key, away_points, away_score, home_score, away_result, 1)
    _distribute_squad_points(client, old_home_squad_id, home_points)
    _distribute_squad_points(client, old_away_squad_id, away_points)

    update_data = {
        "sport": sport_key,
        "stage": stage,
        "home_score": home_score,
        "away_score": away_score,
        "home_points_awarded": home_points,
        "away_points_awarded": away_points,
    }

    client.table("matches").update(update_data).eq("id", match_id).execute()
    return {"status": "ok", "match_id": match_id, "updated": list(update_data.keys())}


@router.delete("/admin/matches/{match_id}")
def admin_delete_match(match_id: int, client=Depends(get_supabase_client), x_admin_token: str = Header(None)):
    """Elimina una partita registrata (admin) con rollback automatico di punti."""
    if x_admin_token != "a3f9c4b8de":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token required")
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    # Ottieni la partita PRIMA di eliminarla
    current = client.table("matches").select(
        "id, sport, home_squad_id, away_squad_id, home_score, away_score, home_points_awarded, away_points_awarded"
    ).eq("id", match_id).limit(1).execute()
    if not current.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    row = current.data[0]
    home_squad_id = int(row.get("home_squad_id"))
    away_squad_id = int(row.get("away_squad_id"))
    home_score = int(row.get("home_score") or 0)
    away_score = int(row.get("away_score") or 0)
    home_points = int(row.get("home_points_awarded") or 0)
    away_points = int(row.get("away_points_awarded") or 0)
    sport = (row.get("sport") or "calcio").strip().lower()

    # Determina i risultati attuali
    if home_score > away_score:
        home_result = "win"
        away_result = "loss"
    elif away_score > home_score:
        home_result = "loss"
        away_result = "win"
    else:
        home_result = "draw"
        away_result = "draw"

    # ROLLBACK: sottrai i punti
    _apply_match_stats(client, home_squad_id, sport, -home_points, -home_score, -away_score, home_result, -1)
    _apply_match_stats(client, away_squad_id, sport, -away_points, -away_score, -home_score, away_result, -1)
    _distribute_squad_points(client, home_squad_id, -home_points)
    _distribute_squad_points(client, away_squad_id, -away_points)

    # Elimina la partita
    client.table("matches").delete().eq("id", match_id).execute()
    return {"status": "ok", "match_id": match_id}
