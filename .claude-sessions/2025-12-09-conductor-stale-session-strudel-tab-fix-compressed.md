# Conductor Session Bug & Strudel Tab Fix - 2025-12-09

## Context
User started the neural music conductor TUI and noticed the LLM was making wrong decisions - claiming patterns had been "playing for 74+ hours" when music just started. Additionally, pattern changes weren't actually reaching Strudel (the browser-based music tool).

## Mistakes Are Learnings (Read This First)

**Key mistakes in this session**:
1. **Stale session state persisted across restarts**: Session file at `/tmp/conductor_session.json` stored `pattern_start_time` indefinitely → LLM received wildly incorrect duration data → Fixed by auto-resetting stale timestamps (>4 hours)
2. **Chrome automation targeted wrong tab**: `run-automation.mjs` defaulted to `pages[0]` → When multiple tabs open, Strudel wasn't first → Fixed by finding tab by URL pattern

**Time wasted**: ~0 (both bugs identified quickly from logs/error output)

## Decisions
- **4-hour staleness threshold**: Patterns realistically won't play >4 hours continuously; any older timestamp indicates a restart
- **Tab selection by URL**: More robust than index - survives tab reordering

## Implementation
- Changed `scripts/conductor_tui.py`: `load_session()` now resets `pattern_start_time` and `current_pattern` if timestamp >4 hours old (lines 309-321)
- Added `--fresh` flag to conductor for explicit session reset
- Changed `chrome-automation/scripts/strudel-play-file.mjs`: Now finds Strudel tab via `pages.find(p => p.url().includes('strudel.cc'))` instead of using `pages[0]`

## Lessons
- ✅ Reading logs first (conductor_reasoning.log) immediately revealed the "74 hours" bug
- ✅ Testing automation directly (`node run-automation.mjs`) showed the `.cm-content` selector failure
- 💡 Persisted state files need staleness detection for long-running/restartable apps
- 💡 Multi-tab Chrome automation should never assume tab order

## Mistakes & Efficiency Improvements

### Tool Call Failures & Inefficiencies
| Tool | Issue | Better Approach |
|------|-------|-----------------|
| N/A | All tool calls succeeded | - |

**Wasted tool calls:** 0
**Sequential→Parallel opportunities:** Used parallel calls for Chrome instance check + port check

### AI Agent Mistakes
None - diagnosis was straightforward from provided logs

### User Mistakes (Where AI Should Push Back)
None - user correctly identified something was wrong and provided relevant log output

## Knowledge Gaps
- Missing: Documentation on session file location and purpose
- Unclear: Which Chrome profile/port the conductor expects

## .claude Improvements

### CLAUDE.md
- [ ] Add note: "Conductor uses `/tmp/conductor_session.json` for state persistence - delete to start fresh"

## Project Enhancements (Code-Level Work)

### Tech Debt Discovered
| Issue | Location | Impact | Suggested Fix |
|-------|----------|--------|---------------|
| Hard-coded tab index | `chrome-automation/scripts/run-automation.mjs:56,77` | medium | Pass target URL pattern as option |
| No session file documentation | `scripts/conductor_tui.py` | low | Add comment explaining persistence |

### Feature Ideas
- [ ] **Session file location in TUI**: Display path in footer or startup message - Priority: P2
- [ ] **Chrome tab health check**: Verify Strudel tab exists before starting conductor - Priority: P1

## Related Sessions
- 2025-12-06-tui-chrome-automation-fix: Previous Strudel/Chrome automation work
- 2025-12-06-llm-conductor: Initial LLM conductor implementation

## Artifacts
- Files modified:
  - `scripts/conductor_tui.py` (staleness detection + --fresh flag)
  - `chrome-automation/scripts/strudel-play-file.mjs` (tab selection fix)
- Commands run:
  - `rm /tmp/conductor_session.json` (cleared stale session)
  - PowerShell Strudel automation test
