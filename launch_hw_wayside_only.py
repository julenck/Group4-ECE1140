#!/usr/bin/env python3
"""
Standalone Hardware Wayside Controller Launcher for Raspberry Pi.

This launches ONLY the hardware wayside controller (Wayside B, blocks 70-143)
in server mode for distributed deployment.

Usage:
    export SERVER_URL=http://YOUR_PC_IP:5000
    python launch_hw_wayside_only.py
"""

import os
import sys
import tkinter as tk

# Ensure we're in the project root
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def main():
    print("🚂 Launching Hardware Wayside Controller B (Blocks 70-143)")

    # Check SERVER_URL
    server_url = os.environ.get('SERVER_URL', None)
    if not server_url:
        print("❌ ERROR: SERVER_URL environment variable not set!")
        print("   Run: export SERVER_URL=http://YOUR_PC_IP:5000")
        sys.exit(1)

    print(f"🌐 Server URL: {server_url}")

    try:
        # Import hardware wayside components
        from track_controller.hw_wayside.hw_wayside_controller import HW_Wayside_Controller
        from track_controller.hw_wayside.hw_wayside_controller_ui import HW_Wayside_Controller_UI
        print("✅ Hardware wayside components loaded")
    except ImportError as e:
        print(f"❌ Failed to import hardware wayside: {e}")
        sys.exit(1)

    # Define blocks for Wayside B (70-143)
    blocks_70_143 = list(range(70, 144))

    print("🏗️  Creating wayside controller...")
    try:
        controller = HW_Wayside_Controller(
            wayside_id="B",
            block_ids=blocks_70_143,
            server_url=server_url,
            timeout=5.0
        )
        print("✅ Controller created successfully")
    except Exception as e:
        print(f"❌ Failed to create controller: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("🖥️  Creating UI...")
    try:
        root = tk.Tk()
        root.title("Hardware Wayside B [SERVER MODE] - Distributed")
        root.geometry("1200x800")

        ui = HW_Wayside_Controller_UI(
            root=root,
            controller=controller,
            title="Hardware Wayside B - X and L Down (Blocks 70-143) [DISTRIBUTED]"
        )
        ui.pack(fill=tk.BOTH, expand=True)
        print("✅ UI created successfully")
    except Exception as e:
        print(f"❌ Failed to create UI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("🚀 Starting Hardware Wayside Controller B...")
    print("   (Press Ctrl+C in terminal or close window to stop)")
    print("=" * 60)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\n⏹️  Stopped by user")
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")

if __name__ == "__main__":
    main()

