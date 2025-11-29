-- Migration 003: Add ingestion checkpoint table and view aliases
-- Date: 2025-08-09

-- Create checkpoint table for resumable ingestion
CREATE TABLE IF NOT EXISTS ingestion_checkpoint (
  file_path TEXT PRIMARY KEY,
  session_id UUID NOT NULL,
  byte_offset BIGINT NOT NULL DEFAULT 0,
  line_number BIGINT NOT NULL DEFAULT 0,
  last_ts TIMESTAMPTZ,
  file_sha256 TEXT,
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create view aliases for backward compatibility with existing tools
-- This allows tools expecting 'window' and 'window_1s' to work with 'eeg_window' tables
CREATE VIEW IF NOT EXISTS window AS SELECT * FROM eeg_window;
CREATE VIEW IF NOT EXISTS window_1s AS SELECT * FROM eeg_window_1s;

-- Add index on checkpoint updated_at for maintenance queries
CREATE INDEX IF NOT EXISTS idx_checkpoint_updated_at ON ingestion_checkpoint(updated_at);

-- Add index on checkpoint session_id for session-based queries
CREATE INDEX IF NOT EXISTS idx_checkpoint_session_id ON ingestion_checkpoint(session_id);