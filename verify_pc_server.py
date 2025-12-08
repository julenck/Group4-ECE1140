#!/usr/bin/env python3
"""
Script to verify PC server is working and receiving wayside API calls.
Run this on the PC to check server status.
"""

import os
import sys
import requests
import time
import json

def check_server_running():
    """Check if the server is running."""
    print("🔍 Checking if server is running...")

    try:
        response = requests.get("http://localhost:5000/api/health", timeout=5.0)
        if response.status_code == 200:
            print("✅ Server is running and healthy")
            return True
        else:
            print(f"❌ Server responded with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("   → Start server with: python train_controller/api/train_api_server.py")
        return False

def test_server_endpoints():
    """Test all wayside-related endpoints."""
    print("🔗 Testing server endpoints...")

    endpoints = [
        ("GET", "http://localhost:5000/api/health", None),
        ("GET", "http://localhost:5000/api/wayside/ctc_commands", None),
        ("GET", "http://localhost:5000/api/wayside/train_physics", None),
        ("POST", "http://localhost:5000/api/wayside/train_status",
         {"train": "Train 1", "position": 50, "state": "test", "active": 1})
    ]

    for method, url, data in endpoints:
        try:
            if method == "GET":
                response = requests.get(url, timeout=5.0)
            else:
                response = requests.post(url, json=data, timeout=5.0)

            if response.status_code == 200:
                print(f"✅ {method} {url}: OK")
            else:
                print(f"❌ {method} {url}: {response.status_code} - {response.text[:100]}")
        except Exception as e:
            print(f"❌ {method} {url}: {e}")

def check_ctc_file():
    """Check the current state of ctc_track_controller.json."""
    print("📄 Checking ctc_track_controller.json...")

    file_path = "ctc_track_controller.json"
    if not os.path.exists(file_path):
        print(f"❌ {file_path} not found")
        return

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        trains = data.get("Trains", {})
        print(f"📊 Current train status:")
        for train_name, train_data in trains.items():
            active = train_data.get("Active", 0)
            position = train_data.get("Train Position", 0)
            state = train_data.get("Train State", "unknown")
            print(f"   {train_name}: Active={active}, Position={position}, State={state}")

    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")

def wait_for_wayside_updates():
    """Wait for wayside updates and show them."""
    print("⏳ Waiting for wayside updates...")
    print("   (This will show live updates from Raspberry Pi wayside)")
    print("   Press Ctrl+C to stop")

    initial_trains = {}
    file_path = "ctc_track_controller.json"

    try:
        while True:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)

                trains = data.get("Trains", {})
                changed = False

                for train_name, train_data in trains.items():
                    position = train_data.get("Train Position", 0)
                    prev_position = initial_trains.get(train_name, {}).get("position", position)

                    if position != prev_position:
                        print(f"📍 {train_name} position changed: {prev_position} → {position}")
                        changed = True

                    initial_trains[train_name] = {"position": position}

                if changed:
                    print("   (Wayside successfully updated CTC!)")

            time.sleep(2)  # Check every 2 seconds

    except KeyboardInterrupt:
        print("\n⏹️  Stopped monitoring")

def main():
    print("🖥️  PC SERVER VERIFICATION")
    print("=" * 40)

    # Check server
    if not check_server_running():
        return

    # Test endpoints
    test_server_endpoints()

    # Check CTC file
    check_ctc_file()

    print("\n" + "=" * 40)
    print("🎯 Ready to receive wayside updates!")
    print("=" * 40)

    print("\n📋 To test with Raspberry Pi:")
    print("1. On Raspberry Pi: export SERVER_URL=http://YOUR_PC_IP:5000")
    print("2. On Raspberry Pi: python launch_hw_wayside_only.py")
    print("3. Watch this terminal for wayside API calls")
    print("4. Check if ctc_track_controller.json updates")

    # Offer to monitor for updates
    response = input("\n🔍 Monitor for live wayside updates? (y/n): ").lower().strip()
    if response == 'y':
        wait_for_wayside_updates()
    else:
        print("✅ Server verification complete!")

if __name__ == "__main__":
    main()
