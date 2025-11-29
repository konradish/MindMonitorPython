"""
OSC Debug Receiver - Prints raw values for all incoming messages
"""
from pythonosc import dispatcher, osc_server
from collections import defaultdict
import time

# Track message counts and sample values per address
message_counts = defaultdict(int)
last_values = {}
start_time = time.time()

def debug_handler(address: str, *args):
    """Print every OSC message."""
    message_counts[address] += 1
    last_values[address] = args

    # Print every message for first 5 seconds, then summarize every 5 seconds
    elapsed = time.time() - start_time

    if elapsed < 5:
        print(f"{address}: {args}")
    elif int(elapsed) % 5 == 0 and message_counts[address] % 256 == 0:
        # Print summary every 5 seconds
        print(f"\n=== Summary at {elapsed:.0f}s ===")
        for addr in sorted(message_counts.keys()):
            val = last_values.get(addr, ())
            count = message_counts[addr]
            print(f"  {addr}: count={count}, last={val[:4]}{'...' if len(val) > 4 else ''}")

def catch_all(address: str, *args):
    """Catch-all handler that logs everything."""
    debug_handler(address, *args)

if __name__ == "__main__":
    print("OSC Debug Receiver - Listening on UDP 5000")
    print("Will print all messages for first 5 seconds, then summarize...\n")

    disp = dispatcher.Dispatcher()
    disp.set_default_handler(catch_all)

    server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", 5000), disp)
    server.serve_forever()
