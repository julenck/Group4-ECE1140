#!/usr/bin/env python3
"""
Debug script for Raspberry Pi hardware wayside setup.
Shows environment variable status and tests the wayside launch.
"""

import os
import sys

def main():
    print("=" * 60)
    print("🔧 HARDWARE WAYSIDE DEBUG - RASPBERRY PI")
    print("=" * 60)

    # Check environment variables
    print("\n📋 ENVIRONMENT VARIABLES:")
    print("-" * 30)

    server_url = os.environ.get('SERVER_URL', 'NOT SET')
    print(f"SERVER_URL: {server_url}")

    if server_url == 'NOT SET':
        print("❌ ERROR: SERVER_URL environment variable not set!")
        print("\n🔧 FIX:")
        print("   export SERVER_URL=http://YOUR_PC_IP:5000")
        print("   # Replace YOUR_PC_IP with your PC's IP address")
        print("   python debug_wayside_pi.py")
        return

    # Check if we can import hardware wayside components
    print("
🔍 IMPORT CHECK:"    print("-" * 30)

    try:
        from track_controller.hw_wayside.hw_wayside_controller import HW_Wayside_Controller
        from track_controller.hw_wayside.hw_wayside_controller_ui import HW_Wayside_Controller_UI
        print("✅ Hardware wayside imports successful")
        hw_available = True
    except ImportError as e:
        print(f"❌ Hardware wayside import failed: {e}")
        hw_available = False
        return

    # Check if we can import the test function
    try:
        from combine_ctc_wayside_test import run_wayside_hw_ui_2
        print("✅ combine_ctc_wayside_test import successful")
    except ImportError as e:
        print(f"❌ combine_ctc_wayside_test import failed: {e}")
        return

    print("
🎯 LAUNCH STATUS:"    print("-" * 30)
    print(f"✅ SERVER_URL is set: {server_url}")
    print(f"✅ Hardware wayside components available: {hw_available}")
    print("✅ All imports successful")

    print("
🚀 READY TO LAUNCH HARDWARE WAYSIDE!"    print("-" * 30)
    print("The script will now launch the hardware wayside controller.")
    print("Press Ctrl+C to stop if needed.")
    print("\nLaunching in 3 seconds...")
    import time
    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)

    print("\n🎬 STARTING HARDWARE WAYSIDE CONTROLLER...")
    try:
        run_wayside_hw_ui_2()
    except KeyboardInterrupt:
        print("\n⏹️  Stopped by user")
    except Exception as e:
        print(f"\n❌ Error during launch: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

