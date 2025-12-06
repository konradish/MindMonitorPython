# Neural Music Conductor Setup - 2025-12-06

## Context
Set up proof of concept for neural music conductor: EEG brain states from Muse headband controlling Strudel live coding music via Claude Code. Grounded the speculative conductor.md in reality, discovered WSL audio issues, pivoted to Windows Chrome automation.

## Mistakes Are Learnings (Read This First)

**Key mistakes in this session**:
1. **Tried Strudel MCP first**: Assumed MCP would handle everything cleanly → WSL Chromium audio sounds awful → Should test audio output path before committing to architecture
2. **Puppeteer MCP doesn't connect to existing browsers**: Called `puppeteer_navigate` expecting it to use Windows Chrome on port 9223 → It launched new WSL browser → Should have checked MCP capabilities first
3. **PowerShell multiline string escaping**: Passed multiline pattern via PowerShell command → String got truncated to 29 chars → Use file-based transfer for any non-trivial strings
4. **Used `page.waitForTimeout()`**: Newer Puppeteer removed this method → Script failed → Use `await new Promise(r => setTimeout(r, ms))` instead
5. **Ctrl+Enter for Strudel play**: Assumed keyboard shortcut would work → Nothing happened → Click "update" button explicitly

**Time wasted**: ~15 minutes debugging audio path and Puppeteer MCP connection. Could have been prevented by asking user about preferred audio output first.

## Decisions
- **Windows Chrome via CDP**: WSL2 audio routing is poor quality. Native Windows Chrome on port 9223 gives proper audio. Uses existing `prompt-kit/chrome-automation` scripts.
- **File-based pattern transfer**: PowerShell escaping is unreliable. Write patterns to `pattern.txt`, script reads from file.
- **Single-line patterns**: Multiline causes escaping issues. All pattern examples converted to single-line format.
- **Keep Strudel MCP installed**: Still useful for headless/testing scenarios, but not primary path.

## Implementation
- Updated `docs/conductor.md`: Architecture diagram, Windows Chrome instructions, single-line patterns for all K_* states, execution scripts
- Created `chrome-automation/strudel-play-file.mjs`: Reads pattern from file, types into CodeMirror editor, clicks update
- Created `chrome-automation/take-screenshot.mjs`: Debug helper for seeing browser state
- Created `scripts/strudel-play.sh`: Wrapper script for easy pattern deployment
- Verified K_* states exist: K_FLOW, K_PLAYING, K_DOWNSHIFT, K_HIGH_LOAD, K_THINKING, K_MUSICAL_CHILLS all in database

## Lessons
- ✅ Windows Chrome automation via CDP works reliably from WSL
- ✅ File-based data transfer avoids all escaping issues
- ✅ Strudel responds to CodeMirror keyboard input + button clicks
- ❌ Strudel MCP uses WSL Playwright → bad audio
- ❌ Puppeteer MCP can't connect to existing browsers
- 💡 Always test audio output path before building audio-dependent features
- 💡 PowerShell + WSL + special characters = pain. Use files.

## Mistakes & Efficiency Improvements

### Tool Call Failures & Inefficiencies

| Tool | Issue | Better Approach |
|------|-------|-----------------|
| mcp__puppeteer__puppeteer_navigate | Launched new browser instead of connecting to port 9223 | Use Windows chrome-automation scripts directly |
| Bash (PowerShell inline) | Multiline pattern truncated | Write to file first, then execute |
| mcp__strudel__* | Audio played through WSL (poor quality) | User had to tell me about Windows Chrome setup |

**Wasted tool calls:** 3 Puppeteer MCP calls that created wrong browser
**Sequential→Parallel opportunities:** Could have searched for Strudel patterns and checked DB states in parallel (did this correctly)

### AI Agent Mistakes
1. **Assumed MCP = best path**: Strudel MCP seemed like the obvious choice. Should have asked about audio routing preferences first.
2. **Didn't read global CLAUDE.md carefully enough**: Windows Chrome automation instructions were there, I found them only after user reminded me.

### Times AI Correctly Pushed Back
- **Questioned original conductor.md execution model**: Correctly identified that Claude can't run continuous loops, proposed CLI invocation approach.

## Knowledge Gaps
- Missing: Documentation on Puppeteer MCP's inability to connect to existing browsers
- Unclear: Best practices for WSL → Windows audio routing

## .claude Improvements

### CLAUDE.md
- [ ] Add note: "For audio output, use Windows Chrome automation, not WSL-based tools"

### REFERENCE.md
- [ ] Add to Windows Chrome automation section: Strudel control pattern with `strudel-play-file.mjs`

## Project Enhancements (Code-Level Work)

### Feature Ideas
- [ ] **Conductor loop script**: Implement `scripts/conductor.sh` that polls EEG and updates music - Priority: P1
- [ ] **Pattern library file**: Store tested patterns in `config/strudel-patterns.yaml` keyed by state - Priority: P1
- [ ] **Strudel stop script**: Add `strudel-stop.mjs` to pause/stop playback - Priority: P2

### Testing Gaps
- [ ] No automated test for EEG→Strudel pipeline
- [ ] Pattern syntax validation before sending to browser

## Related Sessions
- First session establishing neural music conductor concept

## Artifacts
- Files modified: `docs/conductor.md`
- Files created: `chrome-automation/strudel-play-file.mjs`, `chrome-automation/take-screenshot.mjs`, `scripts/strudel-play.sh`
- Packages installed: `@williamzujkowski/strudel-mcp-server@2.2.0`, Playwright Chromium
- Chrome: Running on port 9223 with strudel.cc loaded
