-- Rimozione colonna legacy: la password e gestita da Supabase Auth (auth.users).

alter table if exists users
  drop column if exists password_hash;