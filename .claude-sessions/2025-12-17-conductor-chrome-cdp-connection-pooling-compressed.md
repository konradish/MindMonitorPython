# Conductor Chrome CDP & Connection Pooling Fix - 2025-12-17

## Context
User reported the conductor TUI had inconsistent Chrome CDP debug connections at launch and slow EEG state reads. Investigation revealed: (1) no connection check/retry logic for Chrome CDP, and (2) new database connections created for every state query.

## Mistakes Are Learnings (Read This First)

**Key mistakes in this session**:
1. **PowerShell curl hangs indefinitely**: Tried `powershell.exe -Command "curl -s 'http://localhost:9223/json/version'"` to check Chrome CDP → Command hung → Should have used socket check instead
2. **Background bash from previous session still running**: Shell 324ff2 was running a stale `find | xargs grep` from earlier → Kept showing reminders → Should have killed immediately

**Time wasted**: ~2 min on hanging PowerShell curl command; minor distraction from stale background task

## Decisions
- **Socket-based CDP check**: Use Python socket connection (instant) instead of HTTP fetch (can hang)
- **Connection pool size 1-5**: Minimum 1 keeps connection warm; max 5 handles concurrent worker threads
- **Retry logic 3x with 2s delay**: Chrome needs time to initialize CDP endpoint after startup

## Implementation
- Changed `scripts/conductor_tui.py`:
  - Added `psycopg2.pool.ThreadedConnectionPool` (lines 57-79)
  - Added `check_chrome_cdp()` - socket-based instant check (lines 87-100)
  - Added `wait_for_chrome_cdp()` - retry logic with configurable attempts (lines 103-111)
  - Optimized `get_current_eeg_state()` query: replaced `MODE() WITHIN GROUP` aggregate with `LIMIT 20 + Counter` (lines 131-190)
  - Added `check_chrome_connection()` background worker on mount (lines 583-596)
  - `get_state_history()` now uses connection pooling (lines 193-214)

## Lessons
- ✅ Database query itself was fast (0.3ms) - confirmed with EXPLAIN ANALYZE
- ✅ Connection pooling dropped subsequent queries to <1ms (from 5ms first call)
- ✅ Socket check for port availability is instant and reliable
- ❌ PowerShell/curl from WSL to Windows can hang - avoid for health checks
- 💡 Python startup overhead (~1.4s) is the main latency, not DB queries
- 💡 `MODE() WITHIN GROUP` is overkill for small result sets - Python Counter faster

## Mistakes & Efficiency Improvements

### Tool Call Failures & Inefficiencies
| Tool | Issue | Better Approach |
|------|-------|-----------------|
| Bash | PowerShell curl hung | Use Python socket check directly |
| BashOutput | Kept getting reminders about stale shell 324ff2 | Kill it immediately at session start |

**Wasted tool calls:** 2 (PowerShell curl + BashOutput on stale task)
**Sequential→Parallel opportunities:** Query explain and index check ran in parallel (good)

### AI Agent Mistakes
1. **Used PowerShell curl instead of socket**: WSL→Windows network calls can hang; should have used Python's `socket.connect_ex()` from the start

### User Mistakes (Where AI Should Push Back)
None - user correctly identified the symptoms

## Knowledge Gaps
- Missing: Chrome CDP startup timing documentation (how long before CDP is ready)
- Unclear: Whether TimescaleDB hypertable affects connection pooling

## .claude Improvements

### CLAUDE.md
- [ ] Add: "For port availability checks from WSL, use Python socket, not PowerShell curl"

## Project Enhancements (Code-Level Work)

### Tech Debt Discovered
| Issue | Location | Impact | Suggested Fix |
|-------|----------|--------|---------------|
| No Chrome startup automation | conductor_tui.py | medium | Auto-launch Chrome with --remote-debugging-port |
| Global Counter import | conductor_tui.py:174 | low | Move import to top of file |

### Feature Ideas
- [ ] **Auto-launch Chrome with CDP**: If CDP check fails, offer to launch Chrome - Priority: P2
- [ ] **CDP port configuration**: Allow CDP_PORT env var (already added but not documented) - Priority: P2

### Refactoring Opportunities
- [ ] **Extract DB utilities**: Connection pool, release, and query helpers could be a shared module
  - Motivation: Used by both conductor and MCP server
  - Approach: Create `db/pool.py` with connection context manager

## Related Sessions
- 2025-12-09-conductor-stale-session-strudel-tab-fix: Previous conductor bug (stale session, tab selection)
- 2025-12-06-neural-music-conductor: Original conductor implementation

## Artifacts
- Files modified:
  - `scripts/conductor_tui.py` (connection pooling, Chrome CDP check, optimized query)
- Key measurements:
  - EEG state query: 4.8ms → 0.5ms (after pool warm)
  - Chrome CDP check: instant (socket-based)
  - Pool creation: 5ms
