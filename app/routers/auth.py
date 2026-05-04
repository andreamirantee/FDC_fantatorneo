"""Endpoint autenticazione utente con Supabase Auth.

Gestisce:
- Registrazione utente (signup pubblico con conferma email)
- Login utente (password grant per token JWT access)
- Reinvio email di conferma (per retry verifica email)
- Lettura profilo utente corrente (autenticato)

Step 1 di FDC Fantatorneo: sistema autenticazione.
"""

from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, status
import httpx

from ..auth import get_current_user
from ..database import (
    get_supabase_client,
    get_supabase_status,
    get_supabase_auth_credentials,
    get_supabase_email_redirect_to,
)

# Router auth: signup, login, profilo, e gestione credenziali.
router = APIRouter(prefix="/auth", tags=["Auth"])


def _ensure_user_team_assignment(client, user_row: dict, preferred_name: str | None = None) -> int | None:
    """Garantisce che l'utente DB abbia un team assegnato.

    Se team_id è assente:
    - cerca un team esistente con owner_user_id = user.id
    - altrimenti crea un nuovo team
    - aggiorna users.team_id
    """
    if client is None or not user_row:
        return None

    user_db_id = user_row.get("id")
    if not user_db_id:
        return None

    team_id = user_row.get("team_id")
    desired_team_name = (preferred_name or user_row.get("name") or f"Team {user_db_id}").strip()

    if team_id:
        linked_team = (
            client.table("teams")
            .select("id, owner_user_id, name, balance_credits")
            .eq("id", team_id)
            .limit(1)
            .execute()
        )
        linked_row = linked_team.data[0] if linked_team.data else None
        if linked_row and (linked_row.get("owner_user_id") in (None, user_db_id)):
            update_payload = {"owner_user_id": user_db_id}
            if desired_team_name:
                update_payload["name"] = desired_team_name
            current_balance = linked_row.get("balance_credits")
            if current_balance is None or int(current_balance or 0) <= 0:
                update_payload["balance_credits"] = 100
            client.table("teams").update(update_payload).eq("id", int(team_id)).execute()
            return int(team_id)

    existing_team = (
        client.table("teams")
        .select("id, name, balance_credits")
        .eq("owner_user_id", user_db_id)
        .limit(1)
        .execute()
    )

    if existing_team.data:
        team_id = int(existing_team.data[0]["id"])
        current_balance = existing_team.data[0].get("balance_credits")
        if current_balance is None or int(current_balance or 0) <= 0:
            client.table("teams").update({"balance_credits": 100}).eq("id", team_id).execute()
    else:
        team_name = desired_team_name
        created_team = client.table("teams").insert(
            {"name": team_name, "owner_user_id": user_db_id, "balance_credits": 100}
        ).execute()
        if not created_team.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to create default team")
        team_id = int(created_team.data[0]["id"])

    client.table("users").update({"team_id": team_id}).eq("id", user_db_id).execute()
    user_row["team_id"] = team_id
    return team_id


class RegisterRequest(BaseModel):
    """Richiesta signup: info profilo utente e credenziali.
    
    Attributes:
        name: Nome utente.
        surname: Cognome utente (facoltativo).
        email: Email utente (deve essere valida).
        password: Password utente (inviata a Supabase Auth).
    """
    name: str
    surname: str | None = None
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    """Richiesta login: credenziali per Supabase Auth password grant.
    
    Attributes:
        email: Email registrata utente.
        password: Password utente.
    """
    email: EmailStr
    password: str


class ResendConfirmationRequest(BaseModel):
    """Richiesta reinvio email di conferma.
    
    Attributes:
        email: Indirizzo email a cui inviare link di conferma.
    """
    email: EmailStr


