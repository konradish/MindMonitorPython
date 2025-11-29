"""
UDP Forwarder: Windows -> WSL
Run this on Windows to forward Mind Monitor OSC packets to WSL.

Usage (from PowerShell/cmd):
  python udp_forward_to_wsl.py

This forwards UDP packets from 0.0.0.0:5000 to WSL's IP on port 5000.
"""
import socket
import subprocess
import sys

def get_wsl_ip():
    """Get the WSL2 VM's IP address."""
    try:
        result = subprocess.run(
            ['wsl', '-e', 'ip', 'addr', 'show', 'eth0'],
            capture_output=True, text=True
        )
        for line in result.stdout.split('\n'):
            if 'inet ' in line:
                # Extract IP from "inet 172.x.x.x/20 ..."
                return line.strip().split()[1].split('/')[0]
    except Exception as e:
        print(f"Error getting WSL IP: {e}")
    return None

def main():
    wsl_ip = get_wsl_ip()
    if not wsl_ip:
        print("Could not determine WSL IP address")
        sys.exit(1)

    listen_port = 5000
    forward_port = 5000

    print(f"UDP Forwarder: 0.0.0.0:{listen_port} -> {wsl_ip}:{forward_port}")
    print(f"Configure Mind Monitor to send to your Windows IP on port {listen_port}")
    print("Press Ctrl+C to stop\n")

    # Create sockets
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_sock.bind(('0.0.0.0', listen_port))

    forward_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    packet_count = 0
    try:
        while True:
            data, addr = listen_sock.recvfrom(4096)
            forward_sock.sendto(data, (wsl_ip, forward_port))
            packet_count += 1
            if packet_count % 256 == 0:  # Print every 256 packets (about 1 second of EEG)
                print(f"Forwarded {packet_count} packets...")
    except KeyboardInterrupt:
        print(f"\nStopped. Total packets forwarded: {packet_count}")
    finally:
        listen_sock.close()
        forward_sock.close()

if __name__ == "__main__":
    main()
