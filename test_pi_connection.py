#!/usr/bin/env python3
"""
Quick diagnostic tool to verify Raspberry Pi can connect to PC REST API server.

Usage:
    On Raspberry Pi:
    python test_pi_connection.py http://YOUR_PC_IP:5000
    
Example:
    python test_pi_connection.py http://10.5.127.125:5000
"""

import sys
import requests
import json
from datetime import datetime

def test_connection(server_url):
    """Test connection to REST API server and verify endpoints."""
    
    print("=" * 70)
    print("  Raspberry Pi → PC REST API Server Connection Test")
    print("=" * 70)
    print(f"\nServer URL: {server_url}")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "=" * 70)
    
    # Test 1: Health check
    print("\n[Test 1/5] Health Check")
    print("-" * 70)
    try:
        resp = requests.get(f"{server_url}/api/health", timeout=5.0)
        if resp.status_code == 200:
            print("✅ PASS: Server is reachable")
            data = resp.json()
            print(f"   Status: {data.get('status')}")
            print(f"   Message: {data.get('message')}")
        else:
            print(f"❌ FAIL: Server responded with status {resp.status_code}")
            return False
    except requests.exceptions.Timeout:
        print("❌ FAIL: Connection timed out (5 seconds)")
        print("   Check: Is server running? Is firewall blocking port 5000?")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ FAIL: Cannot connect to server")
        print(f"   Error: {e}")
        print("   Check: Is PC IP correct? Is server running?")
        return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected error: {e}")
        return False
    
    # Test 2: CTC commands endpoint (wayside reads)
    print("\n[Test 2/5] CTC Commands Endpoint (GET)")
    print("-" * 70)
    try:
        resp = requests.get(f"{server_url}/api/wayside/ctc_commands", timeout=5.0)
        if resp.status_code == 200:
            print("✅ PASS: Can read CTC commands")
            data = resp.json()
            trains = data.get("Trains", {})
            print(f"   Found {len(trains)} train(s) in CTC data")
            if trains:
                for train_name, train_info in trains.items():
                    pos = train_info.get("Train Position", "?")
                    active = train_info.get("Active", 0)
                    speed = train_info.get("Suggested Speed", 0)
                    auth = train_info.get("Suggested Authority", 0)
                    print(f"   - {train_name}: Pos={pos}, Active={active}, Speed={speed}, Auth={auth}")
        else:
            print(f"⚠️  WARNING: Status {resp.status_code}")
            print("   CTC data may not be initialized yet")
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False
    
    # Test 3: Train physics endpoint (wayside reads train speeds)
    print("\n[Test 3/5] Train Physics Endpoint (GET)")
    print("-" * 70)
    try:
        resp = requests.get(f"{server_url}/api/wayside/train_physics", timeout=5.0)
        if resp.status_code == 200:
            print("✅ PASS: Can read train physics data")
            data = resp.json()
            train_count = len([k for k in data.keys() if k.startswith('train_')])
            print(f"   Found {train_count} train(s) in physics data")
            if train_count > 0:
                for key, value in data.items():
                    if key.startswith('train_'):
                        train_id = key.replace('train_', '')
                        outputs = value.get('outputs', {})
                        velocity = outputs.get('velocity_mph', 0)
                        print(f"   - Train {train_id}: Velocity={velocity:.1f} mph")
        else:
            print(f"⚠️  WARNING: Status {resp.status_code}")
            print("   Train data may not be initialized yet")
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False
    
    # Test 4: Train status update endpoint (wayside writes position)
    print("\n[Test 4/5] Train Status Update Endpoint (POST)")
    print("-" * 70)
    try:
        test_data = {
            "train": "Train 99",  # Use dummy train to avoid affecting real system
            "position": 999,
            "state": "test",
            "active": 0
        }
        resp = requests.post(f"{server_url}/api/wayside/train_status", 
                            json=test_data, timeout=5.0)
        if resp.status_code == 200:
            print("✅ PASS: Can write train status updates")
            print("   Wayside can report train positions back to CTC")
        else:
            print(f"❌ FAIL: Status {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False
    
    # Test 5: Train commands endpoint (wayside writes commands to trains)
    print("\n[Test 5/5] Train Commands Endpoint (POST)")
    print("-" * 70)
    try:
        test_data = {
            "train": "Train 99",  # Use dummy train
            "commanded_speed": 0.0,
            "commanded_authority": 0.0,
            "current_station": "",
            "next_station": ""
        }
        resp = requests.post(f"{server_url}/api/wayside/train_commands", 
                            json=test_data, timeout=5.0)
        if resp.status_code == 200:
            print("✅ PASS: Can write train commands")
            print("   Wayside can send speed/authority to trains")
        else:
            print(f"❌ FAIL: Status {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False
    
    # Summary
    print("\n" + "=" * 70)
    print("  🎉 ALL TESTS PASSED!")
    print("=" * 70)
    print("\n✅ Raspberry Pi can successfully communicate with PC REST API server")
    print("✅ All required endpoints are accessible")
    print("✅ HW Wayside controller should work correctly in distributed mode")
    print("\nNext steps:")
    print("  1. On PC: Start REST API server (train_controller/api/train_api_server.py)")
    print("  2. On PC: Start CTC + SW Wayside (combine_ctc_wayside_test.py)")
    print(f"  3. On Pi: export SERVER_URL={server_url}")
    print("  4. On Pi: python launch_hw_wayside_only.py")
    print("\n" + "=" * 70)
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_pi_connection.py <server_url>")
        print("Example: python test_pi_connection.py http://10.5.127.125:5000")
        sys.exit(1)
    
    server_url = sys.argv[1].rstrip('/')
    
    try:
        success = test_connection(server_url)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)

if __name__ == "__main__":
    main()
