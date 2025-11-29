# MCP Custom State Definitions - 2025-11-29

## Context
User asked "what can the MCP server do now?" which revealed a gap: Claude could read EEG states but couldn't create/modify state definitions. Implemented "walk" phase of crawl/walk/run: DB-stored custom states that Claude can manage via MCP, enabling personalized EEG pattern recognition without code changes.

## Mistakes Are Learnings (Read This First)

**Key mistakes in this session**:
1. **Write-time-only classification**: Initially put state classification only in osc_receiver (write-time). User correctly pushed back: "A restart is a real PITA for realtime work." → Added read-time classification in MCP server for dynamic evaluation.
2. **Architecture assumption**: Assumed MCP server just reads pre-computed states. Actually has band powers available and can classify dynamically. Should have recognized this pattern earlier.

**Time wasted**: ~5 minutes debugging why custom state wasn't detected - turned out osc_receiver needed restart for write-time classification. User insight led to better solution.

## Decisions
- **Store states in DB with JSONB conditions**: Flexible schema, supports arbitrary band thresholds. Priority field (custom=50, hardcoded=1-20) controls evaluation order.
- **30-second cache in DetectionEngine**: Balances freshness vs DB load for write-time path.
- **Read-time classification in MCP**: `check_custom_states()` evaluates against current band powers at query time. No restart needed for state definition changes.
- **Simple min/max conditions first**: Deferred relational conditions (alpha_gt_beta, ratios) to "run" phase. 80/20 rule.

## Implementation

### New Files
- `migrations/004_state_definitions.sql`: Table with name (PK), priority, conditions (JSONB), interpretation, recommendations, emoji, enabled, author, notes

### Modified: `scripts/eeg_mcp_server.py`
- Added `check_custom_states(percentages)`: Read-time classification against DB states
- Added 5 MCP tools:
  - `create_state_definition(name, conditions, interpretation, recommendations, emoji, priority, notes)`
  - `list_state_definitions(include_disabled)`
  - `update_state_definition(name, ...)` - partial updates
  - `delete_state_definition(name)`
  - `create_state_from_baseline(baseline_name, state_name, tolerance)` - convenience wrapper
- Modified `get_current_eeg_state()`: Check custom states FIRST, return `state_source: "custom"` or `"hardcoded"`

### Modified: `consciousness_monitor/detection/engine.py`
- Added `database_url` param to `__init__`
- Added `_get_custom_states()`: Cached DB lookup (30s TTL)
- Added `_evaluate_custom_state()`: Test conditions against percentages
- Added `_evaluate_database_rules()`: Iterate custom states by priority
- Modified `_evaluate_detection_rules()`: Check DB rules BEFORE hardcoded rules

## Lessons
- ✅ Parallel agents for exploration worked well (found SQL patterns + engine.py structure simultaneously)
- ✅ User insight about read-time vs write-time classification improved architecture
- ❌ Should have asked "where should classification happen?" before implementing
- 💡 For dynamic config, prefer read-time evaluation over cached/precomputed when latency is acceptable

## Mistakes & Efficiency Improvements

### Tool Call Analysis
| Tool | Issue | Better Approach |
|------|-------|-----------------|
| Task (Explore) x2 | Both ran in parallel - good | N/A - correct usage |

**Wasted tool calls**: 0 - efficient session
**Sequential→Parallel opportunities**: Used parallel agents effectively

### AI Correctly Questioned
- User asked about relational conditions (alpha_gt_beta). AI correctly suggested deferring to "run" phase with 80/20 rationale.

## Knowledge Gaps
- Missing: Documentation on MCP server architecture (read vs write paths)
- Unclear: When to use caching vs dynamic evaluation for realtime systems

## .claude Improvements

### CLAUDE.md Additions
- [ ] Add: "For EEG MCP development: read-time classification in MCP server, write-time in osc_receiver"

### Future Enhancements (documented, not actionable yet)
- Relational conditions: `alpha_gt_beta`, `alpha_beta_ratio_min` - add when concrete use case emerges
- Cross-session analysis: Compare "last Tuesday's work" to today
- Pattern learning: Auto-detect personal state signatures

## Artifacts
- Files modified: `migrations/004_state_definitions.sql` (new), `scripts/eeg_mcp_server.py`, `consciousness_monitor/detection/engine.py`
- Tests run: `create_state_definition` → `list_state_definitions` → `delete_state_definition` cycle; DetectionEngine with custom state matching
- State verified: `SATURDAY_TINKERING` detected dynamically via MCP without osc_receiver restart
