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

def main():
    # Start CTC UI in thread
    ctc_thread = threading.Thread(target=run_ctc_ui)
    ctc_thread.daemon = True
    ctc_thread.start() 

    # Start Wayside UI 1 (X and L Up) in thread
    wayside_thread_1 = threading.Thread(target=run_wayside_sw_ui_1)
    wayside_thread_1.daemon = True
    wayside_thread_1.start() 

    # Start Wayside UI 2 (X and L Down) in thread
    wayside_thread_2 = threading.Thread(target=run_wayside_sw_ui_2)
    wayside_thread_2.daemon = True
    wayside_thread_2.start()

    # Create a simple status window
    root = tk.Tk()
    root.title("System Status")
    root.geometry("300x200")

    info_text = "All Systems Running:\n\n• CTC Dispatcher\n• Wayside Controller 1 (Blocks 0-73, 144-150)\n• Wayside Controller 2 (Blocks 70-143)"

    label = ttk.Label(root, text=info_text, justify=tk.CENTER)
    label.pack(expand=True, padx=10, pady=10)
    
    # Start the main loop
    root.mainloop()

if __name__ == "__main__":
    main()

