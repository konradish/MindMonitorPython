"""
Mind Monitor - EEG OSC Receiver with Database Integration
Original: James Clutterbuck (2022)
Extended: Konrad (2024) - Added real-time database emission

Requires: pip install python-osc numpy scipy psycopg2-binary
"""
import os
import sys
import uuid
import json
from datetime import datetime, timezone
from collections import deque
from pythonosc import dispatcher
from pythonosc import osc_server
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ip = "0.0.0.0"
port = 5000
filePath = 'OSC-Python-Recording.csv'
auxCount = -1
recording = False
session_id = None
AUTO_START_DB = True  # Auto-start database recording on first data (no Marker 1 needed)

# Database integration
DB_ENABLED = bool(os.environ.get('DATABASE_URL'))
db_sink = None
signal_processor = None
detection_engine = None

# Sample buffer for windowed analysis (fallback if precomputed not available)
SAMPLE_RATE = 256  # Muse default
WINDOW_SECONDS = 0.75
WINDOW_SAMPLES = int(SAMPLE_RATE * WINDOW_SECONDS)
sample_buffer = {
    'TP9': deque(maxlen=WINDOW_SAMPLES),
    'AF7': deque(maxlen=WINDOW_SAMPLES),
    'AF8': deque(maxlen=WINDOW_SAMPLES),
    'TP10': deque(maxlen=WINDOW_SAMPLES)
}
last_emit_time = 0
EMIT_INTERVAL = 1.0  # Emit to DB every 1 second

# Mind Monitor pre-computed band powers (preferred - more accurate than our FFT)
# Absolute powers are in log-scale (dB), relative are 0-1 range
precomputed_bands = {
    'delta': None,
    'theta': None,
    'alpha': None,
    'beta': None,
    'gamma': None
}
absolute_bands = {
    'delta': None,
    'theta': None,
    'alpha': None,
    'beta': None,
    'gamma': None
}
use_precomputed = True  # Prefer Mind Monitor's calculations

f = open(filePath, 'w+')


def init_database():
    """Initialize database connection and processing components."""
    global db_sink, signal_processor, detection_engine

    if not DB_ENABLED:
        return False

    try:
        from consciousness_monitor.sinks.timescale_sink import TimescaleSink
        from consciousness_monitor.data.processors import SignalProcessor
        from consciousness_monitor.detection.engine import DetectionEngine
        from consciousness_monitor.config import RuleManager, ArtifactThresholds

        db_sink = TimescaleSink()
        signal_processor = SignalProcessor(SAMPLE_RATE)

        rule_manager = RuleManager()
        artifact_thresholds = ArtifactThresholds()
        detection_engine = DetectionEngine(
            rule_manager=rule_manager,
            artifact_thresholds=artifact_thresholds,
            konrad_mode=True
        )

        print(f"✅ Database integration enabled")
        return True
    except ImportError as e:
        print(f"⚠️ Database components not available: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Database initialization failed: {e}")
        return False


