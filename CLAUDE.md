# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python project for processing and analyzing real-time EEG (brainwave) data from Mind Monitor via OSC (Open Sound Control). The system receives live EEG streaming from a Muse headband through the Mind Monitor mobile app and provides consciousness/mental state analysis.

## Core Architecture

The project consists of four main components:

1. **OSC Data Reception** (`OSC Receiver.py`) - Receives live EEG data via OSC protocol on UDP port 5000 and records to CSV
2. **Real-time Analysis** (`realtime_consciousness_analyzer.py`) - Basic consciousness state monitoring from CSV data
3. **Enhanced Consciousness Monitor** (`consciousness_monitor/`) - **Modular architecture** with professional-grade signal processing, clinical EEG band analysis and therapeutic pattern detection

### New Modular Architecture (consciousness_monitor/)

The consciousness monitor has been refactored into a clean, maintainable modular system:

```
consciousness_monitor/
├── __init__.py & __main__.py         # Package entry points
├── main.py                           # Main orchestrator (540 lines)
├── config/                           # Configuration management
│   ├── detection_rules.json         # External rule definitions
│   ├── sub_states.json              # Hierarchical sub-states
│   ├── artifact_thresholds.json     # Artifact filtering
│   ├── konrad_personalized.json     # Legacy compatibility
│   └── *.py files                   # Rule/threshold managers
├── data/                            # Data processing & parsing
│   ├── parsers.py                   # EEG data format detection & parsing
│   ├── processors.py               # Signal processing (FFT, band powers)
│   └── models.py                    # Data structures (BandPower, AnalysisResult)
├── detection/                       # Pattern detection & analysis
│   ├── engine.py                    # Core detection engine
│   ├── patterns.py                  # Therapeutic pattern analysis
│   ├── artifacts.py                 # Artifact filtering
│   └── sub_states.py               # Hierarchical state detection
├── ui/                             # Display & user interface
│   ├── display.py                   # Console output formatting
│   └── commands.py                  # Interactive command handling
└── utils/                          # Mathematical helpers & validation
    ├── math_helpers.py              # Signal math, dB conversion
    └── validation.py                # Data validation utilities
```

**Benefits:**
- **18 focused modules** instead of 1 monolithic file (was 2527 lines)
- Each module **<300 lines** with clear responsibility
- **Maintainable** with clean interfaces between components
- **Extensible** architecture for adding new features
- **Backward compatible** - all existing functionality preserved

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

# Advanced consciousness monitoring with signal processing (both commands work)
uv run python consciousness_monitor.py
uv run python -m consciousness_monitor

# Enhanced consciousness monitoring with therapeutic patterns (RECOMMENDED)
uv run python consciousness_monitor.py --konrad-mode
uv run python -m consciousness_monitor --konrad-mode

# Debug mode to see rule evaluation process
uv run python consciousness_monitor.py --debug --konrad-mode

# Tune detection thresholds without code changes
uv run python consciousness_monitor.py --tune-rule jhana.alpha_min=85

# Load custom therapeutic rules
uv run python consciousness_monitor.py --load-rules example_rules.json

# Analyze existing recording with therapeutic patterns
uv run python consciousness_monitor.py --analyze --file "recording.csv" --konrad-mode

# Basic examples with custom parameters
uv run python consciousness_monitor.py --window 0.75 --update 1
uv run python consciousness_monitor.py --analyze --file "recording.csv"
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

### Root Level
- `OSC Receiver*.py` - OSC data reception variants (simple, audio feedback, CSV recording)
- `consciousness_monitor/` - **Modular consciousness monitor package** (RECOMMENDED)
- `realtime_consciousness_analyzer.py` - Basic real-time monitoring
- `test_therapeutic_patterns.py` - Comprehensive test suite for therapeutic patterns
- `example_rules.json` - Example external rules configuration
- `main.py` - Entry point script
- `OSC-Python-Recording.csv` - Default output file for recorded EEG data

### Consciousness Monitor Package Structure
```
consciousness_monitor/
├── __init__.py                      # Package initialization
├── __main__.py                      # CLI entry point (python -m consciousness_monitor)
├── main.py                          # Main orchestrator class
├── config/
│   ├── __init__.py                  # Config package
│   ├── rules.py                     # Rule management
│   ├── thresholds.py               # Threshold management
│   ├── settings.py                 # Settings management
│   ├── detection_rules.json        # Therapeutic pattern rules
│   ├── sub_states.json             # Sub-state definitions
│   ├── artifact_thresholds.json    # Artifact detection thresholds
│   └── konrad_personalized.json    # Personalized settings
├── data/
│   ├── __init__.py                  # Data package
│   ├── models.py                    # Data structures (BandPower, AnalysisResult)
│   ├── parsers.py                   # EEG data parsing & format detection
│   └── processors.py               # Signal processing (FFT, filtering)
├── detection/
│   ├── __init__.py                  # Detection package
│   ├── engine.py                    # Core detection engine
│   ├── patterns.py                  # Therapeutic pattern analysis
│   ├── artifacts.py                 # Artifact filtering
│   └── sub_states.py               # Sub-state detection
├── ui/
│   ├── __init__.py                  # UI package
│   ├── display.py                   # Console display formatting
│   └── commands.py                  # Interactive commands
└── utils/
    ├── __init__.py                  # Utils package
    ├── math_helpers.py              # Mathematical utilities
    └── validation.py                # Data validation
```

