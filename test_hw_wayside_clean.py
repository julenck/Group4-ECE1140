#!/usr/bin/env python3
"""
Clean test for HW wayside functionality.
Run this to verify HW wayside is working without excessive debug output.
"""

import os
import sys
import json
import time

def check_files():
    """Check if key files exist and have expected structure."""
    print("Checking files...")

    # CTC file
    ctc_file = "ctc_track_controller.json"
    if os.path.exists(ctc_file):
        with open(ctc_file, 'r') as f:
            data = json.load(f)
        trains = data.get("Trains", {})
        print(f"✅ CTC file: {len(trains)} trains")
    else:
        print("❌ CTC file missing")

    # Wayside file
    wayside_file = "track_controller/New_SW_Code/wayside_to_train.json"
    if os.path.exists(wayside_file):
        with open(wayside_file, 'r') as f:
            data = json.load(f)
        print(f"✅ Wayside file: {len(data)} train commands")
    else:
        print("❌ Wayside file missing")

def test_api_connection(server_url):
    """Test API connection if SERVER_URL is set."""
    if not server_url:
        return

    import requests
    try:
        response = requests.get(f"{server_url}/api/health", timeout=3.0)
        if response.status_code == 200:
            print("✅ API connection working")
        else:
            print(f"❌ API error: {response.status_code}")
    except:
        print("❌ API connection failed")

def main():
    print("🧪 HW Wayside Clean Test")
    print("=" * 30)

    server_url = os.environ.get('SERVER_URL')
    if server_url:
        print(f"🌐 Server mode: {server_url}")
        test_api_connection(server_url)
    else:
        print("📁 File mode (no SERVER_URL)")

    check_files()

    print("\n📋 To test HW wayside:")
    print("1. Run: python launch_hw_wayside_only.py")
    print("2. Check for clean startup messages")
    print("3. Look for CTC position updates in server logs")
    print("4. Verify files update correctly")

if __name__ == "__main__":
    main()
