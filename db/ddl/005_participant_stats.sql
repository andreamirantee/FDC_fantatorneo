alter table participants
  add column if not exists matches_played int not null default 0,
  add column if not exists wins int not null default 0,
  add column if not exists losses int not null default 0,
  add column if not exists draws int not null default 0,
  add column if not exists goals_for int not null default 0,
  add column if not exists goals_against int not null default 0,
  add column if not exists sets_won int not null default 0,
  add column if not exists sets_lost int not null default 0;

-- Riallinea score e statistiche a zero per nuove installazioni (opzionale).
update participants
set score = coalesce(score, 0),
    matches_played = coalesce(matches_played, 0),
    wins = coalesce(wins, 0),
    losses = coalesce(losses, 0),
    draws = coalesce(draws, 0),
    goals_for = coalesce(goals_for, 0),
    goals_against = coalesce(goals_against, 0),
    sets_won = coalesce(sets_won, 0),
    sets_lost = coalesce(sets_lost, 0)
where matches_played is null
  or wins is null
  or losses is null
  or draws is null
  or goals_for is null
  or goals_against is null
  or sets_won is null
  or sets_lost is null;