@router.post("/register")
def register_user(payload: RegisterRequest, client=Depends(get_supabase_client)):
    """Registra nuovo utente con conferma email.
    
    Step 1a: Endpoint signup pubblico che:
    1. Crea utente in Supabase Auth con password
    2. Invia email di conferma con link verifica
    3. Crea profilo utente in DB app (con fallback su errore DB)
    
    Args:
        payload: RegisterRequest con name, email, password.
        client: Dipendenza client Supabase.
    
    Returns:
        dict con status, auth_user_id, e dati profilo.
    
    Raises:
        HTTPException: 400 per email invalida, 429 per rate limit,
                      503 se Supabase indisponibile.
    """
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    try:
        auth_url, auth_key = get_supabase_auth_credentials()
        if not auth_url or not auth_key:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase auth not configured")

        # Chiama endpoint Supabase Auth signup: utente deve confermare email prima di login.
        signup_url = f"{auth_url}/signup"
        headers = {"apikey": auth_key, "Authorization": f"Bearer {auth_key}", "Content-Type": "application/json"}
        redirect_to = get_supabase_email_redirect_to()
        request_params = {"redirect_to": redirect_to} if redirect_to else None
        with httpx.Client(timeout=20.0) as http_client:
            auth_response = http_client.post(
                signup_url,
                json={
                    "email": payload.email,
                    "password": payload.password,
                    "data": {"name": payload.name, "surname": payload.surname},
                },
                headers=headers,
                params=request_params,
            )
        if auth_response.status_code >= 400:
            error_payload = auth_response.json()
            if error_payload.get("error_code") == "email_address_invalid":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usa una email vera e valida: Supabase rifiuta email di prova non valide.")
            if "rate limit" in str(error_payload.get("msg", "")).lower():
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error_payload.get("msg") or "Troppe richieste di registrazione. Riprova tra un po'.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_payload.get("msg") or auth_response.text)

        auth_payload = auth_response.json()
        user = auth_payload.get("user") or auth_payload
        user_id = user.get("id") if isinstance(user, dict) else None
        if not user_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Auth signup returned no user id")

        # Crea profilo utente in DB app.
        profile_payload = {
            "auth_id": user_id,
            "name": payload.name,
            "surname": payload.surname,
            "email": payload.email,
            "coins": 100,
        }
        
        # Prova inserimento profilo. Se errore DB, ritorna auth ok con profilo fallback.
        try:
            profile_insert = client.table("users").insert(profile_payload).execute()
            profile_data = profile_insert.data[0] if profile_insert.data else None
            if not profile_data:
                profile_lookup = (
                    client.table("users")
                    .select("id, auth_id, name, surname, email, coins, team_id")
                    .eq("auth_id", user_id)
                    .limit(1)
                    .execute()
                )
                profile_data = profile_lookup.data[0] if profile_lookup.data else profile_payload
        except Exception as db_error:
            # Errore DB (RLS, vincoli, etc.) - auth riuscito, insert profilo fallito.
            profile_data = profile_payload
            auth_message = f"Account auth creato ok. Profilo: {str(db_error)}"
        else:
            auth_message = None

        result = {"status": "ok", "auth_user_id": user_id, "profile": profile_data, "supabase": get_supabase_status()}

        # Regola richiesta prodotto: ogni nuovo utente deve avere un team assegnato.
        try:
            user_lookup = (
                client.table("users")
                .select("id, auth_id, name, surname, email, coins, team_id")
                .eq("auth_id", user_id)
                .limit(1)
                .execute()
            )
            user_row = user_lookup.data[0] if user_lookup.data else None
            if user_row:
                display_name = f"{payload.name} {payload.surname}".strip() if payload.surname else payload.name
                assigned_team_id = _ensure_user_team_assignment(client, user_row, f"{display_name}'s team")
                if assigned_team_id is not None:
                    profile_data["team_id"] = assigned_team_id
            elif auth_message is None:
                auth_message = "Account auth creato ok, ma profilo DB non trovato per assegnazione team automatica."
        except Exception as team_error:
            if auth_message:
                auth_message = f"{auth_message} | Team auto-assign: {str(team_error)}"
            else:
                auth_message = f"Team auto-assign: {str(team_error)}"

        if auth_message:
            result["note"] = auth_message
        return result
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/login")
def login_user(payload: LoginRequest, client=Depends(get_supabase_client)):
    """Autentica utente e ritorna token JWT access.
    
    Step 1b: Endpoint login che scambia email/password per token JWT.
    
    Args:
        payload: LoginRequest con email e password.
        client: Dipendenza client Supabase (facoltativa, per info status).
    
    Returns:
        dict con access_token, token_type, user_id.
    
    Raises:
        HTTPException: 401 per credenziali invalide,
                      503 se Supabase indisponibile.
    """
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase client not available")

    try:
        auth_url, auth_key = get_supabase_auth_credentials()
        if not auth_url or not auth_key:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase auth not configured")

        token_url = f"{auth_url}/token?grant_type=password"
        headers = {"apikey": auth_key, "Authorization": f"Bearer {auth_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=20.0) as http_client:
            auth_response = http_client.post(token_url, json={"email": payload.email, "password": payload.password}, headers=headers)
        if auth_response.status_code >= 400:
            error_payload = auth_response.json()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error_payload.get("msg") or error_payload.get("error_description") or auth_response.text)

        auth_payload = auth_response.json()
        # Supabase ritorna access_token al primo livello, non dentro session.
        access_token = auth_payload.get("access_token")
        user = auth_payload.get("user") or {}
        user_id = user.get("id")
        if not access_token or not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        # Self-healing per utenti legacy: se non hanno team_id, crea/collega team automaticamente.
        try:
            user_lookup = (
                client.table("users")
                .select("id, name, surname, email, team_id")
                .eq("auth_id", user_id)
                .limit(1)
                .execute()
            )
            user_row = user_lookup.data[0] if user_lookup.data else None

            # Se il profilo applicativo è stato eliminato ma l'utente Auth esiste,
            # ricrealo automaticamente al login.
            if not user_row:
                user_metadata = user.get("user_metadata") if isinstance(user, dict) else {}
                fallback_name = (user_metadata or {}).get("name") or payload.email.split("@")[0]
                fallback_surname = (user_metadata or {}).get("surname")

                recreate_payload = {
                    "auth_id": user_id,
                    "name": fallback_name,
                    "surname": fallback_surname,
                    "email": payload.email,
                    "coins": 100,
                }
                recreated = client.table("users").insert(recreate_payload).execute()
                user_row = recreated.data[0] if recreated.data else None

            if user_row:
                full_name = ((user_row.get("name") or "") + " " + (user_row.get("surname") or "")).strip()
                _ensure_user_team_assignment(client, user_row, f"{(full_name or payload.email)}'s team")
                profile_refresh = (
                    client.table("users")
                    .select("id, auth_id, name, surname, email, coins, team_id")
                    .eq("auth_id", user_id)
                    .limit(1)
                    .execute()
                )
                if profile_refresh.data:
                    user_row = profile_refresh.data[0]
        except Exception:
            # Non bloccare login: il frontend mostrerà eventuale messaggio e si può correggere dal profilo/admin.
            pass

        return {
            "status": "ok",
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_id,
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error


@router.post("/resend-confirmation")
def resend_confirmation(payload: ResendConfirmationRequest):
    """Reinvia link conferma email all'utente.
    
    Step 1a (retry): Invia nuova email di conferma se utente non ha ancora verificato.
    
    Args:
        payload: ResendConfirmationRequest con email.
    
    Returns:
        dict con status e messaggio.
    
    Raises:
        HTTPException: 400 per email invalida, 429 per rate limit,
                      503 se Supabase indisponibile.
    """
    try:
        auth_url, auth_key = get_supabase_auth_credentials()
        if not auth_url or not auth_key:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase auth not configured")

        resend_url = f"{auth_url}/resend"
        headers = {"apikey": auth_key, "Authorization": f"Bearer {auth_key}", "Content-Type": "application/json"}
        redirect_to = get_supabase_email_redirect_to()
        request_params = {"redirect_to": redirect_to} if redirect_to else None
        with httpx.Client(timeout=20.0) as http_client:
            auth_response = http_client.post(
                resend_url,
                json={
                    "type": "signup",
                    "email": payload.email,
                },
                headers=headers,
                params=request_params,
            )

        if auth_response.status_code >= 400:
            error_payload = auth_response.json()
            if "rate limit" in str(error_payload.get("msg", "")).lower():
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error_payload.get("msg") or "Troppe richieste di reinvio. Riprova tra un po'.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_payload.get("msg") or error_payload.get("error_description") or auth_response.text)

        return {
            "status": "ok",
            "message": "Email di conferma reinviata. Controlla la posta.",
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/me")
def read_current_user(current_user=Depends(get_current_user)):
    """Ottieni profilo utente autenticato corrente.
    
    Step 1c: Ritorna info utente da token JWT + arricchimento profilo DB.
    Richiede token bearer valido da login.
    
    Args:
        current_user: Dict utente corrente da verifica JWT (dipendenza).
    
    Returns:
        dict con status e dati current_user.
    """
    return {"status": "ok", "current_user": current_user}



def is_admin(current_user: dict = Depends(get_current_user), client=Depends(get_supabase_client)) -> bool:
    """Verifica se l'utente corrente è admin."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non autenticato")
    
    user_id = current_user.get("auth_id")
    if not user_id:
        return False
    
    # Controlla se esiste in tabella admin_users e revoked_at è NULL
    res = client.table("admin_users").select("id").eq("auth_id", user_id).is_("revoked_at", "null").limit(1).execute()
    return bool(res.data)