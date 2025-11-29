# OSC Receiver Database Emission Fix + EEG MCP Server - 2025-11-28

## Context
Database monitor was only writing 1 window to TimescaleDB instead of continuous ~1/sec emission. OSC receiver was correctly recording EEG to CSV, but analysis showed all bands at 20% (NO_SIGNAL) and no "DB: Window" debug messages appeared. After fixing emission, built MCP server to expose real-time EEG consciousness state to Claude Desktop.

## Mistakes Are Learnings (Read This First)

**Key mistakes in this session**:
1. **Didn't trace full code path first**: Fixed `extract_eeg_channels()` but missed that `use_precomputed=True` was bypassing it entirely → Wasted ~15 min → Should trace from entry point (monitor_realtime) through to emission
2. **Many accumulated background processes**: Started debug processes without killing old ones → Confusion about which session was active → Kill processes in separate command before starting new ones
3. **pkill in compound command**: `pkill -f X && uv run...` kills current process → Exit code 144 → Run pkill separately

**Time wasted**: ~20 min debugging why fix didn't work when precomputed mode was bypassing the fix

## Decisions
- **Auto-detect raw mode for osc_receiver**: OSC receiver CSV has raw EEG samples, not precomputed band powers like Mind Monitor exports. Extended auto-switch logic to include osc_receiver alongside muse_player.
- **Simple session ID generation**: Use `uuidgen` instead of complex Python session creation script for quick testing

## Implementation
- **consciousness_monitor/data/parsers.py:489-494**: Added `osc_receiver` case to `extract_eeg_channels()` - was completely missing, caused empty channel dict
- **consciousness_monitor/main.py:65**: Changed `== "muse_player"` to `in ("muse_player", "osc_receiver")` for auto raw-mode switch
- **scripts/consciousness_monitor_db_v2.py:196**: Fixed `result.primary_state` → `result.state` (wrong attribute name)
- **README.md**: Updated Database Integration section with simplified commands and debug mode

## Lessons
- ✅ Debug mode (`--debug`) reveals rule testing flow - showed 20% bands before detection started
- ✅ Checking CSV header (`head -1`) confirms format before deep debugging
- ❌ Fixed wrong layer first (extraction) when real issue was upstream (precomputed mode)
- 💡 When all bands show equal % (20% each), indicates no actual EEG data reaching FFT
- 💡 Format detection happens but processing path selection is separate logic

## Mistakes & Efficiency Improvements

### Tool Call Failures & Inefficiencies

| Tool | Issue | Better Approach |
|------|-------|-----------------|
| BashOutput | Checked old process (00cb63) that had stale data | Track which session ID is current |
| Bash | `pkill && uv run` killed self (exit 144) | Separate commands: `pkill`; then `uv run` |
| Bash | Multiple head -N piped outputs competed | Use single `head -100` then check output |

**Wasted tool calls:** ~5 BashOutput calls on stale/killed processes
**Sequential→Parallel opportunities:** Could have checked CSV header and Docker logs in parallel

### AI Agent Mistakes
1. **Fixed extraction layer before understanding flow**: Saw "extract_eeg_channels" had no osc_receiver case, fixed it. But monitor was using precomputed mode which bypasses extraction entirely. Should have traced: `monitor_realtime()` → `_analyze_precomputed_data()` vs `analyze_eeg_window()` → understood precomputed mode was wrong for raw data.

### Root Cause Chain
```
OSC receiver CSV (raw EEG)
  → detected as "osc_receiver" format ✓
  → use_precomputed=True (default)
  → _analyze_precomputed_data() called
  → looks for alpha_rel, beta_rel columns (don't exist)
  → returns equal 20% for all bands
  → NO_SIGNAL detected
  → emission triggered only once
```

Fix: Auto-switch to raw mode when osc_receiver format detected.

## Knowledge Gaps
- Missing: Documentation that osc_receiver format requires raw mode
- Unclear: Which formats have precomputed bands vs raw samples

## .claude Improvements

### REFERENCE.md (skills/eeg-analysis)
- [ ] Add format detection → processing mode table:
  - `mind_monitor` → precomputed (has alpha_rel, beta_rel columns)
  - `muse_player` → raw (has /muse/eeg messages)
  - `osc_receiver` → raw (has RAW_TP9 columns)

### CLAUDE.md
- [ ] Add: "When debugging EEG analysis showing equal band %s, check if format detection matches processing mode"

## MCP Server Implementation

### Decision
Built MCP server to expose EEG state to Claude Desktop, enabling attention-aware AI responses.

### Architecture
```
Muse → Mind Monitor → OSC → Python Monitor → TimescaleDB → MCP Server → Claude Desktop
```

### Implementation
- **scripts/eeg_mcp_server.py**: FastMCP server with 3 tools:
  - `get_current_eeg_state()` - Current state, band powers, interpretation, recommendations
  - `get_eeg_history(minutes)` - State transitions over time
  - `get_session_summary()` - All recording sessions
- **scripts/mcp-eeg-server**: Bash wrapper for WSL execution from Claude Desktop
- **Claude Desktop config**: Added `eeg-consciousness` server via WSL

### Key Pattern: WSL MCP Server
```json
"eeg-consciousness": {
  "command": "wsl",
  "args": ["-d", "Debian", "--exec", "/mnt/c/projects/MindMonitorPython/scripts/mcp-eeg-server"]
}
```

### State Interpretations
Claude receives recommendations based on detected state:
- DROWSY → "Keep responses short and clear"
- FOCUSED → "Can provide detailed technical information"
- ALERT_TENSE → "Be supportive and calming"

## Artifacts
- Files modified:
  - `consciousness_monitor/data/parsers.py` (extract_eeg_channels)
  - `consciousness_monitor/main.py` (auto raw-mode detection)
  - `scripts/consciousness_monitor_db_v2.py` (attribute fix)
  - `README.md` (database commands)
- Files created:
  - `scripts/eeg_mcp_server.py` (MCP server)
  - `scripts/mcp-eeg-server` (WSL wrapper)
- Config modified:
  - `C:/Users/konra/AppData/Roaming/Claude/claude_desktop_config.json`
- Commands run:
  - `docker compose -f docker/compose.yml exec db psql -U eeg -d eeg -c "SELECT COUNT(*) ... FROM eeg_window GROUP BY session_id"`
- Tests: Verified 27+ windows written to session in ~30 seconds, MCP tools return valid JSON
