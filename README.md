# Mind Monitor Python EEG Analysis System

Real-time EEG consciousness monitoring and therapeutic pattern detection for Mind Monitor (Muse headband).

## Quick Start: Recording EEG Data

### 1. Start the OSC Receiver (Docker - Recommended)

```bash
# Start the receiver
docker compose -f docker/docker-compose.osc.yml up -d

# View logs to get your IP address
docker compose -f docker/docker-compose.osc.yml logs -f
```

### 2. Configure Mind Monitor App

1. Open Mind Monitor on your phone
2. Go to Settings > OSC Stream
3. Set **IP Address**: Your computer's IP (shown in Docker logs)
4. Set **Port**: `5000`
5. Enable OSC streaming

### 3. Start Recording

1. In Mind Monitor, tap **Marker 1** to start recording
2. Data saves to `OSC-Python-Recording.csv`
3. Tap **Marker 2** to stop recording

### 4. Run Consciousness Analysis

```bash
# Real-time therapeutic monitoring (recommended)
uv run python -m consciousness_monitor --konrad-mode

# Analyze a recorded session
uv run python -m consciousness_monitor --analyze --file OSC-Python-Recording.csv --konrad-mode
```

## Installation

```bash
# Install dependencies
uv sync
```

## Project Structure

```
MindMonitorPython/
├── consciousness_monitor/     # Main analysis package
├── scripts/                   # OSC receivers and utilities
│   ├── osc_receiver.py       # Main OSC data receiver
│   ├── osc_receiver_audio.py # With audio feedback
│   └── osc_receiver_simple.py
├── tests/                     # Test files
├── analysis/                  # Analysis and debug scripts
├── data/                      # Recorded EEG data files
├── docs/                      # Documentation
├── docker/                    # Docker configuration
├── tools/                     # Data ingestion tools
├── config/                    # Configuration files
├── assets/                    # Media files (sounds, images)
├── archive/                   # Legacy/backup scripts
└── sql/                       # Database schemas
```

## Consciousness Monitor

The main analysis system with therapeutic pattern detection.

### Features

- **Clinical EEG Analysis**: Delta, Theta, Alpha, Beta, Gamma bands
- **Therapeutic Patterns**: Jhana states, IFS parts detection, startle responses
- **Real-time Processing**: 0.75-1.0 second windows
- **Configuration-Driven**: External JSON rules for customization

### Usage

```bash
# Standard monitoring
uv run python -m consciousness_monitor

# Therapeutic mode (recommended)
uv run python -m consciousness_monitor --konrad-mode

# Debug mode
uv run python -m consciousness_monitor --debug --konrad-mode

# Tune thresholds
uv run python -m consciousness_monitor --tune-rule jhana.alpha_min=85

# Custom window/update rate
uv run python -m consciousness_monitor --window 1.0 --update 2
```

### Detected States

**Therapeutic Patterns:**
- JHANA/TRANSCENDENT - Deep meditative absorption
- YOUNG PART CONNECTED - Vulnerable, childlike state
- HOPEFUL PART ACTIVE - Optimistic consciousness
- SECURITY GUARD ACTIVE - Threat detection

**Standard Patterns:**
- RELAXED, FOCUSED, CREATIVE/FLOW, MEDITATIVE, DROWSY, PEAK FOCUS, ALERT/TENSE

## Real-time Database Streaming

Stream EEG data directly to TimescaleDB as you wear the headband.

### Quick Start (WSL)

```bash
# Terminal 1 (PowerShell on Windows):
cd C:\projects\MindMonitorPython && python scripts/udp_forward_to_wsl.py

# Terminal 2 (WSL):
docker compose -f docker/compose.yml up -d db
DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" uv run python scripts/osc_receiver.py
```

Configure Mind Monitor to send to your Windows IP on port 5000. Database recording starts automatically on first EEG packet (no Marker 1 needed).

### Band Power Source

The OSC receiver uses Mind Monitor's pre-computed absolute band powers (`/muse/elements/*_absolute`), converting them from log-scale dB to relative percentages. This is more accurate than computing FFT from raw samples.

## Database Integration (TimescaleDB)

Store EEG analysis windows and detections in TimescaleDB for later analysis.

### Setup

```bash
# Start TimescaleDB
docker compose -f docker/compose.yml up -d db

# Generate a session ID
SESSION_ID=$(uuidgen)
echo "Session ID: $SESSION_ID"
```

### Run with Database Logging (from CSV)

The monitor auto-detects OSC receiver format and switches to raw signal processing.

```bash
# Database-only mode (silent, writes ~1 window/second to DB)
DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" \
  uv run python scripts/consciousness_monitor_db_v2.py \
  --db-only --session-id $SESSION_ID --konrad-mode --csv OSC-Python-Recording.csv

# With debug output (see database emissions)
DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" \
  uv run python scripts/consciousness_monitor_db_v2.py \
  --db-only --debug --session-id $SESSION_ID --konrad-mode --csv OSC-Python-Recording.csv

# Dual mode (UI + database)
DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" \
  uv run python scripts/consciousness_monitor_db_v2.py \
  --dual --double-parse-ok --session-id $SESSION_ID --konrad-mode --csv OSC-Python-Recording.csv
```

### Query Data

```bash
# Check window count for session
docker compose -f docker/compose.yml exec db \
  psql -U eeg -d eeg -c "SELECT COUNT(*) FROM eeg_window WHERE session_id = '$SESSION_ID';"

# View windows by session
docker compose -f docker/compose.yml exec db \
  psql -U eeg -d eeg -c "SELECT COUNT(*) as windows, session_id FROM eeg_window GROUP BY session_id ORDER BY windows DESC;"

# View recent windows with band powers
docker compose -f docker/compose.yml exec db \
  psql -U eeg -d eeg -c "SELECT ts_start, alpha_rel, beta_rel, delta_rel FROM eeg_window ORDER BY ts_start DESC LIMIT 5;"
```

## Alternative: Direct Python OSC Receiver

If Docker isn't available:

```bash
uv run python scripts/osc_receiver.py
```

Note: On WSL, you may need to configure port forwarding manually. See [CLAUDE.md](CLAUDE.md) for troubleshooting.

## Technical Details

- **Sample Rate**: 256 Hz (Muse standard)
- **Signal Range**: 200-1200 µV typical
- **Frequency Bands**: Delta (0.5-4Hz), Theta (4-8Hz), Alpha (8-13Hz), Beta (13-30Hz), Gamma (30-50Hz)
- **Channels**: TP9 (left ear), AF7 (left forehead), AF8 (right forehead), TP10 (right ear)

## License

See [LICENSE](LICENSE) file.
