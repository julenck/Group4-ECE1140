#!/usr/bin/env python3
"""
Check PC firewall and server status.
Run this on the PC to diagnose why Raspberry Pi can't connect.
"""

import os
import sys
import socket
import subprocess
import requests
import time

def check_server_running():
    """Check if Python server is running."""
    print("🔍 Checking if server is running...")

    try:
        # Check if port 5000 is open
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        result = sock.connect_ex(('127.0.0.1', 5000))
        sock.close()

        if result == 0:
            print("✅ Port 5000 is open (server running)")

            # Test HTTP
            try:
                response = requests.get("http://127.0.0.1:5000/api/health", timeout=5.0)
                if response.status_code == 200:
                    print("✅ HTTP server responding correctly")
                    return True
                else:
                    print(f"❌ HTTP server error: {response.status_code}")
            except Exception as e:
                print(f"❌ HTTP test failed: {e}")

        else:
            print("❌ Port 5000 is closed (server not running)")
            print("   → Start server with: python train_controller/api/train_api_server.py")

    except Exception as e:
        print(f"❌ Port check failed: {e}")

    return False

def check_firewall_rules():
    """Check Windows Firewall rules."""
    print("\n🔥 Checking Windows Firewall...")

    try:
        # Check if firewall is enabled
        result = subprocess.run(['netsh', 'advfirewall', 'show', 'currentprofile'],
                              capture_output=True, text=True, timeout=10)

        if "ON" in result.stdout.upper():
            print("✅ Firewall is enabled")
        else:
            print("⚠️  Firewall is disabled")

        # Look for Python rules
        result = subprocess.run(['netsh', 'advfirewall', 'firewall', 'show', 'rule', 'name=all'],
                              capture_output=True, text=True, timeout=15)

        python_rules = []
        in_rules = False

        for line in result.stdout.split('\n'):
            if line.strip() == "Inbound Rules:":
                in_rules = True
                continue
            elif line.strip() == "Outbound Rules:":
                in_rules = False
                continue

            if in_rules and ('python' in line.lower() or 'py' in line.lower()):
                python_rules.append(line.strip())

        if python_rules:
            print("✅ Found Python-related firewall rules:")
            for rule in python_rules[:5]:  # Show first 5
                print(f"   • {rule}")
        else:
            print("❌ No Python firewall rules found!")
            print("   → This might be blocking the Raspberry Pi connection")

    except Exception as e:
        print(f"❌ Firewall check failed: {e}")
        print("   → Run Command Prompt as Administrator and try:")
        print("   → netsh advfirewall firewall add rule name=\"Python Server\" dir=in action=allow protocol=TCP localport=5000")

def test_external_connection():
    """Test if server is accessible from external IPs."""
    print("\n🌐 Testing external connectivity...")

    # Get local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to Google DNS
        local_ip = s.getsockname()[0]
        s.close()

        print(f"📍 Local IP: {local_ip}")

        # Test from local IP
        try:
            response = requests.get(f"http://{local_ip}:5000/api/health", timeout=5.0)
            if response.status_code == 200:
                print(f"✅ Server accessible from {local_ip}")
                return local_ip
            else:
                print(f"❌ Server not accessible from {local_ip}: {response.status_code}")
        except Exception as e:
            print(f"❌ Local access failed: {e}")

    except Exception as e:
        print(f"❌ Could not determine local IP: {e}")

    return None

def provide_troubleshooting():
    """Provide troubleshooting steps."""
    print("\n" + "=" * 60)
    print("🔧 FIREWALL & SERVER TROUBLESHOOTING")
    print("=" * 60)

    print("\n1. 🚪 FIX WINDOWS FIREWALL:")
    print("   • Open Windows Defender Firewall")
    print("   • Go to 'Inbound Rules' → 'New Rule'")
    print("   • Select 'Port' → TCP → Specific local ports: 5000")
    print("   • Allow the connection")
    print("   • Name: 'Python Train Server'")
    print("")

    print("2. 🐍 ADD PYTHON EXCEPTION:")
    print("   • In Firewall → 'Allow an app through firewall'")
    print("   • Find python.exe (may need to browse)")
    print("   • Allow on Private and Public networks")
    print("")

    print("3. 🔄 ALTERNATIVE: Temporarily disable firewall:")
    print("   • Open Windows Defender Firewall")
    print("   • Turn off firewall for Private and Public networks")
    print("   • Test connection, then re-enable")
    print("")

    print("4. 🌐 CHECK NETWORK SETTINGS:")
    print("   • Ensure PC and Raspberry Pi are on same WiFi network")
    print("   • Check if router has 'Client Isolation' enabled")
    print("   • Try connecting Raspberry Pi via Ethernet")
    print("")

    print("5. 📍 VERIFY IP ADDRESS:")
    print("   • On PC: ipconfig (find IPv4 Address)")
    print("   • On Raspberry Pi: hostname -I")
    print("   • Make sure IPs are in same subnet (first 3 numbers match)")
    print("")

    print("6. 🔧 RUN POWERSHELL AS ADMIN:")
    print("   New-NetFirewallRule -DisplayName 'Python Server' -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow")

def main():
    print("🖥️  PC FIREWALL & SERVER DIAGNOSTIC")
    print("=" * 50)

    # Check server
    server_ok = check_server_running()
    if not server_ok:
        print("\n❌ Server is not running properly!")
        print("Start it with: python train_controller/api/train_api_server.py")
        return

    # Check firewall
    check_firewall_rules()

    # Test external access
    local_ip = test_external_connection()

    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)

    if local_ip:
        print(f"✅ Server running and accessible from {local_ip}")
        print(f"💡 Tell Raspberry Pi to use: export SERVER_URL=http://{local_ip}:5000")
    else:
        print("❌ Server not accessible from network")
        print("🔥 Firewall is likely blocking connections")

    provide_troubleshooting()

if __name__ == "__main__":
    main()
