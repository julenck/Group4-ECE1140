#!/usr/bin/env python3
"""
Test script for running Hardware Wayside Controller on Raspberry Pi in server mode.

Usage:
    # Set server URL to your PC's IP address
    export SERVER_URL=http://10.5.127.125:5000
    
    # Run this script
    python test_hw_wayside_rpi.py
"""

import os
import sys
import tkinter as tk

# Ensure we're in the project root
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import hardware wayside components
try:
    from track_controller.hw_wayside.hw_wayside_controller import HW_Wayside_Controller
    from track_controller.hw_wayside.hw_wayside_controller_ui import HW_Wayside_Controller_UI
    print("✅ Successfully imported hardware wayside components")
except ImportError as e:
    print(f"❌ Failed to import hardware wayside components: {e}")
    sys.exit(1)

def main():
    # Get server URL from environment variable
    server_url = os.environ.get('SERVER_URL', None)
    
    if not server_url:
        print("❌ ERROR: SERVER_URL environment variable not set!")
        print("   Example: export SERVER_URL=http://10.5.127.125:5000")
        sys.exit(1)
    
    print(f"🌐 Server URL: {server_url}")
    
    # Define blocks managed by this wayside (70-143 for Wayside B)
    blocks_70_143 = list(range(70, 144))
    
    print(f"🚂 Creating Hardware Wayside Controller B (blocks 70-143)...")
    
    # Create hardware wayside controller with API support
    try:
        controller = HW_Wayside_Controller(
            wayside_id="B",  # Wayside B (2nd wayside)
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
    
    # Create Tk window
    print("🖥️  Creating UI...")
    root = tk.Tk()
    root.title("Hardware Wayside B [SERVER MODE] - Raspberry Pi")
    root.geometry("1200x800")
    
    # Create UI
    try:
        ui = HW_Wayside_Controller_UI(
            root=root,
            controller=controller,
            title="Hardware Wayside B - X and L Down (Blocks 70-143) [SERVER MODE]"
        )
        ui.pack(fill=tk.BOTH, expand=True)
        print("✅ UI created successfully")
    except Exception as e:
        print(f"❌ Failed to create UI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("🚀 Starting UI mainloop...")
    print("   (Press Ctrl+C in terminal or close window to exit)")
    
    # Start mainloop
    root.mainloop()

if __name__ == "__main__":
    main()

