-- Migration 008: Add composed_of field to participants for squad composition details

ALTER TABLE participants
  ADD COLUMN IF NOT EXISTS composed_of TEXT;
