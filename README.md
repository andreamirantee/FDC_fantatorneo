# FDC Fantatorneo Backend

Backend FastAPI con integrazione Supabase.

## Python consolidato

- Versione target: Python 3.11 o 3.12
- Vincolo progetto: `>=3.11,<3.13` (vedi `pyproject.toml`)

Nota: con Python 3.14 alcune librerie possono avere compatibilita incompleta.

## Setup rapido (Windows PowerShell)

1. Installa Python 3.12 (se non presente).
2. Esegui lo script di bootstrap passando il path del python.exe 3.12.

Esempio:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\rebuild_venv.ps1 -PythonExe "C:\\Path\\To\\Python312\\python.exe"
```

## Avvio server

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api.py
```

## FlutterFlow

Contratto API pronto all'uso per integrazione frontend:

- docs/flutterflow_api_contract.md

## Deploy su Render

Il progetto include un blueprint Render in [render.yaml](render.yaml).

Variabili da impostare su Render:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- `CORS_ORIGINS=https://fdcfanta.me,https://www.fdcfanta.me`
- `SUPABASE_EMAIL_REDIRECT_TO=https://fdcfanta.me/auth`

Comando di avvio usato da Render:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```