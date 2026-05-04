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

    return result