# MCP Rolling Average for EEG State - 2025-12-05

## Context
User wanted to check EEG transmission status, then requested smoothing noisy instant readings in the MCP server's `get_current_eeg_state` by using a rolling average instead of single-sample queries.

## Mistakes Are Learnings (Read This First)

**Key mistakes in this session**:
1. **Stale Windows processes**: Old Python processes from 9:53 AM were still running → Had to kill all Python processes before UDP forwarder would work → Check for stale processes before starting new ones
2. **Background command chaining issue**: Used `&` with `&&` incorrectly → Command parsing failed → Use `run_in_background` parameter instead of shell `&`

**Time wasted**: ~2 minutes debugging why data wasn't flowing when old processes were blocking ports

## Decisions
- **10-second rolling window**: User initially requested 20s, then reduced to 10s for better responsiveness while still smoothing noise. ~112 samples averaged.
- **MODE() for state**: Use SQL `MODE()` aggregate to find dominant state in window rather than recalculating from averaged band powers.
- **Parameterized window**: Added `window_seconds` parameter (range 5-60) so callers can adjust if needed.

## Implementation
- Changed `scripts/eeg_mcp_server.py`: `get_current_eeg_state()` now queries last N seconds with AVG() for band powers
- Added fields to response: `window_seconds`, `samples_averaged`, `state_source: "dominant_in_window"`
- SQL uses `MODE() WITHIN GROUP (ORDER BY features->>'state')` for finding most common state

## Lessons
- ✅ PostgreSQL `MODE()` aggregate perfect for finding dominant categorical value
- ✅ Averaging ~100+ samples dramatically smooths EEG noise
- 💡 When starting multi-component pipelines, verify each component is fresh (not stale process)

## Mistakes & Efficiency Improvements

### Tool Call Failures & Inefficiencies

| Tool | Issue | Better Approach |
|------|-------|-----------------|
| Bash | Background `&` with `&&` chaining failed | Use `run_in_background: true` parameter |
| Bash | Had to kill OSC receiver twice | First kill command had wrong exit handling |

**Wasted tool calls:** 2 (redundant process checks)
**Sequential→Parallel opportunities:** Initial status checks were correctly parallelized

### AI Agent Mistakes
1. **Assumed new UDP forwarder started**: Old processes from morning were still running on Windows, blocking the port. Should have killed existing Python processes first.

## Knowledge Gaps
- None significant - pipeline startup is documented in CLAUDE.md

## .claude Improvements

### CLAUDE.md
- [ ] Add note: "Kill stale Windows Python processes before starting UDP forwarder: `powershell.exe -Command \"Get-Process python | Stop-Process -Force\"`"

## Project Enhancements (Code-Level Work)

### Feature Ideas
- [ ] **Configurable default window via env var**: Allow `EEG_MCP_WINDOW_SECONDS=15` - Priority: P2
  - Files affected: `scripts/eeg_mcp_server.py`
  - Complexity: small

## Artifacts
- Files modified: `scripts/eeg_mcp_server.py`
- Background process still running: OSC receiver (shell 39b040)
