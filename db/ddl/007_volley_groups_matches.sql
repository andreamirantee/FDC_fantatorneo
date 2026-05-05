-- Migration 007: Add group support and matches table for tournament phases

ALTER TABLE participants
  ADD COLUMN IF NOT EXISTS group_code VARCHAR(1);

CREATE TABLE IF NOT EXISTS matches (
  id SERIAL PRIMARY KEY,
  sport VARCHAR(50),
  stage VARCHAR(20) NOT NULL DEFAULT 'group',
  group_code VARCHAR(1),
  home_squad_id INT REFERENCES participants(id) ON DELETE SET NULL,
  away_squad_id INT REFERENCES participants(id) ON DELETE SET NULL,
  home_score INT NOT NULL DEFAULT 0,
  away_score INT NOT NULL DEFAULT 0,
  home_points_awarded INT NOT NULL DEFAULT 0,
  away_points_awarded INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_matches_sport_stage ON matches(sport, stage);
CREATE INDEX IF NOT EXISTS idx_matches_group ON matches(group_code);
CREATE INDEX IF NOT EXISTS idx_matches_home ON matches(home_squad_id);
CREATE INDEX IF NOT EXISTS idx_matches_away ON matches(away_squad_id);