def emit_to_database():
    """Process buffered samples and emit to database."""
    global last_emit_time

    if not db_sink or not session_id:
        return

    now = datetime.now(timezone.utc)

    # Check if enough time has passed
    current_time = now.timestamp()
    if current_time - last_emit_time < EMIT_INTERVAL:
        return

    # Check if we have precomputed bands from Mind Monitor (preferred)
    have_relative = use_precomputed and all(v is not None for v in precomputed_bands.values())
    have_absolute = all(v is not None for v in absolute_bands.values())

    if have_relative:
        # Use Mind Monitor's pre-computed relative powers (already percentages)
        percentages = precomputed_bands.copy()
        source = 'mind_monitor_relative'
    elif have_absolute:
        # Convert absolute (log-scale dB) to relative percentages
        # Absolute values are log10(power), so we exponentiate to get linear power
        linear_powers = {}
        for band, db_val in absolute_bands.items():
            # Convert from dB (log10 scale) to linear power
            linear_powers[band] = 10 ** db_val

        total_power = sum(linear_powers.values())
        if total_power > 0:
            percentages = {band: (p / total_power) * 100 for band, p in linear_powers.items()}
        else:
            percentages = {'delta': 20, 'theta': 20, 'alpha': 20, 'beta': 20, 'gamma': 20}
        source = 'mind_monitor_absolute'
    else:
        # Fallback: compute from raw EEG samples
        if not signal_processor:
            return

        min_samples = WINDOW_SAMPLES // 2
        if len(sample_buffer['TP9']) < min_samples:
            return

        try:
            # Convert buffers to arrays
            channels = {}
            for ch_name, buf in sample_buffer.items():
                if len(buf) >= min_samples:
                    channels[ch_name] = np.array(list(buf))

            if not channels:
                return

            # Calculate band powers
            band_power = signal_processor.calculate_multichannel_average(channels)

            # Calculate percentages
            total_power = band_power.delta + band_power.theta + band_power.alpha + band_power.beta + band_power.gamma
            if total_power > 0:
                percentages = {
                    'delta': (band_power.delta / total_power) * 100,
                    'theta': (band_power.theta / total_power) * 100,
                    'alpha': (band_power.alpha / total_power) * 100,
                    'beta': (band_power.beta / total_power) * 100,
                    'gamma': (band_power.gamma / total_power) * 100
                }
            else:
                percentages = {'delta': 20, 'theta': 20, 'alpha': 20, 'beta': 20, 'gamma': 20}
            source = 'osc_receiver_fft'
        except Exception as e:
            print(f"⚠️ FFT calculation failed: {e}")
            return

    # Detect state based on percentages
    state = "UNKNOWN"
    if detection_engine:
        try:
            # Create a simple BandPower-like object for detection
            from consciousness_monitor.data.models import BandPower
            band_power = BandPower(
                delta=percentages['delta'],
                theta=percentages['theta'],
                alpha=percentages['alpha'],
                beta=percentages['beta'],
                gamma=percentages['gamma']
            )
            result = detection_engine.analyze_bands(band_power, now)
            state = result.state if result else "UNKNOWN"
        except:
            state = "UNKNOWN"

    try:
        # Prepare window data
        window_data = {
            'session_id': str(session_id),
            'ts_start': now,
            'ts_end': now,
            'alpha_rel': percentages['alpha'],
            'beta_rel': percentages['beta'],
            'theta_rel': percentages['theta'],
            'delta_rel': percentages['delta'],
            'gamma_rel': percentages['gamma'],
            'entropy': 0,
            'artifact_flags': {},
            'features': {
                'state': state,
                'percentages': percentages,
                'source': source
            }
        }

        # Emit to database
        db_sink.on_windows([window_data])
        last_emit_time = current_time

    except Exception as e:
        print(f"⚠️ Database emit failed: {e}")


def writeFileHeader():
    global auxCount
    fileString = 'TimeStamp,RAW_TP9,RAW_AF7,RAW_AF8,RAW_TP10,'
    for x in range(0, auxCount):
        fileString += 'AUX' + str(x + 1) + ','
    fileString += 'Marker\n'
    f.write(fileString)


def eeg_handler(address: str, *args):
    global recording
    global auxCount
    global session_id

    if auxCount == -1:
        auxCount = len(args) - 4
        writeFileHeader()
        print(f"EEG data received! Channels: {len(args)}")

        # Auto-start database session on first data if enabled
        if AUTO_START_DB and DB_ENABLED and not session_id:
            session_id = uuid.uuid4()
            print(f"Auto-started DB session: {session_id}")

    # Buffer samples for database emission (always, even when not recording to CSV)
    if len(args) >= 4 and session_id:
        try:
            sample_buffer['TP9'].append(float(args[0]))
            sample_buffer['AF7'].append(float(args[1]))
            sample_buffer['AF8'].append(float(args[2]))
            sample_buffer['TP10'].append(float(args[3]))

            # Try to emit to database
            emit_to_database()
        except (ValueError, IndexError):
            pass

    if recording:
        timestampStr = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        fileString = timestampStr
        for arg in args:
            fileString += "," + str(arg)
        fileString += "\n"
        f.write(fileString)
    elif auxCount > -1:  # Only print after first data received
        print("EEG data flowing (not recording - send Marker 1 to start)")


