"""Modelli Pydantic per validazione richieste/risposte e rappresentazione dati.

Modelli organizzati per feature:
- Step 1 (Auth): RegisterRequest, LoginRequest, ResendConfirmationRequest
- Step 2 (Market): BuyParticipantRequest, SellParticipantRequest, MarketOperationResult
- Step 3 (Data): TeamRosterItem, MarketTransactionItem
- CRUD: Team, Participant, RankingItem, UserProfile
"""

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Modelli Team
# ============================================================================

class TeamBase(BaseModel):
    """Campi condivisi team tra creazione e lettura."""
    name: str | None = None
    owner_user_id: int | None = None


class TeamCreate(TeamBase):
    """Payload per creazione nuovo team."""
    name: str


class TeamRead(TeamBase):
    """Dati team come letti da database. Include campi computati."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    total_cost: int = 0
    score: int = 0


# ============================================================================
# Modelli Participant
# ============================================================================

class ParticipantBase(BaseModel):
    """Campi condivisi partecipante tra creazione e lettura."""
    name: str | None = None
    role: str | None = None
    cost: int | None = None
    team_id: int | None = None
    available: bool | None = None


class ParticipantCreate(ParticipantBase):
    """Payload per creazione nuovo partecipante."""
    name: str


class ParticipantRead(ParticipantBase):
    """Dati partecipante come letti da database."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str | None = None
    cost: int = 0
    score: int = 0
    available: bool = True
    owner_user_ids: list[int] = Field(default_factory=list)


# ============================================================================
# Modelli Step 1 Auth
# ============================================================================

class RegisterRequest(BaseModel):
    """Richiesta signup: email e password per nuovo utente."""
    email: str
    password: str


class LoginRequest(BaseModel):
    """Richiesta login: email e password per autenticazione."""
    email: str
    password: str


class ResendConfirmationRequest(BaseModel):
    """Richiesta reinvio email di conferma."""
    email: str


# ============================================================================
# Modelli Step 2 Market
# ============================================================================

class BuyParticipantRequest(BaseModel):
    """Richiesta acquisto copia partecipante per un team.
    
    Modello proprietà: partecipante può essere posseduto da più team,
    ma stesso team non può possedere copie duplicate.
    """
    buyer_team_id: int
    participant_id: int
    price: int | None = None  # Facoltativo: usa participant.cost se non fornito.


class SellParticipantRequest(BaseModel):
    """Richiesta vendita/rilascio partecipante da proprietà team."""
    seller_team_id: int
    participant_id: int
    price: int | None = None  # Facoltativo: usa participant.cost se non fornito.


class MarketOperationResult(BaseModel):
    """Risposta dopo operazione mercato buy/sell."""
    status: str  # "ok" su successo.
    operation: str  # "buy" o "sell".
    participant_id: int
    buyer_team_id: int | None = None
    seller_team_id: int | None = None
    price: int


# ============================================================================
# Modelli Step 3 Data
# ============================================================================

class RankingItem(BaseModel):
    """Riga classifica team: score e costo totale."""
    id: int
    name: str | None = None
    sport: str | None = None
    score: int = 0
    total_cost: int = 0


class TeamRosterItem(BaseModel):
    """Riga partecipante in roster attivo del team.
    
    Basata su team_participants_history con released_at NULL (proprietà attiva).
    Include timestamp acquired_at per cronologia acquisizione.
    """
    participant_id: int
    participant_name: str | None = None
    role: str | None = None
    cost: int = 0
    participant_score: int = 0
    acquired_at: str  # Timestamp formato ISO.


class MarketTransactionItem(BaseModel):
    """Riga transazione mercato arricchita con nomi team/partecipanti.
    
    Usata per timeline transazioni:
    - buyer_team_id/buyer_team_name NULL = rilascio al mercato
    - seller_team_id/seller_team_name NULL = acquisto da mercato
    - entrambi set = giocatore scambiato tra team
    """
    id: int
    buyer_team_id: int | None = None
    buyer_team_name: str | None = None
    seller_team_id: int | None = None
    seller_team_name: str | None = None
    participant_id: int | None = None
    participant_name: str | None = None
    price: int
    created_at: str  # Timestamp formato ISO.


# ============================================================================
# Admin Requests
# ============================================================================

class UpdateParticipantPoints(BaseModel):
    """Richiesta per aggiornare punti partecipante (squadra)."""
    points: int


class UpdateTeamScore(BaseModel):
    """Richiesta per aggiornare score team."""
    score: int


class MatchResult(BaseModel):
    """Richiesta per registrare risultato partita."""
    home_squad_id: int  # ID squadra home
    away_squad_id: int  # ID squadra away
    home_score: int     # Punti/goal squadra home
    away_score: int     # Punti/goal squadra away
