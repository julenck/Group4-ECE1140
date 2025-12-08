#!/usr/bin/env python3
"""
Comprehensive network connectivity diagnostic for Raspberry Pi.
Run this on the problematic Raspberry Pi to identify why it can't reach the PC server.
"""

import os
import sys
import subprocess
import socket
import requests
import time
import json

def get_network_info():
    """Get detailed network information."""
    print("🌐 NETWORK INFORMATION")
    print("=" * 50)

    try:
        # Get hostname
        hostname = socket.gethostname()
        print(f"Hostname: {hostname}")

        # Get IP addresses
        print("\n📡 IP Addresses:")
        try:
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=5)
            ips = result.stdout.strip().split()
            for i, ip in enumerate(ips):
                print(f"  IP {i+1}: {ip}")
        except Exception as e:
            print(f"  Error getting IPs: {e}")

        # Get default gateway
        try:
            result = subprocess.run(['ip', 'route', 'show', 'default'], capture_output=True, text=True, timeout=5)
            gateway = result.stdout.strip().split()[2] if result.stdout.strip() else "Not found"
            print(f"Gateway: {gateway}")
        except Exception as e:
            print(f"Gateway: Error - {e}")

        # Get DNS servers
        try:
            with open('/etc/resolv.conf', 'r') as f:
                for line in f:
                    if line.startswith('nameserver'):
                        print(f"DNS: {line.split()[1]}")
        except Exception as e:
            print(f"DNS: Error - {e}")

    except Exception as e:
        print(f"Error getting network info: {e}")

def test_ping(target_ip):
    """Test ping to target IP."""
    print(f"\n📡 TESTING PING TO {target_ip}")
    print("-" * 40)

    try:
        # Try different ping options
        ping_commands = [
            ['ping', '-c', '3', '-W', '1', target_ip],  # 1 second timeout
            ['ping', '-c', '1', '-W', '5', target_ip],  # 5 second timeout
        ]

        for cmd in ping_commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                print(f"Command: {' '.join(cmd)}")
                print(f"Return code: {result.returncode}")

                if result.returncode == 0:
                    print("✅ PING SUCCESSFUL!")
                    # Parse ping output for timing
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'time=' in line:
                            print(f"   Timing: {line.strip()}")
                            break
                    return True
                else:
                    print("❌ PING FAILED")
                    print(f"   stdout: {result.stdout}")
                    print(f"   stderr: {result.stderr}")

            except subprocess.TimeoutExpired:
                print("⏰ PING TIMEOUT")
            except Exception as e:
                print(f"❌ PING ERROR: {e}")

        return False

    except Exception as e:
        print(f"❌ Ping test failed: {e}")
        return False