def marker_handler(address: str, i):
    global recording
    global auxCount
    global session_id

    timestampStr = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    markerNum = address[-1]

    if recording:
        fileString = timestampStr + ',,,,,'
        for x in range(0, auxCount):
            fileString += ','
        fileString += '/Marker/' + markerNum + "\n"
        f.write(fileString)

    if markerNum == "1":
        recording = True
        # Create new session for database
        session_id = uuid.uuid4()
        # Clear sample buffers for fresh session
        for buf in sample_buffer.values():
            buf.clear()
        print(f"Recording Started. Session: {session_id}")

    if markerNum == "2":
        f.close()
        recording = False
        print(f"Recording Stopped. Session: {session_id}")
        session_id = None
        server.shutdown()


def relative_band_handler(address: str, *args):
    """Handle Mind Monitor's pre-computed relative band powers."""
    global precomputed_bands

    if not args:
        return

    # Extract band name from address: /muse/elements/delta_relative -> delta
    band = address.split('/')[-1].replace('_relative', '')

    if band in precomputed_bands:
        # Mind Monitor sends 4 values (one per electrode), average them
        # Values are 0-1 range (relative power)
        avg_power = np.mean([float(v) for v in args if v is not None])
        precomputed_bands[band] = avg_power * 100  # Convert to percentage


def absolute_band_handler(address: str, *args):
    """Handle Mind Monitor's absolute band powers (log-scale dB)."""
    global absolute_bands

    if not args:
        return

    # Extract band name from address: /muse/elements/delta_absolute -> delta
    band = address.split('/')[-1].replace('_absolute', '')

    if band in absolute_bands:
        # Mind Monitor sends 1 value (averaged across electrodes)
        # Value is in log10 scale (dB)
        absolute_bands[band] = float(args[0])


if __name__ == "__main__":
    # Initialize database if available
    if DB_ENABLED:
        init_database()
    else:
        print("ℹ️ Database integration disabled (no DATABASE_URL)")

    dispatcher = dispatcher.Dispatcher()
    dispatcher.map("/muse/eeg", eeg_handler)
    dispatcher.map("/Marker/*", marker_handler)

    # Map Mind Monitor's pre-computed relative band powers (preferred)
    dispatcher.map("/muse/elements/delta_relative", relative_band_handler)
    dispatcher.map("/muse/elements/theta_relative", relative_band_handler)
    dispatcher.map("/muse/elements/alpha_relative", relative_band_handler)
    dispatcher.map("/muse/elements/beta_relative", relative_band_handler)
    dispatcher.map("/muse/elements/gamma_relative", relative_band_handler)

    # Map Mind Monitor's absolute band powers (fallback - always available)
    dispatcher.map("/muse/elements/delta_absolute", absolute_band_handler)
    dispatcher.map("/muse/elements/theta_absolute", absolute_band_handler)
    dispatcher.map("/muse/elements/alpha_absolute", absolute_band_handler)
    dispatcher.map("/muse/elements/beta_absolute", absolute_band_handler)
    dispatcher.map("/muse/elements/gamma_absolute", absolute_band_handler)

    server = osc_server.ThreadingOSCUDPServer((ip, port), dispatcher)
    print(f"Listening on UDP port {port}")
    if DB_ENABLED:
        print("Database emission: ENABLED (will stream to TimescaleDB)")
        print("Band powers: Using Mind Monitor absolute bands (converted to relative %)")
        if AUTO_START_DB:
            print("Auto-start: ON (DB recording begins on first EEG packet)")
        else:
            print("Auto-start: OFF (send Marker 1 to start DB recording)")
    print("CSV recording: Send Marker 1 to start, Marker 2 to stop")
    server.serve_forever()
