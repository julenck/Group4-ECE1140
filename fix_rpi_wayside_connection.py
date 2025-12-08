#!/usr/bin/env python3
"""
Fix script for Raspberry Pi wayside connection issues.
Run this on the Raspberry Pi if the wayside can't update CTC.
"""

import os
import sys
import subprocess
import time

def check_server_reachability(server_url):
    """Check if Raspberry Pi can reach the PC server."""
    print("🔍 Checking server reachability...")

    try:
        # Extract hostname from URL
        hostname = server_url.replace('http://', '').replace('https://', '').split(':')[0]

        # Try to ping
        result = subprocess.run(['ping', '-c', '1', '-W', '2', hostname],
                              capture_output=True, text=True, timeout=5)

        if result.returncode == 0:
            print(f"✅ Can ping {hostname}")
            return True
        else:
            print(f"❌ Cannot ping {hostname}")
            print(f"   Ping output: {result.stdout}")
            return False

    except Exception as e:
        print(f"❌ Ping test failed: {e}")
        return False

def test_server_endpoints(server_url):
    """Test if server endpoints are accessible."""
    print("🌐 Testing server endpoints...")

    import requests

    endpoints = [
        f"{server_url}/api/health",
        f"{server_url}/api/wayside/ctc_commands"
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=5.0)
            if response.status_code == 200:
                print(f"✅ {endpoint}: OK")
            else:
                print(f"❌ {endpoint}: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ {endpoint}: {e}")
            return False

    return True

def test_wayside_api(server_url):
    """Test the wayside API client."""
    print("🚂 Testing wayside API client...")

    try:
        # Add API path
        api_path = os.path.join(os.path.dirname(__file__), 'track_controller', 'api')
        if api_path not in sys.path:
            sys.path.insert(0, api_path)

        from wayside_api_client import WaysideAPIClient

        client = WaysideAPIClient(wayside_id=2, server_url=server_url, timeout=10.0)

        # Try to update train status
        success = client.update_train_status("Train 1", position=50, state="test", active=1)

        if success:
            print("✅ Wayside API client working!")
            return True
        else:
            print("❌ Wayside API client failed")
            return False

    except Exception as e:
        print(f"❌ Wayside API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🔧 RASPBERRY PI WAYSIDE CONNECTION FIX")
    print("=" * 50)

    # Check SERVER_URL
    server_url = os.environ.get('SERVER_URL')
    if not server_url:
        print("❌ SERVER_URL not set!")
        print("\nSet it with:")
        print("export SERVER_URL=http://YOUR_PC_IP:5000")
        print("# Replace YOUR_PC_IP with your PC's actual IP")
        return

    print(f"🎯 Target server: {server_url}")

    # Run diagnostics
    ping_ok = check_server_reachability(server_url)
    if not ping_ok:
        print("\n❌ Cannot reach PC. Check network connection.")
        return

    server_ok = test_server_endpoints(server_url)
    if not server_ok:
        print("\n❌ Server not responding. Check if PC server is running.")
        return

    api_ok = test_wayside_api(server_url)
    if not api_ok:
        print("\n❌ Wayside API failing. Check server logs on PC.")
        return

    print("\n" + "=" * 50)
    print("✅ ALL CONNECTION TESTS PASSED!")
    print("=" * 50)

    print("\n🎉 The Raspberry Pi can successfully communicate with the PC server.")
    print("🚀 The wayside should now be able to update CTC with train positions.")

    print("\n📋 Next steps:")
    print("1. Stop any running wayside on Raspberry Pi")
    print("2. Run: python launch_hw_wayside_only.py")
    print("3. Check PC server logs for wayside API calls")
    print("4. Verify ctc_track_controller.json updates with train positions")

if __name__ == "__main__":
    main()
