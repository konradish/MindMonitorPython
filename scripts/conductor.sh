#!/bin/bash
# Neural Music Conductor
# Invokes Claude Code every N seconds to read EEG and control Strudel music
#
# Prerequisites:
# 1. EEG pipeline running (osc_receiver.py → TimescaleDB)
# 2. Windows Chrome with Strudel open on port 9223:
#    powershell.exe -Command "cd C:\projects\prompt-kit\chrome-automation; node scripts/chrome-launcher.mjs --profile=default 'https://strudel.cc'"
#
# Usage:
#    ./scripts/conductor.sh              # Default 10 second interval
#    ./scripts/conductor.sh --interval 5 # Custom interval
#    ./scripts/conductor.sh --dry-run    # Don't actually change music

set -e

# Configuration
CLAUDE_BIN="/home/kodell/.claude/local/claude"
INTERVAL=${INTERVAL:-10}
SESSION_FILE="/tmp/conductor_session.json"
LOG_FILE="/tmp/conductor.log"
PATTERN_FILE="/mnt/c/projects/prompt-kit/chrome-automation/pattern.txt"
CHROME_AUTO="C:\\projects\\prompt-kit\\chrome-automation"
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Initialize session state
init_session() {
    if [ ! -f "$SESSION_FILE" ]; then
        echo '{"last_states": [], "current_pattern": "none", "pattern_name": "none", "patterns_played": [], "patterns_generated": [], "last_change": 0, "iteration": 0}' > "$SESSION_FILE"
        echo "[$(date -Iseconds)] Session initialized" >> "$LOG_FILE"
    fi
}

# Beats library
BEATS_LIBRARY="/mnt/c/projects/MindMonitorPython/config/beats-library.yaml"

# Main conductor prompt
CONDUCTOR_PROMPT='You are the Neural Music Conductor. Be CONCISE - output only essential info.

## Tools & Files
- EEG: get_current_eeg_state(window_seconds=10)
- Session: '"$SESSION_FILE"'
- Beats library: '"$BEATS_LIBRARY"' (read patterns by mood, add new ones)
- Pattern file: '"$PATTERN_FILE"'

## Decision Flow
1. Read EEG state and session file
2. Check if music should change:
   - State different from last 2 reads → change
   - Same K_HIGH_LOAD for 3+ reads → definitely grounding
   - User might want variety → pick different pattern from library for same mood
   - No change needed → just report, do nothing

3. If changing music:
   a. Read beats-library.yaml, find patterns matching state moods
   b. EITHER pick existing pattern OR generate a new one (variety!)
   c. If generating: create single-line Strudel pattern using sawtooth/sine/triangle synths
   d. Write pattern to: '"$PATTERN_FILE"'
   e. Run: powershell.exe -Command "cd '"$CHROME_AUTO"'; $env:CDP_PORT=\"9223\"; node scripts/run-automation.mjs strudel-play-file.mjs pattern.txt"
   f. Update session with: state, pattern_name, last 3 states

4. If you generate a great new pattern:
   - Add it to beats-library.yaml under appropriate section
   - Give it a descriptive name and mood tags

## Pattern Rules
- Single line only (PowerShell compatibility)
- Use: sawtooth, sine, triangle, RolandTR808, RolandTR909
- NO: GM soundfonts, multiline, special chars

## Output (one line):
STATE: [state] | ACTION: [none|played:pattern_name|generated:name] | BANDS: a=[alpha]% b=[beta]%'

# Run one iteration
run_iteration() {
    local iteration=$(jq -r '.iteration' "$SESSION_FILE")
    iteration=$((iteration + 1))

    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "[$(date -Iseconds)] Iteration $iteration (interval: ${INTERVAL}s)"
    echo "═══════════════════════════════════════════════════════════════"

    if [ "$DRY_RUN" = true ]; then
        echo "[DRY RUN] Would invoke Claude with conductor prompt"
        # Just read EEG state without changing anything
        "$CLAUDE_BIN" --print -p "Call get_current_eeg_state() and report: STATE: [state] | BANDS: a=[alpha]% b=[beta]% | FRESH: [yes/no]" 2>&1
    else
        # Invoke Claude with full conductor prompt
        "$CLAUDE_BIN" --print --dangerously-skip-permissions -p "$CONDUCTOR_PROMPT" 2>&1 | tee -a "$LOG_FILE"
    fi

    # Update iteration count
    jq ".iteration = $iteration" "$SESSION_FILE" > "${SESSION_FILE}.tmp" && mv "${SESSION_FILE}.tmp" "$SESSION_FILE"
}

# Cleanup on exit
cleanup() {
    echo ""
    echo "[$(date -Iseconds)] Conductor stopped"
    echo "[$(date -Iseconds)] Conductor stopped" >> "$LOG_FILE"
}
trap cleanup EXIT

# Main loop
main() {
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║           NEURAL MUSIC CONDUCTOR                              ║"
    echo "╠═══════════════════════════════════════════════════════════════╣"
    echo "║  Interval: ${INTERVAL}s                                               ║"
    echo "║  Session:  $SESSION_FILE               ║"
    echo "║  Dry run:  $DRY_RUN                                              ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Press Ctrl+C to stop"
    echo ""

    init_session

    while true; do
        run_iteration
        sleep "$INTERVAL"
    done
}

main
