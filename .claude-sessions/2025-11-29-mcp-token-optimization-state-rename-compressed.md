# MCP Token Optimization + State Rename - 2025-11-29

## Context
EEG MCP server was returning verbose JSON timeseries data to Claude Desktop, consuming excessive tokens. Also discovered that `NO_SIGNAL` state name was misleading - it implied hardware issues when it actually meant "no detection rule matched" (valid signal, ambiguous pattern).

## Mistakes Are Learnings (Read This First)

**Key mistakes in this session**:
1. **Misinterpreted NO_SIGNAL initially**: User and AI both assumed NO_SIGNAL=electrode issues. Had to trace through code to discover it's the fallback when no detection rule matches. → Prevention: Check code before assuming meaning from names.

**Time wasted**: ~5 minutes investigating NO_SIGNAL meaning - Could have been prevented by reading engine.py first.

## Decisions
- **Summary-by-default for timeseries**: Raw JSON for 1200 readings = ~5000 tokens. Summary stats = ~500 tokens (90% reduction). Added `detail` parameter for raw access when needed.
- **Renamed NO_SIGNAL to MIXED**: Clearer meaning - valid signal, no dominant pattern. Not a hardware issue.
- **Created ERROR state**: For actual exceptions/missing channel data. Separates "ambiguous but valid" from "broken".
- **CSV format option**: 40-50% fewer tokens than JSON for bulk data access.

## Implementation

### scripts/eeg_mcp_server.py
- Refactored `get_band_timeseries(minutes, detail='summary')`:
  - `detail='summary'` (default): band_stats (mean/std/min/max), state_distribution, longest_state, transitions count
  - `detail='csv'`: Compact CSV string format
  - `detail='json'`: Original full JSON array (backward compatible)
- Added helper functions: `_compute_band_stats()`, `_find_longest_state()`
- Updated interpretations dict: added MIXED and ERROR states

### consciousness_monitor/detection/engine.py:188
- Changed fallback from `"NO_SIGNAL"` to `"MIXED"` with emoji `🔀`
- Renamed `_get_no_signal_result()` to `_get_error_result()` returning `"ERROR"` state

### consciousness_monitor/main.py
- Renamed all `_get_no_signal_result()` calls to `_get_error_result()`
- Updated state check: `result.state not in ("ERROR", "BASELINE")` instead of checking NO_SIGNAL

## Lessons
- ✅ Summary stats are more useful than raw timeseries for most Claude queries
- ✅ CSV format significantly reduces tokens while preserving data access
- ❌ State names should describe the condition, not imply a cause (NO_SIGNAL implied hardware)
- 💡 Running processes need restart to pick up code changes - they cache old code in memory
- 💡 50% "NO_SIGNAL" in session actually means user spent half the time in transitional states - interesting data, not a problem

## Mistakes & Efficiency Improvements

### Tool Call Failures & Inefficiencies
| Tool | Issue | Better Approach |
|------|-------|-----------------|
| Grep | Multiple searches for NO_SIGNAL across directories | Could have searched project root once with better pattern |

**Wasted tool calls**: ~3 redundant searches while investigating NO_SIGNAL
**Sequential→Parallel opportunities**: Could have searched config/ and detection/ in parallel

### AI Agent Mistakes
1. **Initially agreed NO_SIGNAL = electrode issues**: Should have verified by reading engine.py fallback logic first. State names don't always match their implementation.

### Times AI Correctly Pushed Back
- **Traced code to find real meaning**: Discovered NO_SIGNAL was fallback for "no rule match", not hardware issue. Corrected the misconception.

## Knowledge Gaps
- Missing: Documentation explaining what each state actually means (beyond therapeutic descriptions)

## .claude Improvements

### REFERENCE.md
- [ ] Add to `skills/eeg/REFERENCE.md`: State meanings table
  - MIXED = valid signal, no detection rule matched (ambiguous pattern)
  - ERROR = processing exception or missing channel data
  - List all therapeutic states with their detection criteria

## Related Sessions
- 2025-11-28-osc-receiver-db-emission-fix-compressed: Previous MCP server work

## Artifacts
- Files modified: `scripts/eeg_mcp_server.py`, `consciousness_monitor/detection/engine.py`, `consciousness_monitor/main.py`
- Tests run: Import verification, interpret_state function test
