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

def run_ctc_ui(): 
    dispatcher_ui = ctc_ui.CTCUI()
    dispatcher_ui.mainloop()

def run_wayside_sw_ui(): 
    vital1 = wayside_sw.sw_vital_check.sw_vital_check()
    controller1 = wayside_sw.sw_wayside_controller.sw_wayside_controller(vital1,"track_controller\\New_SW_Code\\Green_Line_PLC_XandLup.py")
    ui1 = wayside_sw.sw_wayside_controller_ui(controller1)

    ui1.title("Green Line Wayside Controller - X and L Up")
    ui1.geometry("1200x800")


    vital2 = wayside_sw.sw_vital_check.sw_vital_check()
    controller2 = wayside_sw.sw_wayside_controller.sw_wayside_controller(vital2,"track_controller\\New_SW_Code\\Green_Line_PLC_XandLdown.py")

    ui1.mainloop()

def main():
    ctc_thread = threading.Thread(target=run_ctc_ui)
    ctc_thread.daemon = True
    ctc_thread.start() 

    wayside_thread = threading.Thread(target=run_wayside_sw_ui)
    wayside_thread.daemon = True
    wayside_thread.start() 

    root = tk.Tk()
    root.title("Train Controller UI Manager")
    root.geometry("300x150")

    info_text = "CTC and Wayside UIs Running"

    label = ttk.Label(root, text=info_text, justify=tk.CENTER)
    label.pack(expand=True, padx=10, pady=10)
    
    # Start the main loop
    root.mainloop()

if __name__ == "__main__":
    main()

