Schema DB per FDC_fantatorneo

Scopo
- Definire le tabelle principali per utenti, team, partecipanti e transazioni.
- Fornire un punto di partenza per migrazioni su Supabase (Postgres).

Note di integrazione Supabase
- Supabase Auth gestisce gli account e fornisce `auth.users` con `id UUID`.
  Salvare quel valore in `users.auth_id` per collegare il profilo.
- Abilitare RLS (Row Level Security) e creare policy per:
  - Consentire al proprietario del profilo di leggere/aggiornare la propria riga in `users`.
  - Consentire ai team owner di modificare il proprio `team` e i partecipanti associati.

Suggerimenti
- Per operazioni atomiche (es. buy/sell) usare transazioni lato DB o funzioni SQL (RPC) per evitare condizioni di race.
- Considerare l'uso di Supabase Functions (Edge Functions) per logica serverless vicina al DB.

Esempio rapido di policy RLS (bozza):
-- allow user to select own profile
-- create policy "select_own_profile" on users using (auth.uid() = auth_id);

Prossimi passi suggeriti
- Creare migrazione 002 per dati iniziali (seed participants).
- Implementare endpoint FastAPI che verifica JWT di Supabase e chiama queste migrazioni/operazioni.
