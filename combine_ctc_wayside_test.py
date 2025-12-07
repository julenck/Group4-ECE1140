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

# Import HW wayside
sys.path.insert(0, os.path.join(current_dir, "track_controller", "hw_wayside"))
import hw_main as hw_wayside

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

def run_wayside_hw_ui():
    """Run HW Wayside Controller (replaces SW Wayside 2)"""
    hw_wayside.main()

def main():
    # Start CTC UI in thread
    ctc_thread = threading.Thread(target=run_ctc_ui)
    ctc_thread.daemon = True
    ctc_thread.start() 

    # Start Wayside UI 1 (X and L Up) in thread
    wayside_thread_1 = threading.Thread(target=run_wayside_sw_ui_1)
    wayside_thread_1.daemon = True
    wayside_thread_1.start() 

    # Start HW Wayside UI (X and L Down) in thread
    wayside_thread_hw = threading.Thread(target=run_wayside_hw_ui)
    wayside_thread_hw.daemon = True
    wayside_thread_hw.start()

    # Create a simple status window
    root = tk.Tk()
    root.title("System Status")
    root.geometry("300x200")

    info_text = "All Systems Running:\n\n• CTC Dispatcher\n• SW Wayside 1 (Blocks 0-73, 144-150)\n• HW Wayside B (Blocks 70-143)"

    label = ttk.Label(root, text=info_text, justify=tk.CENTER)
    label.pack(expand=True, padx=10, pady=10)
    
    # Start the main loop
    root.mainloop()

if __name__ == "__main__":
    main()

