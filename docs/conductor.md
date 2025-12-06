# Neural Music Conductor

Real-time music conductor responding to EEG neural states via Claude Code CLI.

## Architecture

```
Phone (Mind Monitor) → OSC → TimescaleDB → EEG MCP → Claude Code CLI → Windows Chrome → strudel.cc
                                                          ↑
                                              conductor.sh (10s loop)
```

**Execution Model:** Claude Code is invoked every 10 seconds by an external shell script. Each invocation reads the current EEG state and decides whether to evolve the music.

**Why Windows Chrome?** WSL2 audio routing is poor quality. Using native Windows Chrome via CDP (Chrome DevTools Protocol) gives proper audio output.

## Your Tools

### EEG MCP (eeg-consciousness)
- `get_current_eeg_state(window_seconds=10)` - Current state with 10s rolling average
- `get_band_timeseries(minutes=5, detail="summary")` - Band statistics over time
- `get_eeg_history(minutes=5)` - State transitions and distribution
- `get_transition_analysis(minutes=30)` - Stability metrics, rapid oscillations
- `query_band_events(band, operator, value, minutes)` - Find threshold crossings

### Windows Chrome Automation (for Strudel)
Located at `C:\projects\prompt-kit\chrome-automation\`:

**Launch Chrome:**
```bash
powershell.exe -Command "cd C:\projects\prompt-kit\chrome-automation; node scripts/chrome-launcher.mjs --profile=default 'https://strudel.cc'"
```

**Play a pattern:**
```bash
# Write pattern to file
echo 'stack(s("bd sd"), note("c3 g3").s("sawtooth"))' > /mnt/c/projects/prompt-kit/chrome-automation/pattern.txt

# Execute
powershell.exe -Command "cd C:\projects\prompt-kit\chrome-automation; \$env:CDP_PORT='9223'; node scripts/run-automation.mjs strudel-play-file.mjs pattern.txt"
```

**Helper script:** `scripts/strudel-play.sh "pattern code"`

## Neural State Signatures

States defined in TimescaleDB `state_definition` table:

| State | Signature | Interpretation |
|-------|-----------|----------------|
| **K_FLOW** | Alpha 30-45%, Beta 15-28%, Gamma <18% | Absorbed flow - engaged without strain. Sustainable focus. |
| **K_PLAYING** | Theta >15%, Beta <18%, Gamma <12% | Creative/musical absorption. Not thinking, being. |
| **K_DOWNSHIFT** | Alpha 26-50%, balanced | Conscious settling. Regulated return to calm. |
| **K_HIGH_LOAD** | Alpha 15-28%, Beta 20-34%, Gamma 18-38%, Delta >10% | High cognitive/sensory load. Could be frustrated or overwhelmed. |
| **K_THINKING** | Alpha <28%, Beta >18%, Gamma >15% | Active cognitive effort. Problem solving, calculation. |
| **K_MUSICAL_CHILLS** | Alpha 28-36%, Beta 18-26%, Gamma 15-22%, Theta 10-16% | Musical frisson - chills/emotional response to music. |

## Decision Framework

1. **Read state** via `get_current_eeg_state(window_seconds=10)`
2. **DON'T change music on every read** - only when:
   - State transition detected (different from last 2 reads)
   - Sustained intensity (same K_HIGH_LOAD for 3+ consecutive reads)
   - Significant band shift (>10% change in dominant band)
3. **FADE transitions** - use `.slow()`, gradual filter sweeps, tempo glide
4. **Log reasoning** before each change (written to session annotation)

## Musical Mappings

**Note:** Patterns must be single-line for PowerShell compatibility.

### K_FLOW (engaged, sustainable)
**Goal:** Warm, spacious, supportive without demanding attention

```javascript
stack(note("<C3 G3 Eb3 Bb2>/4").s("sawtooth").lpf(600).room(0.8).gain(0.4), s("~ hh*4").gain(0.2).lpf(800), note("c2 g1").s("sine").slow(2).gain(0.5))
```

### K_PLAYING (creative, loose)
**Goal:** Playful, surprising, room for exploration

```javascript
stack(s("bd [~ bd] ~ bd, ~ sd ~ [sd sd]").bank("RolandTR808"), note("<[c4 e4] [g4 b4] [a4 f4]>*2").s("triangle").delay(0.3).room(0.5), s("arpy*8").n(irand(12)).gain(0.3))
```

### K_DOWNSHIFT (settling, ambient)
**Goal:** Slow evolution, gentle landing

```javascript
stack(note("<Dm Am F Em>/4").s("sawtooth").lpf(500).room(0.9).gain(0.4), s("~ rim").slow(4).gain(0.15).room(0.8), note("d1").s("sine").decay(4).sustain(0.1).lpf(200)).slow(2)
```

### K_HIGH_LOAD (overwhelmed, grounding needed)
**Goal:** Sparse, slow, grounding - reduce complexity immediately

```javascript
stack(s("bd").slow(2).gain(0.6).lpf(100), note("c1").s("sine").decay(2).sustain(0).slow(4))
```

### K_THINKING (focused cognition)
**Goal:** Rhythmic structure that supports without distracting

```javascript
stack(s("bd*4, ~ sd ~ sd, hh*8").bank("RolandTR909").gain(0.5), note("<c3 g2 c3 g2>/2").s("sawtooth").lpf(400)).lpf(sine.range(800,2000).slow(16))
```

### K_MUSICAL_CHILLS (peak experience)
**Goal:** Enhance the moment - soaring, expansive

```javascript
stack(note("<Cm Am Fm Gm>/2").s("sawtooth").lpf(900).room(0.9).gain(0.5), note("c4 g4 eb5 g5").s("triangle").slow(2).delay(0.3).gain(0.4))
```

## Strudel Pattern Techniques

### Transitions (FADE, don't jump)
```javascript
// Slow crossfade via gain automation
.gain(sine.range(0, 0.6).slow(16))

