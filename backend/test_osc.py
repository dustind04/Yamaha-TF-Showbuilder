"""Quick OSC test script - run this separately to test TF-Rack communication."""
from pythonosc.udp_client import SimpleUDPClient
import sys

if len(sys.argv) < 2:
    print("Usage: python test_osc.py <TF_RACK_IP>")
    print("Example: python test_osc.py 192.168.0.170")
    sys.exit(1)

ip = sys.argv[1]
port = 49280

print(f"Testing OSC connection to {ip}:{port}")

client = SimpleUDPClient(ip, port)

# Try sending a simple info request
print("Sending /info request...")
client.send_message("/info", [])

# Try setting channel 1 fader to -10dB (0.5 = roughly -10dB in TF scale)
print("Sending fader command to CH1...")
client.send_message("/ch/01/mix/fader", [0.5])

# Try the alternative format without zero padding
print("Trying alternative format...")
client.send_message("/ch/1/mix/fader", [0.5])

print("\nCommands sent. Check your TF-Rack to see if CH1 fader moved.")
print("If nothing happened, the TF-Rack might:")
print("  1. Need OSC remote control enabled in settings")
print("  2. Be on a different network/subnet")
print("  3. Have a firewall blocking UDP port 49280")
