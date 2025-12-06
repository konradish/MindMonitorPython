# Session: TUI Chrome Automation Fix + ATB Example

**Date:** 2025-12-06
**Duration:** ~30 min

## Summary

Fixed conductor TUI's inability to control Chrome/Strudel and added ATB "9pm (Till I Come)" as a full example pattern with vocal samples.

## Changes Made

### 1. GitHub Music Repo
- Created `https://github.com/konradish/music`
- Uploaded vocal samples:
  - `till i come.wav`
  - `change it and say.wav`
- Public raw URLs for Strudel `samples({})` usage

### 2. ATB Pattern Example
- Added full recreation to `docs/conductor.md` (Example: Full Track with Vocals section)
- Added to `config/beats-library.yaml` as `atb_till_i_come` with multiline YAML (`|`)
- Key: A minor, BPM: 140, Progression: Am - Am - Dm - F
- Uses `mask()` for 6-bar arrangement automation

### 3. TUI Chrome Control Fix
**Problem:** TUI showed "playing" but Chrome/Strudel didn't change patterns

**Root cause:** Async subprocess (`asyncio.create_subprocess_shell`) not working correctly within Textual's event loop

**Fix in `scripts/conductor_tui.py`:**
- Changed from async subprocess to sync `subprocess.run`
- Wrapped in `concurrent.futures.ThreadPoolExecutor` to avoid blocking
- Added automation output logging for debugging

```python
# Before (broken)
async def play_pattern(pattern_code: str) -> bool:
    proc = await asyncio.create_subprocess_shell(cmd, ...)
    await proc.communicate()

# After (working)
def play_pattern_sync(pattern_code: str) -> tuple[bool, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return True, result.stdout

# Called via ThreadPoolExecutor in change_pattern()
```

### 4. Strudel Automation Script Fix
- Updated `strudel-play-file.mjs` to use Ctrl+Enter instead of clicking "update" button
- Button selector was unreliable

## Files Modified
- `docs/conductor.md` - Added ATB example section
- `config/beats-library.yaml` - Added `atb_till_i_come` pattern
- `scripts/conductor_tui.py` - Fixed subprocess handling

## Lessons Learned
- Textual + async subprocess = problematic; use ThreadPoolExecutor for external commands
- Strudel keyboard shortcuts (Ctrl+Enter) more reliable than button clicks via Puppeteer
- YAML multiline (`|`) works fine for complex Strudel patterns
