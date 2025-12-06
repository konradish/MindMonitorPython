# Session: LLM-Driven Neural Music Conductor

**Date:** 2025-12-06
**Duration:** ~45 min

## Summary

Replaced rule-based pattern selection with Claude Code CLI integration, enabling LLM-driven music decisions based on EEG brain state.

## Changes Made

### 1. Claude Code CLI Integration
- TUI now shells out to `claude -p` with EEG context
- Claude reads brain state, reasons about it, selects/creates patterns
- Writes decision to `/tmp/conductor_decision.json`
- TUI reads decision and plays pattern

### 2. Conductor Prompt (`config/conductor-prompt.md`)
- Comprehensive Strudel syntax reference
- Mini-notation symbols, core functions, pattern constructors
- Common mistakes to avoid (especially extra parentheses!)
- Brain state to music mapping guidelines
- Web search encouraged for fresh patterns

### 3. Reasoning Log
- All Claude decisions logged to `logs/conductor_reasoning.log`
- Includes timestamp, action, pattern name, reasoning
- Log directory added to `.gitignore`

### 4. Launch Script Updates
- LLM mode is now default
- `--simple` flag for rule-based fallback
- Shows mode on startup

### 5. Bug Fixes
- Pre-create decision file (Write tool requires read first)
- Truncate LLM reasoning in TUI display (100 chars)
- Added debug logging for Claude stderr

## Architecture

```
TUI polls EEG (3s)
    → Builds context (state, bands, current pattern, duration)
    → Calls: claude -p --tools 'Read,Write,WebSearch,WebFetch,mcp__eeg-consciousness__*'
    → Claude reads EEG, reasons, writes /tmp/conductor_decision.json
    → TUI reads decision, plays pattern via Chrome automation
    → Logs reasoning to logs/conductor_reasoning.log
```

## Key Files
- `scripts/conductor_tui.py` - Main TUI with `call_llm_conductor()` and `llm_decide_pattern()`
- `config/conductor-prompt.md` - System prompt with Strudel syntax docs
- `scripts/conductor` - Launch script with `--simple` fallback
- `logs/conductor_reasoning.log` - Decision history (gitignored)

## Environment Variables
- `LLM_CONDUCTOR=1` (default) - Use Claude Code for decisions
- `LLM_CONDUCTOR=0` - Use rule-based pattern matching

## Lessons Learned
- Claude's Write tool requires file to exist first (pre-create with placeholder)
- LLM calls can block UI updates - ThreadPoolExecutor helps but `future.result()` still blocks
- Extra parentheses are a common LLM code generation error - need explicit warnings
- 120s timeout needed for web searches