## Mental State Analysis

### Enhanced Consciousness Monitor (consciousness_monitor/ package)

The consciousness monitor uses validated EEG band power ratios with **maintainable configuration-driven detection** to identify:

#### **Core Therapeutic Patterns:**
- **JHANA/TRANSCENDENT** (80%+ alpha, <15% beta) - Deep meditative absorption states
- **YOUNG PART CONNECTED** (35%+ delta, 30-40% alpha, 15%+ theta) - Vulnerable, childlike state
- **HOPEFUL PART ACTIVE** (75-80% alpha, <15% beta, <20% delta) - Optimistic consciousness  
- **CAUTIOUS PART ACTIVE** (50-70% alpha, 15%+ delta, 15%+ beta) - Protective awareness
- **STARTLED** (40-55% beta with +2dB spike, 35-55% alpha) - Healthy startle response
- **SECURITY GUARD ACTIVE** (dB spikes with meditation exemption) - Threat detection system

#### **Standard Patterns:**
- **RELAXED** (40%+ alpha) - Konrad's personalized threshold
- **FOCUSED** (35%+ beta, 25%+ alpha) - Balanced concentration
- **ALERT/TENSE** (35%+ beta, <25% alpha) - High arousal, low regulation
- **CREATIVE/FLOW** (30%+ theta, 20%+ alpha) - Creative engagement
- **MEDITATIVE** (30%+ theta, <20% alpha) - Deep introspection
- **DROWSY** (40%+ delta) - Low arousal state
- **PEAK FOCUS** (25%+ gamma, 20%+ alpha) - Intense concentration

#### **Key Features:**
- **Configuration-driven rules** (easy to modify without coding)
- **dB change detection** for dynamic pattern recognition
- **Priority-based detection** (specialized states before general ones)
- **Meditation exemption** (prevents false security guard during deep states)
- **Rule versioning** and changelog tracking
- **Debug mode** for rule development and tuning

#### **Therapeutic Applications:**
- **Internal Family Systems** work (parts detection)
- **Meditation practice** monitoring (jhana states)
- **Nervous system regulation** assessment (startle responses)
- **Emotional regulation** tracking (security guard patterns)
- **Therapeutic progress** measurement (healthy vs. dysregulated responses)


## Modular Architecture

### Package-Based Organization

The consciousness monitor is now organized as a Python package with clear separation of concerns:

- **`main.py`** - Core orchestration and analysis workflow
- **`config/`** - All configuration management (rules, thresholds, settings)
- **`data/`** - Data structures, parsing, and signal processing  
- **`detection/`** - Pattern detection, artifacts, and state analysis
- **`ui/`** - Display formatting and interactive commands
- **`utils/`** - Mathematical helpers and validation utilities

### Development Benefits

- **Focused Modules**: Each file has a single, clear responsibility
- **Easy Testing**: Individual components can be tested in isolation
- **Clean Imports**: Clear dependency structure between modules
- **Extensibility**: New features can be added without touching core logic
- **Maintainability**: Bug fixes and improvements are isolated to specific modules

### Entry Points

The package supports multiple entry points:
```bash
# Direct script execution (legacy compatibility)
uv run python consciousness_monitor.py --konrad-mode

# Package module execution (recommended)
uv run python -m consciousness_monitor --konrad-mode

# Help and CLI options
uv run python -m consciousness_monitor --help
```

## Maintainable Architecture

### Configuration-Driven Detection Rules

Rules are stored as data, not hardcoded logic, enabling easy modification:

```python
DETECTION_RULES = {
    "jhana": {
        "priority": 2,
        "conditions": {"alpha_min": 80, "beta_max": 15},
        "emoji": "🧘",
        "insights": ["🧘 Deep meditative absorption state"]
    }
}
```

### Command-Line Rule Tuning

Adjust thresholds without code changes:

```bash
# Increase jhana alpha threshold
uv run python consciousness_monitor.py --tune-rule jhana.alpha_min=85

# Lower security guard sensitivity
uv run python consciousness_monitor.py --tune-rule security_guard.alpha_exemption=75

# Multiple tuning options
uv run python consciousness_monitor.py --tune-rule jhana.alpha_min=85 --tune-rule startled.beta_db_change_min=1.5
```

### External Rules Loading

Load experimental or personalized rule sets:

```bash
# Load custom therapeutic rules
uv run python consciousness_monitor.py --load-rules my_therapeutic_rules.json

# Test experimental patterns
uv run python consciousness_monitor.py --load-rules experimental_rules.json
```

### Rule Development and Testing

Debug mode shows rule evaluation process:

```bash
# See which rules are tested and why they pass/fail
uv run python consciousness_monitor.py --debug --konrad-mode

# Test specific patterns
uv run python test_therapeutic_patterns.py
```

### Version Control for Rules

- **Rule Version Tracking**: Each rule set has version numbers and changelogs
- **Backwards Compatibility**: Legacy KONRAD_RULES still supported
- **Change Documentation**: All modifications are logged with timestamps

**Current Version: 2025-07-27-v3**
- v1: Initial therapeutic patterns
- v2: Fixed jhana detection, added meditation exemption
- v3: Added Startled state detection with beta spike + maintained alpha

### Future Extensions

The architecture supports:
- **A/B testing** of new rules
- **Pattern recording** for unknown states  
- **Rule sharing** between users
- **Safe experimental rules** that don't break existing detection
- **Machine learning integration** for adaptive thresholds