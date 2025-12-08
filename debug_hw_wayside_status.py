#!/usr/bin/env python3
"""
Debug script to check HW wayside status and file interactions.
Run this to see what the HW wayside is reading/writing.
"""

import os
import sys
import json
import time

def check_files():
    """Check the key files that HW wayside should interact with."""
    print("🔍 Checking HW Wayside Files")
    print("=" * 50)

    # CTC track controller file
    ctc_file = "ctc_track_controller.json"
    print(f"\n📄 CTC File: {ctc_file}")
    if os.path.exists(ctc_file):
        try:
            with open(ctc_file, 'r') as f:
                data = json.load(f)
            trains = data.get("Trains", {})
            print(f"   ✅ Found {len(trains)} trains:")
            for train_name, train_data in trains.items():
                active = train_data.get("Active", 0)
                position = train_data.get("Train Position", 0)
                speed = train_data.get("Suggested Speed", 0)
                authority = train_data.get("Suggested Authority", 0)
                print(f"      {train_name}: Active={active}, Pos={position}, Speed={speed}, Auth={authority}")
        except Exception as e:
            print(f"   ❌ Error reading file: {e}")
    else:
        print("   ❌ File not found")

    # Wayside to train file
    wayside_file = "track_controller/New_SW_Code/wayside_to_train.json"
    print(f"\n🚂 Wayside Output File: {wayside_file}")
    if os.path.exists(wayside_file):
        try:
            with open(wayside_file, 'r') as f:
                data = json.load(f)
            print(f"   ✅ Found commands for {len(data)} trains:")
            for train_name, commands in data.items():
                speed = commands.get("Commanded Speed", 0)
                authority = commands.get("Commanded Authority", 0)
                print(f"      {train_name}: Speed={speed}, Authority={authority}")
        except Exception as e:
            print(f"   ❌ Error reading file: {e}")
    else:
        print("   ❌ File not found")

def simulate_hw_wayside_logic():
    """Simulate what the HW wayside should be doing."""
    print("🧠 Simulating HW Wayside Logic")    
    print("=" * 50)

    # Check if we have SERVER_URL
    server_url = os.environ.get('SERVER_URL')
    if server_url:
        print(f"🌐 SERVER_URL set: {server_url}")
    else:
        print("❌ SERVER_URL not set - wayside will use file I/O")

    # Check what blocks HW wayside B should control
    blocks_70_143 = list(range(70, 144))
    print(f"🎯 HW Wayside B should control blocks: {min(blocks_70_143)}-{max(blocks_70_143)}")

    # Check CTC file for trains in those blocks
    ctc_file = "ctc_track_controller.json"
    if os.path.exists(ctc_file):
        try:
            with open(ctc_file, 'r') as f:
                data = json.load(f)
            trains = data.get("Trains", {})

            trains_in_range = []
            for train_name, train_data in trains.items():
                position = train_data.get("Train Position", 0)
                if position in blocks_70_143:
                    trains_in_range.append((train_name, position))

            if trains_in_range:
                print("✅ Found trains in HW wayside range:")
                for train_name, position in trains_in_range:
                    print(f"   {train_name} at block {position}")
            else:
                print("ℹ️  No trains currently in HW wayside range (70-143)")
        except Exception as e:
            print(f"❌ Error checking trains: {e}")

def check_api_connectivity(server_url):
    """Test API connectivity if SERVER_URL is set."""
    if not server_url:
        return

    print("🔗 Testing API Connectivity")    
    print("=" * 50)

    import requests

    # Test health endpoint
    try:
        response = requests.get(f"{server_url}/api/health", timeout=5.0)
        if response.status_code == 200:
            print("✅ API health check passed")
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return

    # Test wayside endpoints
    endpoints = [
        f"{server_url}/api/wayside/ctc_commands",
        f"{server_url}/api/wayside/train_physics"
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=5.0)
            if response.status_code == 200:
                print(f"✅ {endpoint}: OK")
            else:
                print(f"⚠️  {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")

def main():
    print("🔧 HW Wayside Debug Tool")
    print("=" * 60)

    # Get server URL
    server_url = os.environ.get('SERVER_URL')
    if server_url:
        print(f"🌐 SERVER_URL: {server_url}")
    else:
        print("📁 No SERVER_URL - using file-based I/O mode")

    # Check files
    check_files()

    # Simulate logic
    simulate_hw_wayside_logic()

    # Test API if available
    if server_url:
        check_api_connectivity(server_url)

    print("📋 SUMMARY")    
    print("=" * 60)
    print("If HW wayside is running, you should see:")
    print("1. Console messages about loading CTC inputs")
    print("2. Updates to ctc_track_controller.json train positions")
    print("3. Commands written to wayside_to_train.json")
    print("4. API calls to server (if SERVER_URL set)")
    print("")
    print("Run: python launch_hw_wayside_only.py")
    print("Then check this tool again to see file changes!")

if __name__ == "__main__":
    main()
