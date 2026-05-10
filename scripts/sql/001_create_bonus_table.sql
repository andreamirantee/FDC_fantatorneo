-- Bonus table for team scoring adjustments.
-- Required fields: name, points, reason.
-- Extra fields: team relation, sport, participant relation, active flag, metadata and timestamps.

create table if not exists public.bonus (
    id bigserial primary key,
    team_id bigint not null references public.teams(id) on delete cascade,
    participant_id bigint null references public.participants(id) on delete set null,
    created_by_user_id bigint null references public.users(id) on delete set null,
    name text not null,
    points integer not null default 0,
    reason text not null,
    sport text null,
    is_active boolean not null default true,
    awarded_at timestamptz not null default now(),
    expires_at timestamptz null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint bonus_name_not_empty check (char_length(trim(name)) > 0),
    constraint bonus_reason_not_empty check (char_length(trim(reason)) > 0)
);

create index if not exists idx_bonus_team_id on public.bonus(team_id);
create index if not exists idx_bonus_awarded_at on public.bonus(awarded_at desc);
create index if not exists idx_bonus_participant_id on public.bonus(participant_id);
create index if not exists idx_bonus_is_active on public.bonus(is_active);

create or replace function public.set_bonus_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists trg_bonus_set_updated_at on public.bonus;
create trigger trg_bonus_set_updated_at
before update on public.bonus
for each row
execute function public.set_bonus_updated_at();
