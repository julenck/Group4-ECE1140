#!/usr/bin/env python3
"""
Complete System Launcher for Handoff Testing
Launches: CTC, SW Wayside, HW Wayside, Train Model, Train Controllers
All in the MAIN thread to avoid Tkinter threading issues.

Usage on Pi or Mac:
    cd "/path/to/Group4-ECE1140 CODE"
    python3 launch_full_system_test.py
"""

import os
import sys
import tkinter as tk
from tkinter import ttk

# Ensure we're in project root
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("=" * 60)
print("🚂 LAUNCHING COMPLETE TRAIN SYSTEM FOR HANDOFF TEST")
print("=" * 60)
print("Note: All windows will open sequentially in main thread")
print("=" * 60)

# ============================================================================
# Create all components (non-blocking setup)
# ============================================================================
def setup_all_components():
    """Set up all controllers and UIs in Toplevel windows"""
    
    components = {}
    
    # Create main root window (hidden)
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    try:
        # 1. CTC
        print("\n[1/5] 🎛️  Setting up CTC...")
        from ctc.ctc_ui_temp import CTCUI
        components['ctc'] = CTCUI()
        components['ctc'].root.title("CTC Dispatcher")
        print("✅ CTC ready")
    except Exception as e:
        print(f"❌ CTC failed: {e}")
    
    try:
        # 2. SW Wayside
        print("\n[2/5] 🔧 Setting up SW Wayside...")
        from track_controller.New_SW_Code import sw_wayside_controller
        from track_controller.New_SW_Code import sw_vital_check
        from track_controller.New_SW_Code.sw_wayside_controller_ui import sw_wayside_controller_ui
        
        vital = sw_vital_check.sw_vital_check()
        sw_controller = sw_wayside_controller.sw_wayside_controller(vital, "Green_Line_PLC_XandLup.py")
        components['sw_wayside'] = sw_wayside_controller_ui(sw_controller)
        components['sw_wayside'].title("SW Wayside - Blocks 0-69")
        components['sw_wayside'].geometry("1000x700+0+0")
        print("✅ SW Wayside ready")
    except Exception as e:
        print(f"❌ SW Wayside failed: {e}")
    
    try:
        # 3. HW Wayside
        print("\n[3/5] ⚙️  Setting up HW Wayside...")
        hw_dir = os.path.join(project_root, "track_controller", "hw_wayside")
        if hw_dir not in sys.path:
            sys.path.insert(0, hw_dir)
        
        from track_controller.hw_wayside.hw_wayside_controller import HW_Wayside_Controller
        from track_controller.hw_wayside.hw_wayside_controller_ui import HW_Wayside_Controller_UI
        
        hw_controller = HW_Wayside_Controller("B", list(range(70, 144)))
        hw_controller.load_plc("Green_Line_PLC_XandLdown.py")
        hw_controller.start_trains(period_s=1.0)
        
        hw_window = tk.Toplevel(root)
        hw_window.geometry("1000x700+1020+0")
        components['hw_wayside_ui'] = HW_Wayside_Controller_UI(hw_window, hw_controller, "HW Wayside - Blocks 70-143")
        components['hw_wayside_ui'].pack(fill='both', expand=True)
        components['hw_wayside'] = hw_controller
        print("✅ HW Wayside ready")
    except Exception as e:
        print(f"❌ HW Wayside failed: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        # 4. Train Model
        print("\n[4/5] 🚆 Setting up Train Model...")
        from Train_Model.train_model_ui import TrainModelUI
        components['train_model'] = TrainModelUI()
        components['train_model'].title("Train Model")
        components['train_model'].geometry("900x600+0+740")
        print("✅ Train Model ready")
    except Exception as e:
        print(f"❌ Train Model failed: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        # 5. Train Controllers
        print("\n[5/5] 🎮 Setting up Train Controllers...")
        from train_controller.train_manager import TrainManagerUI
        components['train_controller'] = TrainManagerUI()
        components['train_controller'].title("Train Controllers")
        components['train_controller'].geometry("900x600+1020+740")
        print("✅ Train Controllers ready")
    except Exception as e:
        print(f"❌ Train Controllers failed: {e}")
        import traceback
        traceback.print_exc()
    
    return root, components

# ============================================================================
# Main Launcher
# ============================================================================
def main():
    print("\n📦 Setting up all components in main thread...\n")
    
    root, components = setup_all_components()
    
    print("\n" + "=" * 60)
    print("🎉 ALL SYSTEMS READY!")
    print("=" * 60)
    print(f"Launched {len(components)} components")
    print("\n📋 Testing Instructions:")
    print("1. All windows should now be visible")
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
    
    # Start main event loop
    root.mainloop()

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
