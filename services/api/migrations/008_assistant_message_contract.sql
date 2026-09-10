-- Complete the assistant message persistence contract introduced by migration 006.
-- Migration 007 uses CREATE TABLE IF NOT EXISTS, so it cannot add columns to
-- assistant_messages when that table already exists from migration 006.
-- This migration is safe on both fresh and upgraded databases.

ALTER TABLE assistant_messages
    ADD COLUMN IF NOT EXISTS intent TEXT,
    ADD COLUMN IF NOT EXISTS action TEXT,
    ADD COLUMN IF NOT EXISTS status TEXT,
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_assistant_messages_owner_created
    ON assistant_messages(owner_id, created_at DESC);
