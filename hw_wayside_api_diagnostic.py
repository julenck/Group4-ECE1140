#!/usr/bin/env python3
"""
Comprehensive diagnostic for HW Wayside API usage.
Tests all server endpoints that HW wayside should call.
"""

import os
import sys
import json
import requests

def main():
    print("HW Wayside API Diagnostic")
    print("=" * 40)

    server_url = os.environ.get('SERVER_URL')
    if not server_url:
        print("[ERROR] SERVER_URL not set")
        print("   Run: export SERVER_URL=http://YOUR_PC_IP:5000")
        return

    print(f"Testing server: {server_url}")
    print()

    # Test 1: Server health
    print("1. Testing server health...")
    try:
        response = requests.get(f"{server_url}/api/health", timeout=5)
        if response.status_code == 200:
            print("   [OK] Server is responding")
        else:
            print(f"   [FAIL] Server returned status {response.status_code}")
            return
    except Exception as e:
        print(f"   [FAIL] Cannot reach server: {e}")
        return

    # Test 2: CTC commands endpoint (HW wayside reads this)
    print("\n2. Testing CTC commands endpoint (HW wayside reads)...")
    try:
        response = requests.get(f"{server_url}/api/wayside/ctc_commands", timeout=5)
        if response.status_code == 200:
            data = response.json()
            trains = data.get("Trains", {})
            print(f"   [OK] Endpoint works - found {len(trains)} trains")
            for train_name, train_data in trains.items():
                pos = train_data.get('Train Position', 0)
                active = train_data.get('Active', 0)
                print(f"      {train_name}: pos={pos}, active={active}")
        else:
            print(f"   [FAIL] Endpoint failed: status {response.status_code}")
    except Exception as e:
        print(f"   [FAIL] Request failed: {e}")

    # Test 3: Train physics endpoint (HW wayside reads this)
    print("\n3. Testing train physics endpoint (HW wayside reads)...")
    try:
        response = requests.get(f"{server_url}/api/wayside/train_physics", timeout=5)
        if response.status_code == 200:
            data = response.json()
            train_count = len([k for k in data.keys() if k.startswith('train_')])
            print(f"   [OK] Endpoint works - found {train_count} trains in train_data.json")
            for key, train_data in data.items():
                if key.startswith('train_'):
                    outputs = train_data.get('outputs', {})
                    vel = outputs.get('velocity_mph', 0)
                    print(f"      {key}: velocity={vel:.1f} mph")
        else:
            print(f"   [FAIL] Endpoint failed: status {response.status_code}")
    except Exception as e:
        print(f"   [FAIL] Request failed: {e}")

    # Test 4: Train commands endpoint (HW wayside writes this)
    print("\n4. Testing train commands endpoint (HW wayside writes)...")
    test_command = {
        'train': 'Train 1',
        'commanded_speed': 25.0,
        'commanded_authority': 500.0,
        'current_station': 'Station A',
        'next_station': 'Station B'
    }
    try:
        response = requests.post(f"{server_url}/api/wayside/train_commands",
                               json=test_command, timeout=5)
        if response.status_code == 200:
            print("   [OK] Train commands endpoint works")
        else:
            print(f"   [FAIL] Endpoint failed: status {response.status_code}")
    except Exception as e:
        print(f"   [FAIL] Request failed: {e}")

    # Test 5: Train status endpoint (HW wayside writes this)
    print("\n5. Testing train status endpoint (HW wayside writes)...")
    test_status = {
        'train': 'Train 1',
        'position': 75,
        'state': 'moving',
        'active': 1
    }
    try:
        response = requests.post(f"{server_url}/api/wayside/train_status",
                               json=test_status, timeout=5)
        if response.status_code == 200:
            print("   [OK] Train status endpoint works")
        else:
            print(f"   [FAIL] Endpoint failed: status {response.status_code}")
    except Exception as e:
        print(f"   [FAIL] Request failed: {e}")

    print("\n6. Testing HW wayside initialization...")
    try:
        # Test if HW wayside can be created
        from track_controller.hw_wayside.hw_wayside_controller import HW_Wayside_Controller
        controller = HW_Wayside_Controller(
            wayside_id="B",
            block_ids=list(range(70, 144)),
            server_url=server_url,
            timeout=5.0
        )
        print("   [OK] HW wayside controller created successfully")

        # Check if API client was initialized
        if controller.wayside_api:
            print("   [OK] API client initialized")
        else:
            print("   [FAIL] API client NOT initialized - will use file I/O fallback")

        # Test loading CTC inputs
        print("   Testing CTC input loading...")
        controller.load_ctc_inputs()
        print(f"      Found {len(controller.active_trains)} active trains")

    except Exception as e:
        print(f"   [FAIL] HW wayside init failed: {e}")
        import traceback
        traceback.print_exc()

    print("\nDIAGNOSIS:")
    print("   HW Wayside calls these endpoints in this order:")
    print("   1. GET /api/wayside/ctc_commands (reads CTC commands)")
    print("   2. GET /api/wayside/train_physics (reads train speeds)")
    print("   3. POST /api/wayside/train_commands (sends speed/authority commands)")
    print("   4. POST /api/wayside/train_status (reports train positions to CTC)")
    print()
    print("   If HW wayside shows '[FAIL] API client NOT initialized', it falls back to file I/O.")
    print("   Make sure SERVER_URL is set correctly on the Raspberry Pi!")

if __name__ == "__main__":
    main()
