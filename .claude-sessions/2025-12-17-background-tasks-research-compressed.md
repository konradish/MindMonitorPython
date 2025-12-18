# Background Tasks for EEG-Music Integration - 2025-12-17

## Context
Brief research session exploring Claude Code's background tasks feature to understand if it could help with real-time EEG-to-music integration (Mind Monitor → Strudel MCP).

## Decisions
- **Background tasks are polling-based, not event-driven**: They're good for running long processes, but the main loop would need to poll for EEG state changes rather than receive push notifications.
- **Existing conductor approach is better for reactive music**: The LLM conductor (`scripts/llm_conductor.py`) is more appropriate for continuous reactive music generation than background tasks.

## Implementation
- No code changes. Research session only.

## Lessons
- ✅ Claude Code background tasks useful for: dev servers, test suites, OSC receiver, admin panel
- ❌ Not ideal for event-driven reactive systems (push vs poll)
- 💡 Use `Ctrl+B` to move running command to background on-the-fly
- 💡 Background task architecture: process runs → output buffered → retrieve via BashOutput tool

## Background Tasks Feature Summary

### Key Capabilities
- Run commands asynchronously with `run_in_background: true` or asking "in the background"
- `Ctrl+B` moves currently-running command to background (tmux: `Ctrl+B` twice)
- `BashOutput` tool retrieves buffered output from background processes
- Unique task IDs for tracking; auto-cleanup on exit

### Best Use Cases for This Project
| Use Case | Command |
|----------|---------|
| OSC receiver | `uv run python scripts/osc_receiver.py` |
| Admin panel | `uv run streamlit run admin/app.py` |
| Test suite | `uv run pytest` |
| Consciousness monitor | `uv run python -m consciousness_monitor` |

### Architecture Assessment
```
Option A (Background Tasks - Polling):
  Background: OSC receiver → DB
  Background: State watcher
  Claude: Poll state → Generate Strudel → Wait → Repeat

Option B (Conductor Script - Event-Driven):
  Conductor: OSC → State detection → LLM → Strudel
  (More appropriate for reactive music)
```

## Knowledge Gaps
- None significant - feature was well-documented

## .claude Improvements
- None needed - research session only

## Related Sessions
- 2025-12-06-neural-music-conductor-compressed.md: Original conductor implementation
- 2025-12-06-llm-conductor.md: LLM-driven conductor details

## Artifacts
- Files modified: None (research only)
- Commands run: Task agent search for claude-code-guide
