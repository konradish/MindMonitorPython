# /// script
# dependencies = ["python-osc"]
# ///

import csv
from datetime import datetime
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
import threading

# --- Configuration ---
IP_ADDRESS = "0.0.0.0"
PORT = 5000 
CSV_FILENAME = "mind_monitor_data.csv"

# --- Global Data Store with Thread Lock ---
data_lock = threading.Lock()
latest_data = {
    "timestamp_utc": None, "timestamp_local": None,
    "eeg_tp9": None, "eeg_af7": None, "eeg_af8": None, "eeg_tp10": None,
    "accel_x": None, "accel_y": None, "accel_z": None,
    "gyro_x": None, "gyro_y": None, "gyro_z": None,
    "abs_delta": None, "abs_theta": None, "abs_alpha": None, "abs_beta": None, "abs_gamma": None,
    "rel_delta": None, "rel_theta": None, "rel_alpha": None, "rel_beta": None, "rel_gamma": None,
    "touching_forehead": None,
    "horseshoe_tp9": None, "horseshoe_af7": None, "horseshoe_af8": None, "horseshoe_tp10": None,
    "jaw_clench": None,
    "blink": None,
}

# --- CSV File Setup ---
csv_header = latest_data.keys()
try:
    with open(CSV_FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)
except IOError as e:
    print(f"Error creating CSV file: {e}")
    exit()

def write_data_to_csv():
    """Thread-safely writes the current state of 'latest_data' to the CSV file."""
    with data_lock:
        data_to_write = latest_data.copy()
    
    with open(CSV_FILENAME, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_header)
        writer.writerow(data_to_write)

# --- OSC Message Handlers ---

def eeg_handler(address, *args):
    """Handles raw EEG data and triggers the CSV write."""
    with data_lock:
        now = datetime.now()
        latest_data["timestamp_utc"] = now.utcnow().isoformat()
        latest_data["timestamp_local"] = now.isoformat()
        
        if len(args) >= 4:
            latest_data["eeg_tp9"] = args[0]
            latest_data["eeg_af7"] = args[1]
            latest_data["eeg_af8"] = args[2]
            latest_data["eeg_tp10"] = args[3]
            
    write_data_to_csv()

def accelerometer_handler(address, x, y, z):
    with data_lock:
        latest_data["accel_x"] = x
        latest_data["accel_y"] = y
        latest_data["accel_z"] = z

def gyroscope_handler(address, x, y, z):
    with data_lock:
        latest_data["gyro_x"] = x
        latest_data["gyro_y"] = y
        latest_data["gyro_z"] = z
    
# MODIFIED: This handler now correctly expects a single value.
def absolute_band_power_handler(address, value):
    """Handles absolute band power data for a single band."""
    with data_lock:
        band_name = address.split('/')[-1].replace('_absolute', '')
        latest_data[f"abs_{band_name}"] = value

# MODIFIED: This handler also correctly expects a single value.
def relative_band_power_handler(address, value):
    """Handles relative band power data for a single band."""
    with data_lock:
        band_name = address.split('/')[-1].replace('_relative', '')
        latest_data[f"rel_{band_name}"] = value

def horseshoe_handler(address, tp9, af7, af8, tp10):
    with data_lock:
        latest_data["horseshoe_tp9"] = tp9
        latest_data["horseshoe_af7"] = af7
        latest_data["horseshoe_af8"] = af8
        latest_data["horseshoe_tp10"] = tp10

def touching_forehead_handler(address, value):
    with data_lock:
        latest_data["touching_forehead"] = value

def jaw_clench_handler(address, value):
    with data_lock:
        latest_data["jaw_clench"] = value

def blink_handler(address, value):
    with data_lock:
        latest_data["blink"] = value

def main():
    """Sets up the OSC server and starts listening for messages."""
    dispatcher = Dispatcher()
    
    # Map OSC addresses to the corrected handler functions
    dispatcher.map("/muse/eeg", eeg_handler)
    dispatcher.map("/muse/acc", accelerometer_handler)
    dispatcher.map("/muse/gyro", gyroscope_handler)
    
    # Each of these addresses sends a SINGLE value. The handlers are now correct.
    dispatcher.map("/muse/elements/delta_absolute", absolute_band_power_handler)
    dispatcher.map("/muse/elements/theta_absolute", absolute_band_power_handler)
    dispatcher.map("/muse/elements/alpha_absolute", absolute_band_power_handler)
    dispatcher.map("/muse/elements/beta_absolute", absolute_band_power_handler)
    dispatcher.map("/muse/elements/gamma_absolute", absolute_band_power_handler)

    dispatcher.map("/muse/elements/delta_relative", relative_band_power_handler)
    dispatcher.map("/muse/elements/theta_relative", relative_band_power_handler)
    dispatcher.map("/muse/elements/alpha_relative", relative_band_power_handler)
    dispatcher.map("/muse/elements/beta_relative", relative_band_power_handler)
    dispatcher.map("/muse/elements/gamma_relative", relative_band_power_handler)
    
    dispatcher.map("/muse/elements/touching_forehead", touching_forehead_handler)
    dispatcher.map("/muse/elements/horseshoe", horseshoe_handler)
    dispatcher.map("/muse/elements/jaw_clench", jaw_clench_handler)
    dispatcher.map("/muse/elements/blink", blink_handler)

    server = BlockingOSCUDPServer((IP_ADDRESS, PORT), dispatcher)
    print(f"🚀 OSC Server listening on {server.server_address}")
    print(f"✍️  Recording data to {CSV_FILENAME}")
    print("Press Ctrl+C to stop.")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Recording stopped.")
        server.server_close()

if __name__ == "__main__":
    main()