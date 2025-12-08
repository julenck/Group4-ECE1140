#!/usr/bin/env python3
"""
Quick network connectivity fixes for Raspberry Pi.
Try these common solutions when the other Raspberry Pi works but this one doesn't.
"""

import os
import sys
import subprocess
import requests

def test_current_connection(server_url):
    """Test current connection."""
    print("🔍 Testing current connection...")
    try:
        response = requests.get(f"{server_url}/api/health", timeout=5.0)
        if response.status_code == 200:
            print("✅ Current connection works!")
            return True
    except:
        print("❌ Current connection fails")
    return False

def try_alternative_ips(base_ip):
    """Try different IP variations."""
    print("\n🔄 TRYING ALTERNATIVE IPs...")
    print("-" * 40)

    # Extract base IP
    parts = base_ip.split('.')
    if len(parts) != 4:
        return False

    # Try nearby IPs
    alternatives = []

    # Try .1 variation
    if parts[3] != '1':
        alt_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.1"
        alternatives.append(alt_ip)

    # Try adding/subtracting 1 from last octet
    try:
        last_octet = int(parts[3])
        if last_octet > 1:
            alt_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.{last_octet-1}"
            alternatives.append(alt_ip)
        if last_octet < 254:
            alt_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.{last_octet+1}"
            alternatives.append(alt_ip)
    except:
        pass

    success_ip = None
    for alt_ip in alternatives:
        print(f"Testing {alt_ip}...")
        try:
            response = requests.get(f"http://{alt_ip}:5000/api/health", timeout=3.0)
            if response.status_code == 200:
                print(f"✅ SUCCESS with {alt_ip}!")
                success_ip = alt_ip
                break
        except:
            print(f"❌ {alt_ip} failed")

    return success_ip

def check_network_settings():
    """Check and suggest network fixes."""
    print("\n🔧 NETWORK TROUBLESHOOTING")
    print("-" * 40)

    issues = []

    # Check if we're on WiFi
    try:
        result = subprocess.run(['iwconfig'], capture_output=True, text=True, timeout=5)
        if 'ESSID:' in result.stdout:
            print("📶 Connected to WiFi")
            # Check signal strength
            for line in result.stdout.split('\n'):
                if 'Signal level' in line:
                    print(f"   Signal: {line.strip()}")
                    if 'Signal level=-' in line:
                        signal = int(line.split('Signal level=-')[1].split()[0])
                        if signal > 70:
                            issues.append("Weak WiFi signal - try moving closer to router")
        else:
            print("🔌 Connected via Ethernet (good!)")
    except:
        print("⚠️  Could not check WiFi status")

    # Check routing table
    try:
        result = subprocess.run(['ip', 'route'], capture_output=True, text=True, timeout=5)
        default_route = None
        for line in result.stdout.split('\n'):
            if 'default via' in line:
                default_route = line.split()[2]
                print(f"📍 Default gateway: {default_route}")
                break
        if not default_route:
            issues.append("No default gateway - network not configured properly")
    except:
        print("⚠️  Could not check routing")

    # Check DNS
    try:
        with open('/etc/resolv.conf', 'r') as f:
            dns_servers = [line.split()[1] for line in f if line.startswith('nameserver')]
        if dns_servers:
            print(f"🖥️  DNS servers: {', '.join(dns_servers)}")
        else:
            issues.append("No DNS servers configured")
    except:
        print("⚠️  Could not check DNS")

    if issues:
        print("\n⚠️  POTENTIAL ISSUES:")
        for issue in issues:
            print(f"   • {issue}")
    else:
        print("\n✅ Network configuration looks OK")

def main():
    print("🚀 QUICK NETWORK CONNECTIVITY FIX")
    print("=" * 50)

    # Get current SERVER_URL
    server_url = os.environ.get('SERVER_URL')
    if not server_url:
        print("❌ SERVER_URL not set!")
        print("Set it with: export SERVER_URL=http://YOUR_PC_IP:5000")
        return

    print(f"🎯 Current SERVER_URL: {server_url}")

    # Extract IP
    try:
        if server_url.startswith('http://'):
            target_ip = server_url[7:].split(':')[0]
        else:
            print("❌ Invalid SERVER_URL format")
            return
    except:
        print("❌ Could not parse SERVER_URL")
        return

    # Test current connection
    if test_current_connection(server_url):
        print("\n🎉 CONNECTION WORKS! No fixes needed.")
        return

    print("\n🔧 CONNECTION FAILED - TRYING FIXES...")
    print("=" * 50)

    # Try alternative IPs
    working_ip = try_alternative_ips(target_ip)
    if working_ip:
        print(f"\n🎯 SUCCESS! Use this IP instead:")
        print(f"   export SERVER_URL=http://{working_ip}:5000")
        print(f"   python launch_hw_wayside_only.py")
        return

    # Check network settings
    check_network_settings()

    print("\n" + "=" * 50)
    print("🔍 MANUAL TROUBLESHOOTING STEPS")
    print("=" * 50)

    print("1. 📍 Find PC's actual IP address:")
    print("   • On PC: Open command prompt, run 'ipconfig'")
    print("   • Look for 'IPv4 Address' under your active network adapter")
    print("   • Make sure it's the same network as this Raspberry Pi")
    print("")

    print("2. 🔄 Try these commands on this Raspberry Pi:")
    print(f"   • ping {target_ip}")
    print(f"   • curl {server_url}/api/health")
    print("   • If ping works but curl fails: Firewall issue on PC")
    print("   • If ping fails: Network connectivity issue")
    print("")

    print("3. 🚪 Check Windows Firewall on PC:")
    print("   • Open Windows Defender Firewall")
    print("   • Go to 'Inbound Rules'")
    print("   • Look for Python rules, ensure they're enabled")
    print("   • Try temporarily disabling firewall to test")
    print("")

    print("4. 🌐 Check router settings:")
    print("   • Log into router admin panel (usually 192.168.1.1)")
    print("   • Look for 'Client Isolation' or 'AP Isolation' - disable it")
    print("   • Check if both Raspberry Pis have IPs in same subnet")
    print("")

    print("5. 🔌 Try Ethernet connection:")
    print("   • Connect this Raspberry Pi directly to router with Ethernet")
    print("   • Disable WiFi temporarily")
    print("   • Test connection again")

if __name__ == "__main__":
    main()
