#!/usr/bin/env python3
"""
Complete System Launcher for Handoff Testing
Launches: CTC, SW Wayside, HW Wayside, Train Model, Train Controllers

Usage on Pi or Mac:
    cd "/path/to/Group4-ECE1140 CODE"
    python3 launch_full_system_test.py
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk

# Ensure we're in project root
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("=" * 60)
print("🚂 LAUNCHING COMPLETE TRAIN SYSTEM FOR HANDOFF TEST")
print("=" * 60)

# ============================================================================
# 1. CTC (Dispatcher)
# ============================================================================
def launch_ctc():
    print("\n[1/5] 🎛️  Launching CTC Dispatcher...")
    try:
        from ctc.ctc_ui_temp import CTCUI
        ctc_ui = CTCUI()
        ctc_ui.run()
    except Exception as e:
        print(f"❌ CTC failed to launch: {e}")
        import traceback
        traceback.print_exc()

# ============================================================================
# 2. SW Wayside Controller (Blocks 0-69)
# ============================================================================
def launch_sw_wayside():
    print("\n[2/5] 🔧 Launching SW Wayside Controller (Blocks 0-69)...")
    try:
        from track_controller.New_SW_Code import sw_wayside_controller
        from track_controller.New_SW_Code import sw_vital_check
        from track_controller.New_SW_Code.sw_wayside_controller_ui import sw_wayside_controller_ui
        
        vital = sw_vital_check.sw_vital_check()
        controller = sw_wayside_controller.sw_wayside_controller(
            vital, 
            "Green_Line_PLC_XandLup.py"
        )
        ui = sw_wayside_controller_ui(controller)
        ui.title("SW Wayside Controller - Blocks 0-69")
        ui.geometry("1200x800")
        ui.mainloop()
    except Exception as e:
        print(f"❌ SW Wayside failed to launch: {e}")
        import traceback
        traceback.print_exc()

# ============================================================================
# 3. HW Wayside Controller (Blocks 70-143)
# ============================================================================
def launch_hw_wayside():
    print("\n[3/5] ⚙️  Launching HW Wayside Controller (Blocks 70-143)...")
    try:
        # Add hw_wayside to path
        hw_dir = os.path.join(project_root, "track_controller", "hw_wayside")
        if hw_dir not in sys.path:
            sys.path.insert(0, hw_dir)
        
        from track_controller.hw_wayside.hw_wayside_controller import HW_Wayside_Controller
        from track_controller.hw_wayside.hw_wayside_controller_ui import HW_Wayside_Controller_UI
        from track_controller.hw_wayside.hw_display import HW_Display
        
        blocks_70_143 = list(range(70, 144))
        
        # Create controller
        controller = HW_Wayside_Controller(
            wayside_id="B",
            block_ids=blocks_70_143
        )
        
        # Load PLC program
        controller.load_plc("Green_Line_PLC_XandLdown.py")
        
        # Create UI
        root = tk.Tk()
        root.title("HW Wayside Controller - Blocks 70-143")
        root.geometry("1200x800")
        
        display = HW_Display()
        ui = HW_Wayside_Controller_UI(root, controller, display)
        
        # Start controller's train loop
        controller.start_trains(period_s=1.0)
        
        root.mainloop()
    except Exception as e:
        print(f"❌ HW Wayside failed to launch: {e}")
        import traceback
        traceback.print_exc()

# ============================================================================
# 4. Train Model
# ============================================================================
def launch_train_model():
    print("\n[4/5] 🚆 Launching Train Model...")
    try:
        from Train_Model.train_model_ui import TrainModelUI
        train_ui = TrainModelUI()
        train_ui.run()
    except Exception as e:
        print(f"❌ Train Model failed to launch: {e}")
        import traceback
        traceback.print_exc()

# ============================================================================
# 5. Train Controllers (Software - handles Kp/Ki)
# ============================================================================
def launch_train_controllers():
    print("\n[5/5] 🎮 Launching Train Controllers...")
    try:
        from train_controller.train_manager import TrainManagerUI
        manager_ui = TrainManagerUI()
        manager_ui.run()
    except Exception as e:
        print(f"❌ Train Controllers failed to launch: {e}")
        import traceback
        traceback.print_exc()

# ============================================================================
# Main Launcher
# ============================================================================
def main():
    print("\n📦 Starting all components in separate threads...\n")
    
    # Launch each component in its own thread
    threads = [
        threading.Thread(target=launch_ctc, daemon=True, name="CTC"),
        threading.Thread(target=launch_sw_wayside, daemon=True, name="SW_Wayside"),
        threading.Thread(target=launch_hw_wayside, daemon=True, name="HW_Wayside"),
        threading.Thread(target=launch_train_model, daemon=True, name="Train_Model"),
        threading.Thread(target=launch_train_controllers, daemon=True, name="Train_Controllers"),
    ]
    
    for thread in threads:
        thread.start()
        print(f"✅ Started: {thread.name}")
    
    print("\n" + "=" * 60)
    print("🎉 ALL SYSTEMS LAUNCHED!")
    print("=" * 60)
    print("\n📋 Testing Instructions:")
    print("1. Wait for all 5 windows to open")
    print("2. In Train Controller: Set Kp/Ki for Train 1 (e.g., Kp=5000, Ki=100)")
    print("3. In CTC: Dispatch Train 1 to 'Edgebrook' station")
    print("4. Watch train travel through SW Wayside (blocks 0-69)")
    print("5. 🎯 OBSERVE HANDOFF at block 70 to HW Wayside")
    print("6. Verify:")
    print("   - Speed stays correct (not super high)")
    print("   - Authority values are correct")
    print("   - Block 70 shows occupied on HW UI")
    print("   - Train stops smoothly at station")
    print("\n" + "=" * 60)
    
    # Keep main thread alive
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 System shutdown requested")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
