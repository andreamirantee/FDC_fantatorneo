-- Migration 006: Add wins and losses tracking to participants table

ALTER TABLE participants
  ADD COLUMN wins INT NOT NULL DEFAULT 0,
  ADD COLUMN losses INT NOT NULL DEFAULT 0,
  ADD COLUMN draws INT NOT NULL DEFAULT 0;
