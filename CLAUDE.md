# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python project for processing and analyzing real-time EEG (brainwave) data from Mind Monitor via OSC (Open Sound Control). The system receives live EEG streaming from a Muse headband through the Mind Monitor mobile app and provides consciousness/mental state analysis.

## Project Structure

```
MindMonitorPython/
├── consciousness_monitor/     # Main analysis package (modular architecture)
├── admin/                     # Streamlit admin panel
│   ├── app.py                # Main entry point
│   ├── pages/                # Multi-page UI
│   └── utils/                # Database utilities
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
│   ├── Dockerfile.admin      # Admin panel container
│   ├── compose.yml
│   └── Dockerfile
├── tools/                     # Data ingestion tools
├── config/                    # External configuration files
├── assets/                    # Media files (sounds, images)
├── archive/                   # Legacy/backup scripts (gitignored)
├── specs/                     # Boundary specifications (CSV)
└── sql/                       # Database schemas
```

## Development Workflow

### Specs-First Development

Before modifying boundaries, adding features, or changing component interfaces:

1. **Update specs first** - Edit `specs/boundary_specs.csv` to add/modify the component row
2. **Mark as provisional** - Add `[PROVISIONAL]` prefix to the Notes column
3. **Implement the change** - Write the code, tests, and documentation
4. **Verify and finalize** - Remove `[PROVISIONAL]` once implementation is complete and tested

Example workflow for adding a new detection pattern:
```
1. Add row to boundary_specs.csv:
   NewPattern,consciousness_monitor/detection/new.py,class,detection,...,[PROVISIONAL] Adding new pattern

2. Implement the pattern in code

3. Add tests

4. Update Notes column to remove [PROVISIONAL]
```

This ensures architectural decisions are documented before implementation and prevents undocumented boundary changes.

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

For WSL without Docker, see the WSL2 UDP Workaround section below.

## WSL2 UDP Workaround (Real-time Streaming to Database)

WSL2 has a NAT network that doesn't forward UDP packets from the Windows host. This requires a workaround to get Mind Monitor data into WSL.

### Architecture
```
Phone (Mind Monitor) → Windows IP:5000 (UDP) → UDP Forwarder → WSL IP:5000 → OSC Receiver → TimescaleDB
```

### Step 1: Start the Database
```bash
docker compose -f docker/compose.yml up -d db
```

### Step 2: Start the UDP Forwarder on Windows
Open PowerShell (as regular user) and run:
```powershell
cd C:\projects\MindMonitorPython
python scripts/udp_forward_to_wsl.py
```
This listens on Windows UDP 5000 and forwards to WSL.

### Step 3: Start the OSC Receiver in WSL
```bash
DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" uv run python scripts/osc_receiver.py
```

### Step 4: Configure Mind Monitor
- **IP Address:** Your Windows IP (find with `ipconfig` - usually 192.168.x.x)
- **Port:** 5000

Database recording starts automatically on first EEG packet (no Marker 1 needed).

### Band Power Source Hierarchy
The OSC receiver uses band powers in this priority order:
1. **`/muse/elements/*_relative`** (if "Relative Brain Waves" enabled in Mind Monitor)
2. **`/muse/elements/*_absolute`** (always available, converted from log-scale dB to %)
3. **Raw FFT** (fallback, computed from `/muse/eeg` samples)

### Verifying Data Flow
```bash
# Check if receiver is getting data (should show "EEG data received!")
# Check database for new records
docker compose -f docker/compose.yml exec db \
  psql -U eeg -d eeg -c "SELECT COUNT(*), MAX(ts_start) AT TIME ZONE 'America/Chicago' FROM eeg_window;"
```

### Why This Workaround?
- WSL2 uses a virtual network with NAT
- `netsh portproxy` only works for TCP, not UDP
- Mind Monitor sends OSC over UDP
- The Python UDP forwarder bridges Windows → WSL

### Firewall Note
A Windows Firewall rule "Mind Monitor OSC (UDP 5000)" should already exist. If not:
```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "Mind Monitor OSC (UDP 5000)" -Direction Inbound -Protocol UDP -LocalPort 5000 -Action Allow
```

### Quick Restart After Reboot
```bash
# Terminal 1 (PowerShell on Windows):
cd C:\projects\MindMonitorPython && python scripts/udp_forward_to_wsl.py

# Terminal 2 (WSL):
docker compose -f docker/compose.yml up -d db
DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" uv run python scripts/osc_receiver.py

# Database recording starts automatically when EEG data arrives
```

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

## EEG Admin Panel (Streamlit)

A web-based admin panel for viewing brain states, managing labels, and monitoring EEG data.

**Features:**
- **Dashboard** - Real-time brain state visualization with band power charts
- **Sessions** - Browse recording sessions, view statistics, export data
- **Annotations** - Add/view/delete labels on EEG data
- **State Definitions** - Create custom brain state patterns with thresholds
- **Baselines** - Save and compare personal EEG baselines

**Running the Admin Panel:**

```bash
# Direct (recommended for development)
DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" \
  uv run streamlit run admin/app.py --server.headless=true

# Access at http://localhost:8501

# With Docker
docker compose -f docker/compose.yml up -d admin
```

**Files:**
- `admin/app.py` - Main entry point
- `admin/pages/` - Multi-page UI (Dashboard, Sessions, Annotations, etc.)
- `admin/utils/db.py` - Database utilities

## Data Format Detection

| Format | Detection | Processing Mode | Columns |
|--------|-----------|-----------------|---------|
| `mind_monitor` | `timestamp_utc` header | precomputed | `alpha_rel`, `beta_rel`, etc. |
| `muse_player` | `/muse/eeg` messages | raw FFT | Comma-separated values |
| `osc_receiver` | `TimeStamp` + `RAW_` columns | raw FFT | `RAW_TP9`, `RAW_AF7`, etc. |

**Debugging tip:** If all bands show equal % (20% each), check if format detection matches processing mode. OSC receiver format requires raw mode (auto-detected).
