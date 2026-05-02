# FlutterFlow API Contract - FDC Fantatorneo

Documento operativo per collegare velocemente FlutterFlow al backend FastAPI.

## Base

- Base URL locale: http://127.0.0.1:8000
- Prefisso API: /api/v1
- Content-Type: application/json

## FlutterFlow App State consigliato

Usa questi nomi variabili per evitare confusione tra pagine:

- ffAccessToken (String)
- ffTokenType (String, default: bearer)
- ffAuthUserId (String)
- ffCurrentUserName (String)
- ffCurrentUserEmail (String)
- ffCurrentUserCoins (int)
- ffCurrentTeamId (int)

## Header template per call protette

Per tutte le API protette imposta:

- Authorization: Bearer [ffAccessToken]
- Content-Type: application/json

## Autenticazione

### 1) Register

- Method: POST
- URL: /api/v1/auth/register
- Body:

```json
{
  "name": "Mario",
  "surname": "Rossi",
  "email": "mario.rossi@example.com",
  "password": "Password123!"
}
```

- Success response (200):

```json
{
  "status": "ok",
  "auth_user_id": "uuid",
  "profile": {
    "auth_id": "uuid",
    "name": "Mario",
    "surname": "Rossi",
    "email": "mario.rossi@example.com",
    "coins": 100
  }
}
```

### 2) Login

- Method: POST
- URL: /api/v1/auth/login
- Body:

```json
{
  "email": "mario.rossi@example.com",
  "password": "Password123!"
}
```

- Success response (200):

```json
{
  "status": "ok",
  "access_token": "jwt-token",
  "token_type": "bearer",
  "user_id": "uuid"
}
```

- JSON mapping suggerito in FlutterFlow:
  - $.access_token -> ffAccessToken
  - $.token_type -> ffTokenType
  - $.user_id -> ffAuthUserId

### 3) Resend Confirmation

- Method: POST
- URL: /api/v1/auth/resend-confirmation
- Body:

```json
{
  "email": "mario.rossi@example.com"
}
```

### 4) Current User

- Method: GET
- URL: /api/v1/auth/me
- Header:
  - Authorization: Bearer <access_token>

## Users

### Profile corrente

- Method: GET
- URL: /api/v1/users/me
- Header:
  - Authorization: Bearer <access_token>

- JSON mapping suggerito in FlutterFlow:
  - $.current_user.name -> ffCurrentUserName
  - $.current_user.email -> ffCurrentUserEmail
  - $.current_user.coins -> ffCurrentUserCoins
  - $.current_user.team_id -> ffCurrentTeamId

## Teams

### Lista team

- Method: GET
- URL: /api/v1/teams

- List path in FlutterFlow:
  - $
- Campi principali item:
  - $.id
  - $.name
  - $.score
  - $.total_cost

### Crea team

- Method: POST
- URL: /api/v1/teams
- Body:

```json
{
  "name": "Team Alpha",
  "owner_user_id": 1
}
```

## Participants

### Lista participants

- Method: GET
- URL: /api/v1/participants

- List path in FlutterFlow:
  - $
- Campi principali item:
  - $.id
  - $.name
  - $.role
  - $.cost
  - $.available

### Crea participant

- Method: POST
- URL: /api/v1/participants
- Body:

```json
{
  "name": "Giocatore Uno",
  "role": "attaccante",
  "cost": 25,
  "team_id": null,
  "available": true
}
```

## Market

### Ranking

- Method: GET
- URL: /api/v1/market/ranking

- List path in FlutterFlow:
  - $
- Campi principali item:
  - $.id
  - $.name
  - $.score
  - $.total_cost

### Buy

- Method: POST
- URL: /api/v1/market/buy
- Body:

```json
{
  "buyer_team_id": 1,
  "participant_id": 10,
  "price": 30
}
```

### Sell

- Method: POST
- URL: /api/v1/market/sell
- Body:

```json
{
  "seller_team_id": 1,
  "participant_id": 10,
  "price": 30
}
```

### Team Roster (Step 3)

- Method: GET
- URL: /api/v1/market/teams/{team_id}/roster
- Example URL: /api/v1/market/teams/1/roster

- Success response (200):

```json
[
  {
    "participant_id": 10,
    "participant_name": "Giocatore Uno",
    "role": "attaccante",
    "cost": 30,
    "acquired_at": "2026-04-28T10:00:00+00:00"
  }
]
```

- List path in FlutterFlow:
  - $
- Campi principali item:
  - $.participant_id
  - $.participant_name
  - $.role
  - $.cost
  - $.acquired_at

### Transactions Timeline (Step 3)

- Method: GET
- URL: /api/v1/market/transactions
- Optional query param:
  - limit (default 50, max 200)

- Example URL: /api/v1/market/transactions?limit=20

- Success response (200):

```json
[
  {
    "id": 101,
    "buyer_team_id": 1,
    "buyer_team_name": "Team Alpha",
    "seller_team_id": null,
    "seller_team_name": null,
    "participant_id": 10,
    "participant_name": "Giocatore Uno",
    "price": 30,
    "created_at": "2026-04-28T10:05:00+00:00"
  }
]
```

- List path in FlutterFlow:
  - $
- Campi principali item:
  - $.id
  - $.buyer_team_id
  - $.buyer_team_name
  - $.seller_team_id
  - $.seller_team_name
  - $.participant_id
  - $.participant_name
  - $.price
  - $.created_at

## Errori comuni da gestire in FlutterFlow

- 400: richiesta non valida
- 401: credenziali errate o token non valido
- 404: risorsa non trovata
- 409: conflitto logico (es. participant gia posseduto dal team)
- 429: rate limit (soprattutto auth)
- 503: servizio DB/Supabase non disponibile

## Setup pratico in FlutterFlow

1. Crea una API Call per ogni endpoint usato.
2. Salva i campi login con i mapping suggeriti in App State.
3. Per tutte le rotte protette aggiungi header Authorization: Bearer <token>.
4. Gestisci errore 401 forzando logout e ritorno alla pagina login.
5. Per liste usa sempre fallback UI su array vuoto.

## Flusso minimo consigliato in FlutterFlow

1. Pagina Login: chiama /auth/login e salva ffAccessToken, ffTokenType, ffAuthUserId.
2. On App Start (o Home init): chiama /users/me e salva dati utente in App State.
3. Home classifica: chiama /market/ranking e mostra lista.
4. Pagina Team: chiama /market/teams/{team_id}/roster usando ffCurrentTeamId.
5. Pagina Storico mercato: chiama /market/transactions?limit=50 e mostra timeline.
