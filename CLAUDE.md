# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python project for processing and analyzing real-time EEG (brainwave) data from Mind Monitor via OSC (Open Sound Control). The system receives live EEG streaming from a Muse headband through the Mind Monitor mobile app and provides consciousness/mental state analysis.

## Project Structure

```
MindMonitorPython/
├── consciousness_monitor/     # Main analysis package (modular architecture)
├── scripts/                   # OSC receivers and utilities
│   ├── osc_receiver.py       # Main OSC data receiver
│   ├── osc_receiver_audio.py # With audio feedback
│   ├── osc_receiver_simple.py
│   └── realtime_consciousness_analyzer.py
├── tests/                     # Test files
├── analysis/                  # Analysis and debug scripts
├── data/                      # Recorded EEG data files (gitignored)
├── docs/                      # Documentation
├── docker/                    # Docker configuration
│   ├── docker-compose.osc.yml
│   ├── Dockerfile.osc
│   ├── compose.yml
│   └── Dockerfile
├── tools/                     # Data ingestion tools
├── config/                    # External configuration files
├── assets/                    # Media files (sounds, images)
├── archive/                   # Legacy/backup scripts (gitignored)
└── sql/                       # Database schemas
```

## Development Commands

### Environment Setup

```bash
uv sync
```

### Running Components

#### OSC Data Reception (Docker - Recommended)

```bash
# Start OSC receiver
docker compose -f docker/docker-compose.osc.yml up -d

# View logs (shows IP address to use)
docker compose -f docker/docker-compose.osc.yml logs -f

# Stop
docker compose -f docker/docker-compose.osc.yml down
```

**Mind Monitor App Configuration:**
- **IP Address:** Your Windows IP (shown in Docker logs)
- **Port:** 5000
- **Protocol:** UDP

**Recording:** Tap Marker 1 to start, Marker 2 to stop. Data saves to `OSC-Python-Recording.csv`.

#### Direct Python (Alternative)

```bash
uv run python scripts/osc_receiver.py
```

#### Consciousness Analysis

```bash
# Therapeutic monitoring (recommended)
uv run python -m consciousness_monitor --konrad-mode

# Basic monitoring
uv run python -m consciousness_monitor

# Debug mode
uv run python -m consciousness_monitor --debug --konrad-mode

# Analyze recording
uv run python -m consciousness_monitor --analyze --file OSC-Python-Recording.csv --konrad-mode
```

## Key Technical Details

### EEG Signal Processing
- Sample rate: 256 Hz (Muse standard)
- Mind Monitor outputs microvolts directly
- Typical signal range: 200-1200 µV
- **Optimal window: 0.75-1.0 seconds**
- **Minimal preprocessing: DC removal only** (preserves alpha)
- Frequency bands: Delta (0.5-4Hz), Theta (4-8Hz), Alpha (8-13Hz), Beta (13-30Hz), Gamma (30-50Hz)

### Data Format
- CSV columns: TimeStamp, RAW_TP9, RAW_AF7, RAW_AF8, RAW_TP10, AUX channels, Marker
- Channels: TP9 (left ear), AF7 (left forehead), AF8 (right forehead), TP10 (right ear)
- Markers: `/Marker/1` starts recording, `/Marker/2` stops

### Dependencies
- `python-osc`: OSC protocol handling
- `numpy`: Numerical computations
- `scipy`: Signal processing (FFT)
- `pandas`: Data manipulation

## Consciousness Monitor Package

```
consciousness_monitor/
├── main.py              # Main orchestrator
├── config/              # Rules, thresholds, settings
├── data/                # Parsing, processing, models
├── detection/           # Pattern detection, artifacts
├── ui/                  # Display, commands
└── utils/               # Math helpers, validation
```

### Therapeutic Patterns Detected
- **JHANA/TRANSCENDENT** - Deep meditative absorption (80%+ alpha, <15% beta)
- **YOUNG PART CONNECTED** - Vulnerable state (35%+ delta, 30-40% alpha)
- **HOPEFUL PART ACTIVE** - Optimistic consciousness
- **SECURITY GUARD ACTIVE** - Threat detection
- **STARTLED** - Healthy startle response

### Standard Patterns
- RELAXED, FOCUSED, CREATIVE/FLOW, MEDITATIVE, DROWSY, PEAK FOCUS, ALERT/TENSE

## Troubleshooting

### OSC Receiver Not Receiving Data

Use Docker (recommended) - it handles port forwarding automatically:

```bash
docker compose -f docker/docker-compose.osc.yml up -d
docker compose -f docker/docker-compose.osc.yml logs -f
```

For WSL without Docker, see manual port forwarding instructions in docs/.

## Database Integration (TimescaleDB)

```bash
# Start database
docker compose -f docker/compose.yml up -d db

# Run monitor with DB logging
SESSION_ID=$(uuidgen)
DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" \
  uv run python scripts/consciousness_monitor_db_v2.py \
  --db-only --session-id $SESSION_ID --konrad-mode --csv OSC-Python-Recording.csv

# Check windows written
docker compose -f docker/compose.yml exec db \
  psql -U eeg -d eeg -c "SELECT COUNT(*) FROM eeg_window WHERE session_id = '$SESSION_ID';"
```

## EEG MCP Server (Claude Desktop Integration)

The MCP server exposes real-time EEG state to Claude Desktop, enabling attention-aware responses.

**Architecture:** `Muse → Mind Monitor → OSC → Python Monitor → TimescaleDB → MCP Server → Claude Desktop`

**Files:**
- `scripts/eeg_mcp_server.py` - FastMCP server with tools
- `scripts/mcp-eeg-server` - WSL wrapper for Claude Desktop

**MCP Tools:**
- `get_current_eeg_state()` - Current state, band powers, interpretation, recommendations
- `get_eeg_history(minutes)` - State transitions over time
- `get_session_summary()` - All recording sessions

**Claude Desktop Config** (`C:/Users/konra/AppData/Roaming/Claude/claude_desktop_config.json`):
```json
"eeg-consciousness": {
  "command": "wsl",
  "args": ["-d", "Debian", "--exec", "/mnt/c/projects/MindMonitorPython/scripts/mcp-eeg-server"]
}
```

**Testing:**
```bash
DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" \
  uv run python scripts/eeg_mcp_server.py --test
```

## Data Format Detection

| Format | Detection | Processing Mode | Columns |
|--------|-----------|-----------------|---------|
| `mind_monitor` | `timestamp_utc` header | precomputed | `alpha_rel`, `beta_rel`, etc. |
| `muse_player` | `/muse/eeg` messages | raw FFT | Comma-separated values |
| `osc_receiver` | `TimeStamp` + `RAW_` columns | raw FFT | `RAW_TP9`, `RAW_AF7`, etc. |

**Debugging tip:** If all bands show equal % (20% each), check if format detection matches processing mode. OSC receiver format requires raw mode (auto-detected).
