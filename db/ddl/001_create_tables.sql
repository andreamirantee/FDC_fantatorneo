create extension if not exists pgcrypto;

-- Create teams first.
-- NOTE: owner_user_id non ha FK in questa fase per evitare dipendenza circolare.
create table if not exists teams (
    id serial primary key,
    owner_user_id int, -- add constraint later
    name varchar(255),
    total_cost int not null default 0,
    score int not null default 0,
    created_at timestamptz not null default now()
);

-- Create users second.
-- NOTE: team_id non ha FK in questa fase per evitare dipendenza circolare.
create table if not exists users (
    id serial primary key,
    auth_id uuid unique,
    name varchar(150) not null,
    surname varchar(150),
    email varchar(255) unique,
    team_id int, -- add constraint later
    coins int not null default 100,
    created_at timestamptz not null default now()
);

-- Aggiungiamo ora le FK mancanti: entrambe le tabelle esistono gia.
alter table teams
  add constraint teams_owner_user_id_fkey
  foreign key (owner_user_id) references users(id)
  on delete cascade;

alter table users
  add constraint users_team_id_fkey
  foreign key (team_id) references teams(id)
  on delete set null;

-- PARTICIPANTS (current owner team)
create table if not exists participants (
    id serial primary key,
    external_id varchar(128),
    name varchar(255) not null,
    role varchar(100),
    cost int not null default 0,
    score int not null default 0,
    team_id int references teams(id) on delete set null,
    owner_user_ids int[] not null default '{}'::int[],
    available boolean not null default true,
    created_at timestamptz not null default now()
);

create table if not exists team_participants_history (
    id serial primary key,
    team_id int references teams(id) on delete cascade,
    participant_id int references participants(id) on delete cascade,
    acquired_at timestamptz not null default now(),
    released_at timestamptz
);

create table if not exists transactions (
    id serial primary key,
    buyer_team_id int references teams(id) on delete set null,
    seller_team_id int references teams(id) on delete set null,
    participant_id int references participants(id) on delete set null,
    price int not null,
    created_at timestamptz not null default now()
);

-- Indici base per query frequenti su join e lookup.
create index if not exists idx_participants_team on participants(team_id);
create index if not exists idx_users_authid on users(auth_id);
create index if not exists idx_transactions_participant on transactions(participant_id);

-- Vista comoda per leggere roster per team con left join.
create or replace view team_roster as
select t.id as team_id, t.name as team_name,
       p.id as participant_id, p.name as participant_name, p.cost
from teams t
left join participants p on p.team_id = t.id;

create or replace function recompute_team_totals(tid int) returns void as $$
begin
    -- Ricalcola solo total_cost, lasciando score gestito da altra logica applicativa.
    update teams
    set total_cost = coalesce((select sum(cost) from participants where team_id = tid),0)
    where id = tid;
end;
$$ language plpgsql;