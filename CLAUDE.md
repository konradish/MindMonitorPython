# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python project for processing and analyzing real-time EEG (brainwave) data from Mind Monitor via OSC (Open Sound Control). The system receives live EEG streaming from a Muse headband through the Mind Monitor mobile app and provides consciousness/mental state analysis.

## Core Architecture

The project consists of three main components:

1. **OSC Data Reception** (`OSC Receiver.py`) - Receives live EEG data via OSC protocol on UDP port 5000 and records to CSV
2. **Real-time Analysis** (`realtime_consciousness_analyzer.py`) - Basic consciousness state monitoring from CSV data
3. **Advanced Analysis** (`consciousness_monitor.py`) - Professional-grade signal processing with clinical EEG band analysis

### Data Flow
1. Muse headband → Mind Monitor app → OSC UDP packets → Python receiver → CSV file
2. Analysis scripts continuously monitor the CSV file for new data
3. Real-time consciousness state interpretation and visualization

## Development Commands

### Environment Setup

#### Windows (with uv)
```bash
# Install dependencies
uv sync
```

#### Linux/WSL (alternative)
```bash
# Create separate Linux venv if needed
python3 -m venv .venv-linux
source .venv-linux/bin/activate
pip install numpy pandas python-osc scipy
```

### Running Components
```bash
# Start OSC receiver (listens on port 5000)
uv run python "OSC Receiver.py"

# Real-time consciousness monitoring (basic)
uv run python realtime_consciousness_analyzer.py

# Advanced consciousness monitoring with signal processing
uv run python consciousness_monitor.py

# Example with custom parameters (1 second window, 2 second updates, no insights)  
uv run python consciousness_monitor.py --window 1 --update 2 --no-insights

# Optimal Mind Monitor matching settings (0.75s window)
uv run python consciousness_monitor.py --window 0.75 --update 1

# Analyze existing recording file
uv run python consciousness_monitor.py --analyze --file "recording.csv"

# Full parameter options
uv run python consciousness_monitor.py --window 2.0 --update 1.0 --no-bands --no-insights --channels TP9 AF7 AF8 TP10
```

## Key Technical Details

### EEG Signal Processing
- Sample rate: 256 Hz (Muse standard)  
- Mind Monitor outputs microvolts directly (no ADC conversion needed)
- Typical signal range: 200-1200 µV for good EEG
- **Optimal window size: 0.75-1.0 seconds** (matches Mind Monitor app)
- **Minimal preprocessing: DC removal only** (preserves alpha waves)
- **Avoid aggressive filtering** (high-pass/low-pass kills alpha, inflates delta)
- Frequency bands: Delta (0.5-4Hz), Theta (4-8Hz), Alpha (8-13Hz), Beta (13-30Hz), Gamma (30-50Hz)

### Data Format
- CSV columns: TimeStamp, RAW_TP9, RAW_AF7, RAW_AF8, RAW_TP10, AUX channels, Marker
- Channels: TP9 (left ear), AF7 (left forehead), AF8 (right forehead), TP10 (right ear)
- Markers: `/Marker/1` starts recording, `/Marker/2` stops recording

### Dependencies
- `python-osc`: OSC protocol handling
- `numpy`: Numerical computations
- `scipy`: Signal processing (FFT, filtering)
- `pandas`: Data manipulation and CSV handling

## File Structure

- `OSC Receiver*.py` - OSC data reception variants (simple, audio feedback, CSV recording)
- `consciousness_monitor.py` - Advanced analysis with clinical-grade signal processing
- `realtime_consciousness_analyzer.py` - Basic real-time monitoring
- `main.py` - Entry point script
- `OSC-Python-Recording.csv` - Default output file for recorded EEG data

## Mental State Analysis

The consciousness monitoring uses validated EEG band power ratios to detect:
- RELAXED (high alpha)
- FOCUSED (balanced beta/alpha)
- ALERT/TENSE (high beta, low alpha) 
- CREATIVE/FLOW (high theta)
- MEDITATIVE (high theta + alpha)
- DROWSY (high delta)
- PEAK FOCUS (high gamma)

Insights include detection of "security guard" mental patterns and emotional regulation states.