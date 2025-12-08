#!/usr/bin/env python3
"""
Quick test to verify Raspberry Pi can reach the PC's REST API server.

Usage on Raspberry Pi:
    python test_server_connection.py http://10.5.127.125:5000
"""

import sys
import requests

def test_server(server_url):
    """Test if server is reachable."""
    print(f"Testing connection to: {server_url}")
    print("-" * 60)
    
    try:
        # Test health endpoint
        health_url = f"{server_url}/api/health"
        print(f"\n1. Testing health endpoint: {health_url}")
        response = requests.get(health_url, timeout=5.0)
        
        if response.status_code == 200:
            print(f"   ✅ SUCCESS: {response.json()}")
        else:
            print(f"   ❌ FAILED: Status code {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"   ❌ TIMEOUT: Server did not respond within 5 seconds")
        print(f"   → Check if server is running on PC")
        print(f"   → Check if PC firewall is blocking port 5000")
        return False
        
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ CONNECTION ERROR: {e}")
        print(f"   → Check if server is running: python train_controller/api/train_api_server.py")
        print(f"   → Check if PC IP address is correct: {server_url}")
        print(f"   → Check if PC and Raspberry Pi are on same network")
        return False
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False
    
    # Test wayside endpoints
    try:
        print(f"\n2. Testing wayside CTC commands endpoint")
        ctc_url = f"{server_url}/api/wayside/ctc_commands"
        response = requests.get(ctc_url, timeout=5.0)
        
        if response.status_code == 200:
            print(f"   ✅ SUCCESS: CTC commands endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"   ⚠ WARNING: Status code {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("✅ CONNECTION TEST PASSED!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Set SERVER_URL:")
    print(f"   export SERVER_URL={server_url}")
    print("2. Run hardware wayside:")
    print("   python test_hw_wayside_rpi.py")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_server_connection.py <server_url>")
        print("Example: python test_server_connection.py http://10.5.127.125:5000")
        sys.exit(1)
    
    server_url = sys.argv[1].rstrip('/')
    success = test_server(server_url)
    sys.exit(0 if success else 1)

