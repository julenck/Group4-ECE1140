import tkinter as tk
from tkinter import ttk 
import os
import sys
import threading

# Add parent directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import track_controller.New_SW_Code.sw_wayside_controller_ui as wayside_sw
import ctc.ctc_ui_temp as ctc_ui
from train_controller.train_manager import TrainManagerUI

# Import hardware wayside components
try:
    from track_controller.hw_wayside.hw_wayside_controller import HW_Wayside_Controller
    from track_controller.hw_wayside.hw_wayside_controller_ui import HW_Wayside_Controller_UI
    from track_controller.hw_wayside.hw_vital_check import HW_Vital_Check
    HW_WAYSIDE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Hardware wayside not available: {e}")
    HW_WAYSIDE_AVAILABLE = False

def run_ctc_ui(): 
    dispatcher_ui = ctc_ui.CTCUI()
    dispatcher_ui.run()

def run_wayside_sw_ui_1(): 
    vital1 = wayside_sw.sw_vital_check.sw_vital_check()
    controller1 = wayside_sw.sw_wayside_controller.sw_wayside_controller(vital1, os.path.join("track_controller", "New_SW_Code", "Green_Line_PLC_XandLup.py"))
    ui1 = wayside_sw.sw_wayside_controller_ui(controller1)

    ui1.title("Green Line Wayside Controller - X and L Up (Blocks 0-73, 144-150)")
    ui1.geometry("1200x800")

    ui1.mainloop()

def run_wayside_sw_ui_2():
    vital2 = wayside_sw.sw_vital_check.sw_vital_check()
    controller2 = wayside_sw.sw_wayside_controller.sw_wayside_controller(vital2, os.path.join("track_controller", "New_SW_Code", "Green_Line_PLC_XandLdown.py"))
    ui2 = wayside_sw.sw_wayside_controller_ui(controller2)

    ui2.title("Green Line Wayside Controller - X and L Down (Blocks 70-143)")
    ui2.geometry("1200x800")
    
    ui2.mainloop()

def run_wayside_hw_ui_2():
    """Launch Hardware Wayside Controller 2 (X and L Down).
    
    ONLY runs on Raspberry Pi when SERVER_URL environment variable is set.
    On PC, falls back to SW wayside.
    """
    # Get server URL from environment variable
    server_url = os.environ.get('SERVER_URL', None)
    
    # If SERVER_URL is not set, we're on PC - use SW wayside instead
    if not server_url:
        print("[Wayside 2] No SERVER_URL set, using SW wayside controller on PC")
        run_wayside_sw_ui_2()
        return
    
    # SERVER_URL is set - we're on Raspberry Pi, use HW wayside
    if not HW_WAYSIDE_AVAILABLE:
        print("ERROR: Hardware wayside components not available but SERVER_URL is set!")
        print("       Falling back to SW wayside.")
        run_wayside_sw_ui_2()
        return
    
    print(f"[Wayside 2] SERVER_URL detected: {server_url}")
    print(f"[Wayside 2] Launching HARDWARE wayside controller [SERVER MODE]")
    
    # Define blocks managed by this wayside (70-143)
    blocks_70_143 = list(range(70, 144))
    
    # Create hardware wayside controller with API support
    controller = HW_Wayside_Controller(
        wayside_id="B",  # Wayside B (2nd wayside)
        block_ids=blocks_70_143,
        server_url=server_url,
        timeout=5.0
    )
    
    # Create Tk window
    root = tk.Tk()
    
    # Create UI
    ui = HW_Wayside_Controller_UI(
        root=root,
        controller=controller,
        title="Hardware Wayside B - X and L Down (Blocks 70-143) [SERVER MODE]"
    )
    ui.pack(fill=tk.BOTH, expand=True)
    
    # Start mainloop
    root.mainloop()

def main():
    # Start CTC UI in thread
    ctc_thread = threading.Thread(target=run_ctc_ui)
    ctc_thread.daemon = True
    ctc_thread.start() 

    # Start Wayside UI 1 (X and L Up) in thread
    wayside_thread_1 = threading.Thread(target=run_wayside_sw_ui_1)
    wayside_thread_1.daemon = True
    wayside_thread_1.start()

    # NOTE: Wayside 2 runs on separate Raspberry Pi
    # Use run_wayside_hw_ui_2() on Raspberry Pi with SERVER_URL set

    wayside_thread_2 = threading.Thread(target=run_wayside_hw_ui_2)
    wayside_thread_2.daemon = True
    wayside_thread_2.start()


    # Create a simple status window
    root = tk.Tk()
    root.title("System Status")
    root.geometry("350x250")

    info_text = ("Distributed System Status:\n\n"
                "• CTC Dispatcher [PC]\n"
                "• Wayside Controller 1 [SW] (Blocks 0-73, 144-150) [PC]\n"
                "• Wayside Controller 2 [HW] (Blocks 70-143) [Raspberry Pi]\n"
                "• Train Controllers [HW] [Raspberry Pi]")

    label = ttk.Label(root, text=info_text, justify=tk.CENTER)
    label.pack(expand=True, padx=10, pady=10)
    
    # Start the main loop
    root.mainloop()

if __name__ == "__main__":
    main()

