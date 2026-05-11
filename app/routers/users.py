"""Endpoint profilo utente.

Fornisce accesso autenticato a informazioni profilo utente corrente.
"""

from fastapi import APIRouter, Depends

from ..auth import get_current_user
from ..database import get_supabase_client

# Router utente: endpoint informazioni utente autenticato.
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
def read_me(current_user=Depends(get_current_user), client=Depends(get_supabase_client)):
    """Ottieni profilo utente autenticato corrente.
    
    Returns:
        Dati utente corrente da token JWT e profilo arricchito da database.
    """
    result = current_user
    if client is not None and result.get("team_id") is None:
        try:
            auth_id = result.get("auth_id")
            profile = result.get("profile") if isinstance(result.get("profile"), dict) else None
            if not auth_id and profile:
                auth_id = profile.get("auth_id")

            if auth_id:
                user_res = (
                    client.table("users")
                    .select("id, team_id")
                    .eq("auth_id", auth_id)
                    .limit(1)
                    .execute()
                )
                if user_res.data:
                    user_row = user_res.data[0]
                    team_id = user_row.get("team_id")
                    if not team_id and user_row.get("id"):
                        team_res = (
                            client.table("teams")
                            .select("id")
                            .eq("owner_user_id", user_row.get("id"))
                            .limit(1)
                            .execute()
                        )
                        if team_res.data:
                            team_id = team_res.data[0].get("id")

                    if team_id:
                        result["team_id"] = team_id
                        if profile is not None:
                            profile["team_id"] = team_id

                        try:
                            team_row = (
                                client.table("teams")
                                .select("id, balance_credits")
                                .eq("id", team_id)
                                .limit(1)
                                .execute()
                            )
                            if team_row.data:
                                current_balance = team_row.data[0].get("balance_credits")
                                if current_balance is None:
                                    client.table("teams").update({"balance_credits": 100}).eq("id", team_id).execute()
                        except Exception:
                            pass
        except Exception:
            pass

    # Se abbiamo un client e un team_id noto, arricchisci con il balance del team
    try:
        team_id = result.get("team_id") if isinstance(result, dict) else None
        if client is not None and team_id:
            try:
                team_row = (
                    client.table("teams")
                    .select("id, balance_credits")
                    .eq("id", int(team_id))
                    .limit(1)
                    .execute()
                )
                if team_row and getattr(team_row, 'data', None):
                    tb = team_row.data[0].get("balance_credits")
                    # normalizza a numero
                    try:
                        tb_val = int(tb) if tb is not None else 0
                    except Exception:
                        tb_val = 0
                    result["team_balance"] = tb_val
                    # compatibilità frontend: alias dome_balance
                    result["dome_balance"] = tb_val
            except Exception:
                # non bloccare la risposta se il DB fallisce qui
                pass

            # Bonus team: restituisce elenco bonus e totale punti bonus.
            try:
                bonus_res = (
                    client.table("bonus")
                    .select("id, name, points, reason, sport, participant_id, awarded_at, is_active")
                    .eq("team_id", int(team_id))
                    .order("awarded_at", desc=True)
                    .execute()
                )
                bonus_rows = bonus_res.data if bonus_res and getattr(bonus_res, "data", None) else []

                # Recupera nomi delle squadre (participants) per i bonus
                participant_ids = [row.get("participant_id") for row in bonus_rows if row.get("participant_id")]
                participants_map = {}
                if participant_ids:
                    try:
                        participants_res = (
                            client.table("participants")
                            .select("id, name")
                            .in_("id", list(set(participant_ids)))
                            .execute()
                        )
                        if participants_res and getattr(participants_res, "data", None):
                            participants_map = {p.get("id"): p.get("name") for p in participants_res.data}
                    except Exception:
                        pass

                normalized_bonus = []
                bonus_total = 0
                for row in bonus_rows:
                    if not isinstance(row, dict):
                        continue
                    try:
                        pts = int(row.get("points") or 0)
                    except Exception:
                        pts = 0
                    bonus_total += pts
                    participant_id = row.get("participant_id")
                    participant_name = participants_map.get(participant_id) if participant_id else None
                    normalized_bonus.append(
                        {
                            "id": row.get("id"),
                            "name": row.get("name") or "Bonus",
                            "points": pts,
                            "reason": row.get("reason") or "Motivo non specificato",
                            "sport": row.get("sport"),
                            "participant_id": participant_id,
                            "participant_name": participant_name,
                            "awarded_at": row.get("awarded_at"),
                            "is_active": bool(row.get("is_active", True)),
                        }
                    )

                result["bonus_items"] = normalized_bonus
                result["bonus_total"] = bonus_total
            except Exception:
                # se la tabella bonus non esiste ancora o fallisce, non bloccare /users/me
                result["bonus_items"] = []
                result["bonus_total"] = 0
    except Exception:
        pass

    return result
