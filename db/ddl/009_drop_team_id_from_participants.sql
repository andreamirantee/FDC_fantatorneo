-- Migration 009: Drop unused team_id foreign key from participants

-- The team_id column on participants is unused; all team ownership is now tracked via
-- team_participants_history (active ownership with released_at IS NULL).

DROP INDEX IF EXISTS idx_participants_team;

ALTER TABLE participants
  DROP COLUMN IF EXISTS team_id;
