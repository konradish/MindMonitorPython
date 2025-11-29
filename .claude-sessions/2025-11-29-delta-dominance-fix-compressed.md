# Delta Dominance Bug Fix & Auto-Start - 2025-11-29

## Context
Database showed 80-92% delta band power while Mind Monitor displayed different values. User suggested binary search debugging approach: validate raw UDP data before calculations. Also added auto-start feature for database recording.

## Mistakes Are Learnings (Read This First)

**Key mistakes in this session**:
1. **Original code assumed relative bands available**: Code waited for `/muse/elements/*_relative` messages that Mind Monitor doesn't send by default → 80-92% delta (bogus FFT fallback) → Added absolute band handler as fallback
2. **Not validating OSC message format first**: Should have created debug receiver earlier to see what Mind Monitor actually sends → Would have found root cause faster → Create osc_debug.py for raw message inspection

**Time wasted**: ~30 minutes debugging FFT code when the issue was message format. Could have been prevented by dumping raw OSC messages first.

## Decisions
- **Use absolute bands as primary source**: Mind Monitor's `/muse/elements/*_absolute` is always available, `/muse/elements/*_relative` requires app setting. Absolute bands are log-scale (dB), convert with `10^dB_value`.
- **Auto-start database sessions**: No need for Marker 1 tap. Session starts on first EEG packet. Reduces friction.
- **Three-tier band power source**: 1) relative (if available) → 2) absolute (convert dB) → 3) FFT fallback (least accurate)

## Implementation

### scripts/osc_receiver.py
- Added `absolute_bands` dictionary to store dB values
- Added `absolute_band_handler()` for `/muse/elements/*_absolute` messages
- Modified `emit_to_database()` priority: relative → absolute → FFT
- dB-to-linear conversion: `linear_powers[band] = 10 ** db_val`
- Added `AUTO_START_DB = True` flag
- Auto-create `session_id` in `eeg_handler()` on first EEG packet

### scripts/osc_debug.py (new)
- Minimal debug receiver that prints all OSC messages
- Shows message counts and sample values
- Critical for diagnosing OSC format issues

### scripts/udp_forward_to_wsl.py (new)
- Bridges UDP from Windows to WSL (netsh portproxy doesn't support UDP)
- Gets WSL IP via `wsl -e ip addr show eth0`
- Required for Mind Monitor → WSL data flow

### Documentation
- README.md: Added "Real-time Database Streaming" section with WSL quick start
- CLAUDE.md: Updated band power source hierarchy, auto-start info

## Lessons
- ✅ Binary search debugging works: validate raw data before calculations
- ✅ osc_debug.py should be first step for OSC issues
- ❌ Assumed Mind Monitor output format without verification
- 💡 Mind Monitor absolute bands are log-scale dB, not linear power
- 💡 WSL2 UDP requires manual forwarding (no native support)

## Technical Details

### Mind Monitor OSC Messages
```
/muse/elements/alpha_absolute: 0.57  (dB, log10 scale)
/muse/elements/beta_absolute: 0.04
/muse/elements/delta_absolute: 0.16
/muse/elements/theta_absolute: 0.35
/muse/elements/gamma_absolute: -0.19
```

### dB to Percentage Conversion
```python
# Convert from log-scale to linear power
linear_powers = {band: 10 ** db_val for band, db_val in absolute_bands.items()}
# Normalize to percentages
total_power = sum(linear_powers.values())
percentages = {band: (p / total_power) * 100 for band, p in linear_powers.items()}
```

### Result
- Delta: 80-92% → ~15% (realistic)
- Source field in DB: `mind_monitor_absolute`

## Mistakes & Efficiency Improvements

### Tool Call Failures & Inefficiencies
| Tool | Issue | Better Approach |
|------|-------|-----------------|
| Multiple osc_receiver restarts | Had to kill old processes multiple times | Use `pkill -f osc_receiver` before starting |

**Wasted tool calls**: ~5 calls killing/restarting receiver processes
**Sequential→Parallel opportunities**: Git status/diff/log could run in parallel

### AI Agent Mistakes
1. **Focused on FFT code first**: Assumed calculation bug when actual issue was missing input data. Should validate inputs before debugging calculations.

### Times AI Correctly Identified
- **Created osc_debug.py**: User's "binary search" suggestion led to raw message inspection, which found root cause immediately.

## .claude Improvements

### REFERENCE.md (detailed technical info)
- [ ] Add to `skills/eeg-processing/REFERENCE.md`: Mind Monitor OSC message format
  - Absolute bands: `/muse/elements/*_absolute` (dB, always available)
  - Relative bands: `/muse/elements/*_relative` (0-1, requires app setting)
  - dB conversion formula: `10^dB_value`

### CLAUDE.md
- [x] Already updated with band power source hierarchy

## Related Sessions
- 2025-11-28-osc-receiver-db-emission-fix: Initial database integration work

## Artifacts
- Files modified: `scripts/osc_receiver.py`, `README.md`, `CLAUDE.md`
- Files created: `scripts/osc_debug.py`, `scripts/udp_forward_to_wsl.py`
- Commands: `uv run python scripts/osc_debug.py` (debug OSC messages)
- Commit: `28a3f3b` - "Fix delta dominance bug and add auto-start database recording"