// Filter sweep
.lpf(sine.range(200, 4000).slow(8))

// Tempo glide (use with caution)
setcps(saw.range(0.3, 0.6).slow(32))
```

### Common Modifiers
```javascript
// Spatial
.room(0.8)        // reverb amount
.delay(0.25)      // delay mix
.size(4)          // reverb size

// Tonal
.lpf(freq)        // low-pass filter
.hpf(freq)        // high-pass filter
.shape(0.3)       // soft saturation

// Rhythmic
.slow(2)          // half speed
.fast(2)          // double speed
.ply("2")         // double notes
.rarely(fn)       // occasional variation
```

## Execution

### Starting a Session

```bash
# Terminal 1: EEG pipeline
docker compose -f docker/compose.yml up -d db
DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" uv run python scripts/osc_receiver.py

# Terminal 2: Launch Windows Chrome with Strudel
powershell.exe -Command "cd C:\projects\prompt-kit\chrome-automation; node scripts/chrome-launcher.mjs --profile=default 'https://strudel.cc'"

# Terminal 3: Claude Code (manual conductor mode)
claude
```

### Manual Conductor Mode

In Claude Code, say things like:
- "Read my brain state and play matching music"
- "I'm in K_FLOW, play something warm and spacious"
- "Check my EEG and evolve the music"
- "I'm feeling overwhelmed, switch to K_HIGH_LOAD pattern"

### Automated Conductor Script (`scripts/conductor.sh`)

```bash
#!/bin/bash
# Neural Music Conductor - invokes Claude Code every 10 seconds

SESSION_FILE="/tmp/conductor_session.json"

# Initialize session state
if [ ! -f "$SESSION_FILE" ]; then
    echo '{"last_states": [], "current_pattern": "none"}' > "$SESSION_FILE"
fi

while true; do
    claude --print --dangerously-skip-permissions \
        -p "You are the Neural Music Conductor.
            1. Read EEG via get_current_eeg_state()
            2. Check session at $SESSION_FILE for last states
            3. If state changed significantly, write new pattern to /mnt/c/projects/prompt-kit/chrome-automation/pattern.txt
            4. Run: powershell.exe -Command \"cd C:\\projects\\prompt-kit\\chrome-automation; \\\$env:CDP_PORT='9223'; node scripts/run-automation.mjs strudel-play-file.mjs pattern.txt\"
            5. Update session file
            Be concise. Single-line Strudel patterns only." \
        2>&1 | tee -a /tmp/conductor.log

    sleep 10
done
```

## Testing

```bash
# Test EEG MCP
DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" uv run python scripts/eeg_mcp_server.py --test

# Test Strudel via Windows Chrome
powershell.exe -Command "cd C:\projects\prompt-kit\chrome-automation; node scripts/chrome-launcher.mjs --profile=default 'https://strudel.cc'"
# Then in Claude Code:
# > Play a simple kick pattern on strudel
```

## Notes

- **Audio:** Uses Windows Chrome (CDP port 9223) for native audio quality
- **Patterns:** Must be single-line to avoid PowerShell escaping issues
- **Chrome scripts:** Located at `C:\projects\prompt-kit\chrome-automation\`
- **Pattern library:** Sourced from [awesome-strudel](https://github.com/terryds/awesome-strudel), [strudel.cc workshop](https://strudel.cc/workshop/getting-started/)
