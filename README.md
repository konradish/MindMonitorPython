# Mind Monitor Python OSC Samples
Mind Monitor OSC Streaming Python Samples

These code samples are to demonstrate streaming live OSC brainwave data from Mind Monitor (connected to a Muse device), to a computer, which can then process and work with the brainwave data.

## Usage

### Setup
```bash
# Install dependencies
uv sync
```

### Components

## [OSC Receiver.py](OSC%20Receiver.py)
* Records RAW EEG to a CSV file.
* Marker #1 starts recording. Marker #2 stops recording.
```bash
uv run python "OSC Receiver.py"
```

## [consciousness_monitor.py](consciousness_monitor.py)
* Advanced real-time consciousness analysis with clinical-grade signal processing
* Detects mental states: RELAXED, FOCUSED, CREATIVE/FLOW, MEDITATIVE, etc.
```bash
# Basic monitoring
uv run python consciousness_monitor.py

# Custom parameters (example: 5 second window, 5 second updates, no insights)
uv run python consciousness_monitor.py --window 5 --update 5 --no-insights

# Analyze recorded session
uv run python consciousness_monitor.py --analyze --file "recording.csv"
```

## [realtime_consciousness_analyzer.py](realtime_consciousness_analyzer.py)
* Basic real-time consciousness monitoring
```bash
uv run python realtime_consciousness_analyzer.py
```

## [OSC Receiver Audio Feedback.py](OSC%20Receiver%20Audio%20Feedback.py)
![alt image](RelativeGraph.jpg)
* Calculates and graphs the relative waves.
* Plays a sound file if Alpha relative reaches a pre-set threshold.
* Displays if the headband is correctly fitted in the console.

## [OSC Receiver Simple.py](OSC%20Receiver%20Simple.py)
* Displays RAW EEG.