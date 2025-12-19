# Conductor Logging & Stale Session Fix - 2025-12-19

## Context
User noticed `conductor_reasoning.log` was no longer updating. Last entry was Dec 17.

## Mistakes Are Learnings (Read This First)

**Key mistakes in this session**:
1. **Silent failure paths not logged**: Two code paths in `call_llm_conductor` returned `None` without logging - decision file missing, and future timeout exceptions
2. **Stale paused session again**: `/tmp/conductor_session.json` had `paused: true` from Dec 17 - same class of bug as 2025-12-09 session

**Time wasted**: ~5 minutes diagnosing before checking session file

## Decisions
- Add logging for all failure paths in LLM conductor flow
- Session file should be checked earlier when debugging conductor issues

## Implementation
- `scripts/conductor_tui.py` line 430: Added `log_reasoning("Decision file not found after Claude call", "N/A", "error")`
- `scripts/conductor_tui.py` line 856: Added `log_reasoning(f"LLM future failed: {e}", "N/A", "error")`

## Lessons
- 💡 When conductor isn't logging, check session file for `paused: true` first
- 💡 All failure paths should log to the reasoning file, not just TUI
- 💡 Log file path changed to `logs/conductor_reasoning.log` (not project root)

## Mistakes & Efficiency Improvements

### Tool Call Failures & Inefficiencies
| Tool | Issue | Better Approach |
|------|-------|-----------------|
| N/A | All tool calls succeeded | - |

### AI Agent Mistakes
- Could have checked session file earlier instead of diving into code

### User Mistakes (Where AI Should Push Back)
None - user correctly identified the symptom

## Knowledge Gaps
- Missing: Quick debugging checklist for "conductor not working"

## .claude Improvements

### CLAUDE.md
- [ ] Add debugging tip: "If conductor isn't responding, check `/tmp/conductor_session.json` for `paused: true`"

## Related Sessions
- 2025-12-09-conductor-stale-session-strudel-tab-fix: Same stale session issue

## Artifacts
- Files modified:
  - `scripts/conductor_tui.py` (added logging for silent failures)
- Commands run:
  - `rm /tmp/conductor_session.json` (cleared stale paused session)
