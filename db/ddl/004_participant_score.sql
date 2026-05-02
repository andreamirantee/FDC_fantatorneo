-- Aggiunge la colonna score ai partecipanti esistenti.

alter table if exists participants
  add column if not exists score int not null default 0;

update participants
set score = coalesce(score, 0);