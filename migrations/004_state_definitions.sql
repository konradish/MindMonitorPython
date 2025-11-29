-- Migration 004: Add state_definition table for Claude-managed custom states
-- Date: 2025-11-29
-- Purpose: Allow Claude (via MCP) to create/modify EEG state definitions
--          that are checked BEFORE hardcoded detection rules

-- Custom state definitions managed via MCP
CREATE TABLE IF NOT EXISTS state_definition (
    name TEXT PRIMARY KEY,                      -- e.g., "DEEP_WORK", "K_RELAXED"
    priority INT NOT NULL DEFAULT 50,           -- Higher = checked first (DB states default 50, hardcoded 1-20)
    conditions JSONB NOT NULL,                  -- {"alpha_min": 25, "alpha_max": 40, "beta_min": 15}
    interpretation TEXT,                        -- Human-readable explanation
    recommendations TEXT[],                     -- Communication recommendations
    emoji TEXT DEFAULT '🧠',                    -- Display emoji
    enabled BOOLEAN NOT NULL DEFAULT true,      -- Can disable without deleting
    author TEXT NOT NULL DEFAULT 'claude_mcp',  -- Who created this
    notes TEXT,                                 -- Additional context
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Index for enabled states lookup (most common query)
CREATE INDEX IF NOT EXISTS idx_state_definition_enabled
    ON state_definition(enabled, priority DESC)
    WHERE enabled = true;

-- Comment for documentation
COMMENT ON TABLE state_definition IS 'Claude-managed custom EEG state definitions. Checked before hardcoded rules.';
COMMENT ON COLUMN state_definition.conditions IS 'JSONB with band thresholds: alpha_min, alpha_max, beta_min, beta_max, delta_min, delta_max, theta_min, theta_max, gamma_min, gamma_max (all optional, percentages 0-100)';
COMMENT ON COLUMN state_definition.priority IS 'Higher priority checked first. Default 50 for custom states (hardcoded rules are 1-20)';
