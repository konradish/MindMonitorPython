# Neural Music Conductor

Real-time music conductor responding to EEG neural states.

## Quick Start

```bash
./scripts/conductor
```

That's it. This starts the database, launches Chrome with Strudel, and opens the TUI.

## Architecture

```
Phone (Mind Monitor) → OSC → TimescaleDB → Conductor TUI → Windows Chrome → strudel.cc
                                                ↓
                                    [Space] Pause  [N] Next  [R] Regen
                                    [Enter] Queue msg  [Ctrl+Enter] Send now
```

**Execution Model:** The TUI polls EEG state every 3 seconds and automatically selects patterns from the beats library. You can interject messages at any time.

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

## Beats Library

The conductor maintains a curated library of patterns at `config/beats-library.yaml`.

### Library Structure
```yaml
library:
  pattern_name:
    pattern: 'single-line Strudel code'
    moods: [grounding, minimal, etc]
    source: original|generated|web
    notes: "Description"

mood_state_map:
  K_HIGH_LOAD: [grounding, minimal, calming]
  K_FLOW: [flow, warm, chill]
  # etc...
```

### Pattern Selection
1. Conductor reads EEG state
2. Maps state to moods via `mood_state_map`
3. Selects pattern with matching moods
4. Can generate new patterns for variety
5. Saves good generated patterns to library

### Pattern Rules
- **Single-line only** (PowerShell compatibility)
- **Use:** `sawtooth`, `sine`, `triangle`, `RolandTR808`, `RolandTR909`
- **Avoid:** GM soundfonts (unreliable loading), multiline, special chars

## Musical Mappings

Core patterns from the library:

| State | Goal | Moods |
|-------|------|-------|
| K_FLOW | Warm, spacious, supportive | flow, warm, chill |
| K_PLAYING | Playful, room for exploration | playful, creative, funky |
| K_DOWNSHIFT | Slow evolution, gentle landing | ambient, settling, peaceful |
| K_HIGH_LOAD | Sparse, grounding, reduce complexity | grounding, minimal |
| K_THINKING | Rhythmic structure, focus support | focus, steady, rhythmic |
| K_MUSICAL_CHILLS | Enhance peak experience | peak, soaring, emotional |

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

## Example: Full Track with Vocals

ATB - 9pm (Till I Come) recreation demonstrating samples, chord progressions, and arrangement:

```javascript
// ATB - 9pm (Till I Come) - CORRECTED from XM analysis
// BPM: 140, Key: A minor, Progression: Am - Am - Dm - F
const bpm = 140

samples({
  tillIcome: 'https://raw.githubusercontent.com/konradish/music/main/till%20i%20come.wav',
  changeIt: 'https://raw.githubusercontent.com/konradish/music/main/change%20it%20and%20say.wav'
})

stack(
  // === SUB BASS DRONE ===
  note("a0")
    .s("sawtooth")
    .lpf(120)
    .gain(0.12),

  // === 16TH NOTE ARPEGGIO (C5+C6 octave pulse) ===
  note("<[c5,c6] [c5,c6] [d5,d6] [f5,f6]>/4")
    .s("sawtooth")
    .lpf(2000)
    .gain(0.08)
    .struct("1*16"),

  // === LEAD (Kurtis transcription) ===
  note(`[
    ~ a4 a4 b4 a4
    ~ c5 ~ c5 ~ c5 e5 d5
    f4@2 ~ f4 g4 a4 g4
    ~ a4 ~ c5 ~ c5 d5 c5
    g4@3
  ]/6`)
    .s("sawtooth")
    .lpf(4500)
    .delay(0.4).dfb(0.55).dt(60/bpm/2)
    .room(0.2)
    .gain(0.18)
    .mask("<0 0 0 1 1 1>".slow(6)),

  // === PAD - CORRECT PROGRESSION: Am Am Dm F ===
  note("<[a3,c4,e4] [a3,c4,e4] [d4,f4,a4] [f4,a4,c5]>/6")
    .s("gm_pad_choir")
    .lpf(1200)
    .room(0.5)
    .gain(0.05),

  // === BASS (follows chord roots) ===
  note("<a1 a1 d2 f1>/6")
    .s("sawtooth")
    .lpf(500)
    .gain(0.1)
    .mask("<0 1 1 1 1 0>".slow(6)),

  // === KICK ===
  s("bd*4").bank("RolandTR909").gain(0.16)
    .mask("<0 0 1 1 1 0>".slow(6)),

  // === CLAP ===
  s("~ cp ~ cp").bank("RolandTR909").room(0.25).gain(0.08)
    .mask("<0 0 1 1 1 0>".slow(6)),

  // === HATS ===
  s("hh*8").bank("RolandTR909").gain(0.05)
    .mask("<0 0 0 0 1 0>".slow(6)),

  // === VOCALS ===
  s("tillIcome")
    .struct("[1 ~ ~ ~] [~ ~ 1 ~] [~ ~ ~ ~] [1 ~ ~ ~]")
    .slow(4)
    .gain(0.3),

  s("changeIt")
    .struct("[~ ~ ~ ~] [~ ~ ~ ~] [~ 1 ~ ~] [~ ~ ~ ~]")
    .slow(4)
    .gain(0.3)

).gain(0.35).cpm(bpm/4)
```

**Key techniques:**
- `samples({...})` - Load external wav files
- `mask("<0 0 1 1 1 0>".slow(6))` - Arrangement automation (6-bar cycle)
- `struct("1*16")` - Force 16th note rhythm
- `note("<...>/6")` - Distribute chord progression over 6 bars
- `.dt(60/bpm/2)` - Tempo-synced delay (8th notes)

## Execution

### One Command Start

```bash
./scripts/conductor
```

This handles everything:
1. Starts the database (if not running)
2. Launches Chrome with Strudel
3. Opens the TUI

**Other options:**
```bash
./scripts/conductor --tui    # Just TUI (db/chrome already running)
./scripts/conductor --stop   # Stop everything
./scripts/conductor --help   # Show help
```

### Prerequisites (separate terminal)

The OSC receiver must be running to get EEG data:
```bash
DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" uv run python scripts/osc_receiver.py
```

### TUI Layout
```
+------------------+------------------+
| Brain State      | Current Pattern  |
| K_FLOW    LIVE   | flow_warm_groove |
| a Alpha ###----- | Moods: flow,warm |
| b Beta  ##------ | Duration: 2:30   |
| ...              | [Space] [N] [R]  |
+------------------+------------------+
| State History (5 min)              |
| K_FLOW(12) -> K_THINKING(3) -> ... |
+------------------------------------+
| Log                                |
| 14:32:01 Playing: flow_warm_groove |
+------------------------------------+
| > Type message here (Enter/Ctrl+E) |
+------------------------------------+
```

**Keybindings:**
| Key | Action |
|-----|--------|
| `Space` | Pause/resume conductor |
| `N` | Force next pattern |
| `R` | Regenerate (different pattern) |
| `Enter` | Queue message for next cycle |
| `Ctrl+Enter` | Send message immediately |
| `Q` | Quit |

**Interjection Examples:**
- "this is too repetitive" - triggers pattern change
- "something more complex" - increases complexity
- "calmer please" - shifts to grounding patterns

### Alternative: Claude Code Mode

You can also use Claude Code directly for manual control:
- "Read my brain state and play matching music"
- "I'm in K_FLOW, play something warm and spacious"
- "I'm feeling overwhelmed, switch to K_HIGH_LOAD pattern"

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
