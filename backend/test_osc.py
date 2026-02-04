"""
Yamaha TF-Rack RCP (TCP) Test Script

Tests direct TCP communication with TF-Rack using the RCP protocol.
Based on: https://github.com/Dom-TC/Yamaha-TF-Control
"""
import socket
import sys
import time

if len(sys.argv) < 2:
    print("Usage: python test_osc.py <TF_RACK_IP>")
    print("Example: python test_osc.py 192.168.0.170")
    sys.exit(1)

ip = sys.argv[1]
port = 49280

print(f"Testing TCP/RCP connection to TF-Rack at {ip}:{port}")
print("=" * 50)

try:
    # Create TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)

    print(f"Connecting to {ip}:{port}...")
    sock.connect((ip, port))
    print("✓ Connected successfully!")

    # Test 1: Set CH1 fader to -10dB (-1000 in protocol)
    print("\nTest 1: Setting CH1 fader to -10dB...")
    command = "set MIXER:Current/InCh/Fader/Level 0 0 -1000\n"
    sock.sendall(command.encode())
    time.sleep(0.1)

    # Try to receive response
    sock.settimeout(1.0)
    try:
        response = sock.recv(1024).decode().strip()
        print(f"   Response: {response}")
    except socket.timeout:
        print("   (No response received - this is normal)")

    # Test 2: Set CH1 fader to 0dB (0 in protocol)
    print("\nTest 2: Setting CH1 fader to 0dB...")
    command = "set MIXER:Current/InCh/Fader/Level 0 0 0\n"
    sock.sendall(command.encode())
    time.sleep(0.5)

    # Test 3: Recall scene 0 from bank A
    print("\nTest 3: Recalling scene 0 from bank A...")
    command = "ssrecall_ex scene_a 0\n"
    sock.sendall(command.encode())
    time.sleep(0.1)

    try:
        response = sock.recv(1024).decode().strip()
        print(f"   Response: {response}")
    except socket.timeout:
        print("   (No response received)")

    print("\n" + "=" * 50)
    print("Tests complete! Check your TF-Rack:")
    print("  - CH1 fader should have moved")
    print("  - Scene 0/Bank A should have been recalled")
    print("\nIf nothing happened, check:")
    print("  1. TF-Rack network settings")
    print("  2. Firewall on this PC")
    print("  3. Both devices on same subnet")

    sock.close()

except socket.timeout:
    print(f"✗ Connection timed out - TF-Rack not responding at {ip}:{port}")
    print("\nPossible causes:")
    print("  1. Wrong IP address")
    print("  2. TF-Rack not powered on")
    print("  3. Network not connected")
    sys.exit(1)

except ConnectionRefusedError:
    print(f"✗ Connection refused by {ip}:{port}")
    print("\nThe TF-Rack is rejecting connections. Check:")
    print("  1. TF-Rack network settings")
    print("  2. Remote control may need to be enabled")
    sys.exit(1)

except OSError as e:
    print(f"✗ Network error: {e}")
    print("\nCheck your network configuration")
    sys.exit(1)

except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
