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
        echo '{"last_states": [], "current_pattern": "none", "last_change": 0, "iteration": 0}' > "$SESSION_FILE"
        echo "[$(date -Iseconds)] Session initialized" >> "$LOG_FILE"
    fi
}

# Main conductor prompt
CONDUCTOR_PROMPT='You are the Neural Music Conductor. Be CONCISE - output only essential info.

1. Call get_current_eeg_state(window_seconds=10) to read current brain state
2. Read session file: '"$SESSION_FILE"'
3. Decide if music should change based on:
   - State different from last 2 reads → change
   - Same K_HIGH_LOAD for 3+ reads → definitely change to grounding
   - No change needed → just report state, do nothing

4. If changing music:
   - Look up pattern from config/strudel-patterns.yaml for the detected state
   - Write ONLY the pattern (single line) to: '"$PATTERN_FILE"'
   - Run: powershell.exe -Command "cd '"$CHROME_AUTO"'; $env:CDP_PORT=\"9223\"; node scripts/run-automation.mjs strudel-play-file.mjs pattern.txt"
   - Update session file with new state

5. Output format (one line):
   STATE: [state] | ACTION: [none|changed to X] | BANDS: a=[alpha]% b=[beta]%'

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
        claude --print -p "Call get_current_eeg_state() and report: STATE: [state] | BANDS: a=[alpha]% b=[beta]% | FRESH: [yes/no]" 2>&1
    else
        # Invoke Claude with full conductor prompt
        claude --print --dangerously-skip-permissions -p "$CONDUCTOR_PROMPT" 2>&1 | tee -a "$LOG_FILE"
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