def test_tcp_connection(target_ip, port):
    """Test TCP connection to specific port."""
    print(f"\n🔌 TESTING TCP CONNECTION TO {target_ip}:{port}")
    print("-" * 50)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)

        start_time = time.time()
        result = sock.connect_ex((target_ip, port))
        end_time = time.time()

        if result == 0:
            print(f"✅ TCP CONNECTION SUCCESSFUL! (took {(end_time-start_time)*1000:.1f}ms)")
            return True
        else:
            print(f"❌ TCP CONNECTION FAILED (error code: {result})")
            return False

    except Exception as e:
        print(f"❌ TCP test failed: {e}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass

def test_http_connection(server_url):
    """Test HTTP connection to server."""
    print(f"\n🌐 TESTING HTTP CONNECTION TO {server_url}")
    print("-" * 50)

    try:
        # Test with different timeouts
        for timeout in [2.0, 5.0, 10.0]:
            try:
                print(f"Trying with {timeout}s timeout...")
                response = requests.get(server_url, timeout=timeout)

                if response.status_code == 200:
                    print(f"✅ HTTP SUCCESS! Status: {response.status_code}")
                    print(f"   Response: {response.text[:100]}...")
                    return True
                else:
                    print(f"⚠️  HTTP responded with status {response.status_code}")
                    return False

            except requests.exceptions.Timeout:
                print(f"⏰ Timeout after {timeout}s")
                continue
            except requests.exceptions.ConnectionError as e:
                print(f"🔌 Connection error: {e}")
                break
            except Exception as e:
                print(f"❌ HTTP error: {e}")
                break

        return False

    except Exception as e:
        print(f"❌ HTTP test failed: {e}")
        return False

def compare_with_working_pi():
    """Compare network settings with the working Raspberry Pi."""
    print("
🔄 COMPARING WITH WORKING RASPBERRY PI"    print("-" * 50)
    print("Since the other Raspberry Pi works, let's compare:")
    print("")
    print("1. 📍 Check if both Pis are on the same network:")
    print("   - Run 'hostname -I' on both Pis")
    print("   - Check if IPs are in same subnet (first 3 numbers same)")
    print("")
    print("2. 🔍 Check WiFi connection:")
    print("   - Run 'iwconfig' on both Pis")
    print("   - Verify connected to same SSID")
    print("")
    print("3. 🚪 Check if PC firewall is blocking this Pi:")
    print("   - On PC: Check Windows Firewall rules")
    print("   - Try temporarily disabling firewall")
    print("")
    print("4. 🌐 Check if router has client isolation:")
    print("   - Some routers prevent device-to-device communication")
    print("   - Check router admin panel for 'AP Isolation' or 'Client Isolation'")
    print("")
    print("5. 🔄 Try different PC IP or network:")
    print("   - Maybe this Pi is on a different VLAN")
    print("   - Try connecting both Pis to Ethernet instead of WiFi")

def main():
    print("🔧 RASPBERRY PI NETWORK CONNECTIVITY DIAGNOSTIC")
    print("=" * 60)

    # Get server URL
    server_url = os.environ.get('SERVER_URL')
    if not server_url:
        print("❌ SERVER_URL environment variable not set!")
        print("\nSet it with:")
        print("export SERVER_URL=http://YOUR_PC_IP:5000")
        return

    # Extract IP and port
    try:
        if server_url.startswith('http://'):
            url_parts = server_url[7:].split(':')
            target_ip = url_parts[0]
            port = int(url_parts[1]) if len(url_parts) > 1 else 80
        else:
            print("❌ Invalid SERVER_URL format. Should be http://IP:PORT")
            return
    except Exception as e:
        print(f"❌ Error parsing SERVER_URL: {e}")
        return

    print(f"🎯 Target: {server_url}")
    print(f"📍 IP: {target_ip}, Port: {port}")

    # Get network info
    get_network_info()

    # Test connectivity
    ping_ok = test_ping(target_ip)
    tcp_ok = test_tcp_connection(target_ip, port) if ping_ok else False
    http_ok = test_http_connection(server_url) if tcp_ok else False

    # Summary
    print("\n" + "=" * 60)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)

    print(f"Ping to {target_ip}: {'✅ PASS' if ping_ok else '❌ FAIL'}")
    print(f"TCP to {target_ip}:{port}: {'✅ PASS' if tcp_ok else '❌ FAIL'}")
    print(f"HTTP to {server_url}: {'✅ PASS' if http_ok else '❌ FAIL'}")

    if http_ok:
        print("\n🎉 ALL TESTS PASSED! Network connectivity is working.")
        print("   The wayside should be able to communicate with the PC server.")
    else:
        print("\n❌ NETWORK CONNECTIVITY ISSUES DETECTED")
        print("   The Raspberry Pi cannot reach the PC server.")
        print("   Since the other Raspberry Pi works, this is device-specific.")

        compare_with_working_pi()

    print("
💡 QUICK FIXES TO TRY:"    print("1. export SERVER_URL=http://YOUR_PC_IP:5000  # Double-check IP")
    print("2. On PC: Disable Windows Firewall temporarily")
    print("3. Check router for client isolation/AP isolation")
    print("4. Try connecting this Pi to Ethernet instead of WiFi")
    print("5. Restart both devices and router")

if __name__ == "__main__":
    main()
