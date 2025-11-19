#!/usr/bin/env python3
"""Diagnostic tool to test Train Model Test UI → Server → Hardware Controller flow"""

import requests
import json
import sys
import time

def test_server_connection(server_url):
    """Test if server is reachable"""
    print(f"Testing connection to {server_url}...")
    try:
        response = requests.get(f"{server_url}/api/health", timeout=2.0)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Server is running")
            print(f"  Status: {data.get('status')}")
            print(f"  Timestamp: {data.get('timestamp')}")
            return True
        else:
            print(f"✗ Server returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Cannot reach server: {e}")
        return False

def test_train_state(server_url, train_id):
    """Test fetching train state"""
    print(f"\nFetching state for Train {train_id}...")
    try:
        response = requests.get(f"{server_url}/api/train/{train_id}/state", timeout=2.0)
        if response.status_code == 200:
            state = response.json()
            print(f"✓ Train {train_id} state retrieved")
            print(f"  Commanded Speed: {state.get('commanded_speed')}")
            print(f"  Speed Limit: {state.get('speed_limit')}")
            print(f"  Train Velocity: {state.get('train_velocity')}")
            print(f"  Current Station: {state.get('current_station', 'N/A')}")
            return True
        elif response.status_code == 404:
            print(f"⚠ Train {train_id} not found on server")
            print(f"  This is normal if train hasn't been created yet")
            return False
        else:
            print(f"✗ Server returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Error fetching train state: {e}")
        return False

def test_update_train_state(server_url, train_id):
    """Test sending data to server"""
    print(f"\nTesting data update for Train {train_id}...")
    test_data = {
        "commanded_speed": 42.0,
        "speed_limit": 45.0,
        "current_station": "Test Station"
    }
    try:
        response = requests.post(
            f"{server_url}/api/train/{train_id}/state",
            json=test_data,
            timeout=2.0
        )
        if response.status_code == 200:
            print(f"✓ Successfully sent test data to server")
            print(f"  Sent: {test_data}")
            
            # Verify the update
            time.sleep(0.5)
            response = requests.get(f"{server_url}/api/train/{train_id}/state", timeout=2.0)
            if response.status_code == 200:
                state = response.json()
                if state.get('commanded_speed') == 42.0:
                    print(f"✓ Server correctly stored the data")
                    return True
                else:
                    print(f"⚠ Data not stored correctly")
                    print(f"  Expected: 42.0, Got: {state.get('commanded_speed')}")
                    return False
            return True
        else:
            print(f"✗ Server returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Error updating train state: {e}")
        return False

def check_local_files():
    """Check if local JSON files exist and are readable"""
    print("\nChecking local files...")
    
    files_to_check = [
        "Train Model/train_data.json",
        "train_controller/data/train_states.json"
    ]
    
    all_exist = True
    for filepath in files_to_check:
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                print(f"✓ {filepath} exists and is valid JSON")
        except FileNotFoundError:
            print(f"⚠ {filepath} not found (will be created when needed)")
            all_exist = False
        except json.JSONDecodeError:
            print(f"✗ {filepath} exists but contains invalid JSON")
            all_exist = False
        except Exception as e:
            print(f"✗ Error reading {filepath}: {e}")
            all_exist = False
    
    return all_exist

def main():
    print("=" * 70)
    print("  HARDWARE TRAIN CONTROLLER DIAGNOSTIC TOOL")
    print("=" * 70)
    
    if len(sys.argv) < 2:
        print("\nUsage: python diagnostic_tool.py <server_url> [train_id]")
        print("\nExample:")
        print("  python diagnostic_tool.py http://192.168.1.100:5000 1")
        print("\nThis tool tests the connection between:")
        print("  - Train Model Test UI")
        print("  - REST API Server")
        print("  - Hardware Train Controller")
        sys.exit(1)
    
    server_url = sys.argv[1].rstrip('/')
    train_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    print(f"\nServer URL: {server_url}")
    print(f"Train ID: {train_id}")
    print()
    
    # Run tests
    tests_passed = 0
    tests_total = 4
    
    # Test 1: Server connection
    if test_server_connection(server_url):
        tests_passed += 1
    
    # Test 2: Local files
    if check_local_files():
        tests_passed += 1
    
    # Test 3: Fetch train state
    if test_train_state(server_url, train_id):
        tests_passed += 1
    
    # Test 4: Update train state
    if test_update_train_state(server_url, train_id):
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 70)
    print(f"  RESULTS: {tests_passed}/{tests_total} tests passed")
    print("=" * 70)
    
    if tests_passed == tests_total:
        print("\n✓ All tests passed! System is working correctly.")
        print("\nNext steps:")
        print(f"  1. Start Train Model Test UI:")
        print(f"     python train_model_test_ui.py --train-id {train_id} --server {server_url}")
        print(f"  2. Start Hardware Controller on Raspberry Pi:")
        print(f"     python train_controller_hw_ui.py --train-id {train_id} --server {server_url}")
    elif tests_passed >= 2:
        print("\n⚠ Some tests passed, but there are issues.")
        print("  Check the error messages above.")
        print("  Make sure the server is running: python start_server.py")
    else:
        print("\n✗ Most tests failed.")
        print("  Make sure:")
        print("  1. Server is running: python train_controller/start_server.py")
        print("  2. Server URL is correct")
        print("  3. Firewall allows port 5000")
    
    print()

if __name__ == "__main__":
    main()
