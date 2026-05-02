-- Persistenza owner multipli per partecipante.
-- owner_user_ids contiene tutti gli user id dei team attualmente proprietari.

alter table if exists participants
  add column if not exists owner_user_ids int[] not null default '{}'::int[];

update participants p
set owner_user_ids = coalesce(
  (
    select array_agg(distinct t.owner_user_id)
    from team_participants_history h
    join teams t on t.id = h.team_id
    where h.participant_id = p.id
      and h.released_at is null
      and t.owner_user_id is not null
  ),
  '{}'::int[]
);

create or replace function sync_participant_owner_user_ids() returns trigger as $$
declare
  participant_key int;
begin
  if tg_op = 'DELETE' then
    participant_key := old.participant_id;
  else
    participant_key := new.participant_id;
  end if;

  if participant_key is null then
    return null;
  end if;

  update participants p
  set owner_user_ids = coalesce(
    (
      select array_agg(distinct t.owner_user_id)
      from team_participants_history h
      join teams t on t.id = h.team_id
      where h.participant_id = participant_key
        and h.released_at is null
        and t.owner_user_id is not null
    ),
    '{}'::int[]
  )
  where p.id = participant_key;

  return null;
end;
$$ language plpgsql;

create or replace function sync_team_participant_owner_user_ids() returns trigger as $$
begin
  update participants p
  set owner_user_ids = coalesce(
    (
      select array_agg(distinct t.owner_user_id)
      from team_participants_history h
      join teams t on t.id = h.team_id
      where h.participant_id = p.id
        and h.released_at is null
        and t.owner_user_id is not null
    ),
    '{}'::int[]
  )
  where p.team_id = new.id;

  return null;
end;
$$ language plpgsql;

drop trigger if exists trg_sync_participant_owner_user_ids on team_participants_history;

create trigger trg_sync_participant_owner_user_ids
after insert or update or delete on team_participants_history
for each row execute function sync_participant_owner_user_ids();

drop trigger if exists trg_sync_team_participant_owner_user_ids on teams;

create trigger trg_sync_team_participant_owner_user_ids
after update of owner_user_id on teams
for each row execute function sync_team_participant_owner_user_ids();