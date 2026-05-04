-- auto_playlist table for RhythmClaw midi_server.py
create table if not exists auto_playlist (
  id uuid primary key default gen_random_uuid(),
  track_id uuid references tracks(id) on delete cascade,
  position integer not null default 0,
  added_at timestamptz default now(),
  played_at timestamptz,
  skipped boolean default false
);
alter table auto_playlist enable row level security;
create policy "service_role_all" on auto_playlist using (true);
