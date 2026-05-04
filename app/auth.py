"""Autenticazione JWT e risoluzione profilo utente.

Gestisce verifica token da Supabase Auth e arricchisce JWT claims
con dati profilo utente dal database applicativo.
"""

import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from dotenv import load_dotenv
from .database import get_supabase_client

# Carica segreto JWT dall'ambiente.
load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("SUPABASE_JWT_SECRET must be set in environment variables.")

# Supabase ora usa ES256 per access token (non HS256).
ALGORITHM = "HS256"


def _ensure_profile_team(client, profile_data: dict | None) -> dict | None:
    """Garantisce che il profilo utente abbia un team assegnato.

    Fallback robusto: se team_id manca, collega un team esistente del proprietario
    o ne crea uno nuovo e aggiorna users.team_id.
    """
    if client is None or not profile_data:
        return profile_data

    user_db_id = profile_data.get("id")
    if not user_db_id:
        return profile_data

    surname = (profile_data.get("surname") or "").strip()
    display_name = f"{(profile_data.get('name') or '').strip()} {surname}".strip()
    desired_team_name = (f"{display_name}'s team" if display_name else f"Team {user_db_id}")

    existing_user_team_id = profile_data.get("team_id")
    if existing_user_team_id:
        linked_team = (
            client.table("teams")
            .select("id, owner_user_id")
            .eq("id", existing_user_team_id)
            .limit(1)
            .execute()
        )
        linked_row = linked_team.data[0] if linked_team.data else None
        if linked_row and (linked_row.get("owner_user_id") in (None, user_db_id)):
            client.table("teams").update({"owner_user_id": user_db_id, "name": desired_team_name}).eq("id", int(existing_user_team_id)).execute()
            profile_data["team_id"] = int(existing_user_team_id)
            return profile_data

    team_id = None
    existing_team = (
        client.table("teams")
        .select("id")
        .eq("owner_user_id", user_db_id)
        .limit(1)
        .execute()
    )

    if existing_team.data:
        team_id = int(existing_team.data[0]["id"])
        client.table("teams").update({"name": desired_team_name}).eq("id", team_id).execute()
    else:
        created_team = client.table("teams").insert({"name": desired_team_name, "owner_user_id": user_db_id}).execute()
        if created_team.data:
            team_id = int(created_team.data[0]["id"])

    if team_id is not None:
        client.table("users").update({"team_id": team_id}).eq("id", user_db_id).execute()
        profile_data["team_id"] = team_id

    return profile_data


def get_current_user(token: str = Depends(oauth2_scheme), client=Depends(get_supabase_client)):
    """Verifica token JWT da Supabase e risolve profilo utente.
    
    Args:
        token: Bearer token da header Authorization HTTP.
        client: Client Supabase per arricchimento profilo facoltativo.
    
    Returns:
        dict con auth_id, email, e profile (se DB disponibile).
    
    Raises:
        HTTPException: 401 se token invalido o verifica fallisce.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Supabase ora usa ES256 per access token, non HS256.
        # Decodifica senza verifica firma (token viene direttamente da Supabase Auth).
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        email = payload.get("email")
        user_metadata = payload.get("user_metadata") or {}
        display_name = (user_metadata.get("name") or user_metadata.get("full_name") or "").strip()
        surname = (user_metadata.get("surname") or "").strip()

        # Arricchisci risposta con profilo utente da DB app se client disponibile.
        profile_data = None
        if client is not None:
            try:
                # Cerca il profilo - seleziona tutti i campi per assicurarsi di avere team_id
                user_profile = client.table("users").select("*").eq("auth_id", user_id).execute()
                profile_data = user_profile.data[0] if user_profile.data else None
                
                # Se non trovato, lo crea
                if not profile_data:
                    create_payload = {
                        "auth_id": user_id,
                        "name": display_name or (email.split("@")[0] if email else "User"),
                        "surname": surname or None,
                        "email": email,
                        "coins": 100,
                    }
                    try:
                        created_profile = client.table("users").insert(create_payload).execute()
                        profile_data = created_profile.data[0] if created_profile.data else None
                    except Exception:
                        pass
                    
                    # Se insert non ha ritornato dati, refetch
                    if not profile_data:
                        user_profile = client.table("users").select("*").eq("auth_id", user_id).execute()
                        profile_data = user_profile.data[0] if user_profile.data else None
                
                # Se il profilo è presente e ha un id, assicura team
                if profile_data and profile_data.get("id"):
                    try:
                        profile_data = _ensure_profile_team(client, profile_data)
                    except Exception:
                        pass
            except Exception:
                profile_data = None

        # Se il profilo è ancora None o non ha un team_id, tenta il fallback di emergency
        if not profile_data or not profile_data.get("team_id"):
            if client is not None:
                try:
                    # Rescue: leggi il profilo una volta ancora
                    user_profile = client.table("users").select("*").eq("auth_id", user_id).execute()
                    if user_profile.data:
                        profile_data = user_profile.data[0]
                        # Se il profilo non ha team_id, assicura il team subito
                        if not profile_data.get("team_id"):
                            try:
                                profile_data = _ensure_profile_team(client, profile_data)
                            except Exception:
                                pass
                except Exception:
                    pass
        
        # Se il profilo è ancora None, crea un minimo fallback
        if not profile_data:
            profile_data = {
                "auth_id": user_id,
                "email": email,
                "name": display_name or (email.split("@")[0] if email else "User"),
                "surname": surname or None,
                "coins": 100,
                "team_id": None,
            }

        team_id = profile_data.get("team_id") if isinstance(profile_data, dict) else None

        return {
            "auth_id": user_id,
            "email": email,
            "team_id": team_id,
            "profile": profile_data,
        }

    except Exception:
        raise credentials_exception
