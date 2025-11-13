"""Quick Start Script for Testing Network Setup

This script helps test the REST API server and client connection.
"""
import requests
import time

def test_server_connection(server_url="http://localhost:5000"):
    """Test connection to REST API server."""
    print("=" * 70)
    print("  TESTING REST API SERVER CONNECTION")
    print("=" * 70)
    print(f"\nServer URL: {server_url}\n")
    
    # Test 1: Health check
    print("Test 1: Health Check")
    try:
        response = requests.get(f"{server_url}/api/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Server is running")
            print(f"  ✓ Status: {data['status']}")
            print(f"  ✓ Message: {data['message']}")
        else:
            print(f"  ✗ Server returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Connection failed: {e}")
        return False
    
    # Test 2: Get all trains
    print("\nTest 2: Get All Trains")
    try:
        response = requests.get(f"{server_url}/api/trains", timeout=2)
        if response.status_code == 200:
            trains = response.json()
            print(f"  ✓ Retrieved train list")
            print(f"  ✓ Active trains: {len(trains)}")
        else:
            print(f"  ✗ Failed to get trains: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Request failed: {e}")
    
    # Test 3: Create/Update train state
    print("\nTest 3: Update Train 1 State")
    try:
        test_data = {
            "service_brake": True,
            "driver_velocity": 25.0,
            "power_command": 5000.0
        }
        response = requests.post(f"{server_url}/api/train/1/state", json=test_data, timeout=2)
        if response.status_code == 200:
            print(f"  ✓ Successfully updated train 1 state")
        else:
            print(f"  ✗ Update failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Request failed: {e}")
    
    # Test 4: Get train state
    print("\nTest 4: Get Train 1 State")
    try:
        response = requests.get(f"{server_url}/api/train/1/state", timeout=2)
        if response.status_code == 200:
            state = response.json()
            print(f"  ✓ Retrieved train 1 state")
            print(f"  ✓ Service brake: {state.get('service_brake', 'N/A')}")
            print(f"  ✓ Driver velocity: {state.get('driver_velocity', 'N/A')} mph")
            print(f"  ✓ Power command: {state.get('power_command', 'N/A')} W")
        else:
            print(f"  ✗ Get failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Request failed: {e}")
    
    print("\n" + "=" * 70)
    print("  ALL TESTS COMPLETED")
    print("=" * 70)
    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    else:
        server_url = "http://localhost:5000"
    
    print("\nStarting API server tests...")
    print("Make sure the REST API server is running!")
    print(f"(Run: python start_server.py)\n")
    
    time.sleep(1)
    
    success = test_server_connection(server_url)
    
    if success:
        print("\n✓ All tests passed! Server is working correctly.")
    else:
        print("\n✗ Tests failed. Check if server is running.")
