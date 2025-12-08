#!/usr/bin/env python3
"""
Diagnostic script to test Raspberry Pi connection to PC server.
Run this on the Raspberry Pi to diagnose connectivity issues.
"""

import os
import sys
import requests
import time

def test_basic_connectivity(server_url):
    """Test if Raspberry Pi can reach PC server."""
    print("🌐 Testing basic connectivity...")
    print("-" * 50)

    try:
        # Test ping first (if available)
        hostname = server_url.replace('http://', '').replace('https://', '').split(':')[0]
        print(f"📡 Pinging {hostname}...")
        response = os.system(f"ping -c 1 -W 2 {hostname} > /dev/null 2>&1")
        if response == 0:
            print(f"✅ Ping successful to {hostname}")
        else:
            print(f"❌ Ping failed to {hostname}")
            print("   → Check network connection between Raspberry Pi and PC")
            return False

    except Exception as e:
        print(f"⚠️  Ping test failed: {e}")

    return True

def test_server_endpoints(server_url):
    """Test all relevant server endpoints."""
    print("\n🔗 Testing server endpoints...")
    print("-" * 50)

    endpoints = [
        (f"{server_url}/api/health", "Health check"),
        (f"{server_url}/api/wayside/ctc_commands", "CTC commands"),
        (f"{server_url}/api/wayside/train_physics", "Train physics"),
        (f"{server_url}/api/wayside/train_status", "Train status update (POST)")
    ]

    success_count = 0

    for url, description in endpoints:
        try:
            if "train_status" in url:
                # POST request for train status update
                test_data = {
                    "train": "Train 1",
                    "position": 50,
                    "state": "moving",
                    "active": 1
                }
                response = requests.post(url, json=test_data, timeout=5.0)
            else:
                # GET request for other endpoints
                response = requests.get(url, timeout=5.0)

            if response.status_code == 200:
                print(f"✅ {description}: {response.status_code}")
                success_count += 1
            else:
                print(f"❌ {description}: {response.status_code} - {response.text[:100]}")

        except requests.exceptions.Timeout:
            print(f"⏰ {description}: TIMEOUT (5s)")
        except requests.exceptions.ConnectionError:
            print(f"🔌 {description}: CONNECTION FAILED")
            print(f"   → Server not reachable at {server_url}")
            break
        except Exception as e:
            print(f"❌ {description}: ERROR - {e}")

    return success_count == len(endpoints)

def test_wayside_simulation(server_url):
    """Simulate what the wayside does."""
    print("\n🚂 Simulating wayside API calls...")
    print("-" * 50)

    try:
        # Import wayside API client
        sys.path.append(os.path.join(os.path.dirname(__file__), 'track_controller', 'api'))
        from wayside_api_client import WaysideAPIClient

        print("🏗️  Creating Wayside API client...")
        client = WaysideAPIClient(wayside_id=2, server_url=server_url, timeout=5.0)

        print("📤 Testing train status update...")
        success = client.update_train_status("Train 1", position=75, state="moving", active=1)

        if success:
            print("✅ Wayside API client working correctly!")
            return True
        else:
            print("❌ Wayside API client failed")
            return False

    except Exception as e:
        print(f"❌ Failed to test wayside API: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🔧 RASPBERRY PI SERVER CONNECTIVITY DIAGNOSTIC")
    print("=" * 60)

    # Get server URL
    server_url = os.environ.get('SERVER_URL')
    if not server_url:
        print("❌ SERVER_URL environment variable not set!")
        print("\n🔧 Set it with:")
        print("   export SERVER_URL=http://YOUR_PC_IP:5000")
        print("   # Replace YOUR_PC_IP with your PC's IP address")
        return

    print(f"🎯 Target server: {server_url}")
    print(f"📍 Local IP: {os.popen('hostname -I').read().strip()}")

    # Run tests
    connectivity_ok = test_basic_connectivity(server_url)
    if not connectivity_ok:
        print("\n❌ Basic connectivity failed. Cannot proceed.")
        return

    endpoints_ok = test_server_endpoints(server_url)
    if not endpoints_ok:
        print("\n❌ Server endpoint tests failed.")
        return

    wayside_ok = test_wayside_simulation(server_url)

    # Summary
    print("\n" + "=" * 60)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)

    if wayside_ok:
        print("✅ ALL TESTS PASSED!")
        print("🎉 Raspberry Pi can successfully communicate with PC server")
        print("\n🚀 The wayside should now be able to update CTC with train positions")
    else:
        print("❌ SOME TESTS FAILED")
        print("🔍 Check the error messages above for troubleshooting")

    print("\n💡 If issues persist:")
    print("   1. Verify PC server is running: python train_controller/api/train_api_server.py")
    print("   2. Check PC firewall allows connections on port 5000")
    print("   3. Ensure Raspberry Pi and PC are on same network")
    print(f"   4. Test manually: curl {server_url}/api/health")

if __name__ == "__main__":
    main()
