#!/usr/bin/env python3
"""
Simple test to verify HW wayside is working.
Run this instead of the full UI to see what's happening.
"""

import os
import sys
import time

# Ensure we're in the project root
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def main():
    print("🧪 Simple HW Wayside Test")
    print("=" * 30)

    server_url = os.environ.get('SERVER_URL')
    if not server_url:
        print("❌ SERVER_URL not set")
        return

    print(f"🌐 Server: {server_url}")

    try:
        from track_controller.hw_wayside.hw_wayside_controller import HW_Wayside_Controller

        # Create controller
        blocks = list(range(70, 144))  # Wayside B blocks
        controller = HW_Wayside_Controller(
            wayside_id="B",
            block_ids=blocks,
            server_url=server_url,
            timeout=5.0
        )

        print("✅ HW Wayside controller created")

        # Check managed blocks
        print(f"🎯 Managed blocks: {sorted(controller.managed_blocks) if controller.managed_blocks else 'None'}")

        # Check if API client was created
        if controller.wayside_api:
            print("✅ API client initialized")
        else:
            print("❌ API client NOT initialized - falling back to file I/O")

        # Manually trigger CTC input loading
        print("📡 Loading CTC inputs...")
        controller.load_ctc_inputs()
        print(f"📊 Active trains: {len(controller.active_trains)}")

        if controller.active_trains:
            print("🚂 Trains found:")
            for train_id, train_data in controller.active_trains.items():
                pos = train_data.get('Train Position', 0)
                active = train_data.get('Active', 0)
                speed = train_data.get('Suggested Speed', 0)
                authority = train_data.get('Suggested Authority', 0)
                print(f"   {train_id}: Pos={pos}, Active={active}, Speed={speed}, Auth={authority}")

                # Check if this train is in our managed blocks
                if pos in controller.managed_blocks:
                    print(f"   ✅ {train_id} is in managed blocks (70-143)")
                else:
                    print(f"   ❌ {train_id} is NOT in managed blocks (70-143)")
        else:
            print("❌ No active trains found in CTC")

        # Try to start trains cycle briefly
        print("🔄 Starting trains cycle for 5 seconds...")
        controller.start_trains(period_s=1.0)
        time.sleep(5)
        controller.stop()

        print("✅ Test completed")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
