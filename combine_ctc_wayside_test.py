import tkinter as tk
from tkinter import ttk 
import os
import sys
import subprocess
import json

# Add parent directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Add Track_Model directory to path for its internal imports
track_model_dir = os.path.join(current_dir, "Track_Model")
sys.path.append(track_model_dir)

import track_controller.New_SW_Code.sw_wayside_controller_ui as wayside_sw
import ctc.ctc_ui as ctc_ui
import Track_Model.track_model_UI as track_model_ui

def clear_json_files():
    """Clear all JSON communication files to start fresh."""
    json_files = {
        "ctc_data.json": os.path.join(current_dir, "ctc", "ctc_data.json"),
        "ctc_track_controller.json": os.path.join(current_dir, "ctc_track_controller.json"),
        "ctc_ui_inputs.json": os.path.join(current_dir, "ctc", "ctc_ui_inputs.json"),
    }
    
    # Initialize with empty/default structures
    default_data = {
        "ctc_data.json": {
            "Dispatcher": {
                "Trains": {}
            }
        },
        "ctc_track_controller.json": {
            "Trains": {
                "Train 1": {
                    "Active": 0,
                    "Suggested Authority": 0,
                    "Suggested Speed": 0,
                    "Train Position": 0,
                    "Train State": "Stopped"
                }
            }
        },
        "ctc_ui_inputs.json": {}
    }
    
    for filename, filepath in json_files.items():
        try:
            with open(filepath, 'w') as f:
                json.dump(default_data[filename], f, indent=4)
            print(f"[Setup] Cleared {filename}")
        except Exception as e:
            print(f"[Setup] Warning: Could not clear {filename}: {e}")

def main():
    # Clear JSON files before starting
    print("[Setup] Clearing previous session data...")
    clear_json_files()
    
    # Get the Python executable path
    python_exe = sys.executable
    
    # Start each UI in a separate process
    ctc_process = subprocess.Popen([python_exe, "-c", 
        "import sys; sys.path.append(r'" + current_dir + "'); "
        "from ctc.ctc_ui import CTCUI; "
        "ui = CTCUI(); ui.run()"])
    
    # Wayside Controller 1 - Handles blocks 0-73 and 144-151 (X and L Up)
    wayside1_process = subprocess.Popen([python_exe, "-c",
        "import sys; sys.path.append(r'" + current_dir + "'); "
        "from track_controller.New_SW_Code import sw_vital_check, sw_wayside_controller, sw_wayside_controller_ui; "
        "vital = sw_vital_check.sw_vital_check(); "
        "controller = sw_wayside_controller.sw_wayside_controller(vital, r'Green_Line_PLC_XandLup.py'); "
        "ui = sw_wayside_controller_ui.sw_wayside_controller_ui(controller); "
        "ui.title('Green Line Wayside Controller 1 - X and L Up'); "
        "ui.geometry('1200x800'); "
        "ui.mainloop()"])
    
    # Wayside Controller 2 - Handles blocks 70-146 (X and L Down)
    wayside2_process = subprocess.Popen([python_exe, "-c",
        "import sys; sys.path.append(r'" + current_dir + "'); "
        "from track_controller.New_SW_Code import sw_vital_check, sw_wayside_controller, sw_wayside_controller_ui; "
        "vital = sw_vital_check.sw_vital_check(); "
        "controller = sw_wayside_controller.sw_wayside_controller(vital, r'Green_Line_PLC_XandLdown.py'); "
        "ui = sw_wayside_controller_ui.sw_wayside_controller_ui(controller); "
        "ui.title('Green Line Wayside Controller 2 - X and L Down'); "
        "ui.geometry('1200x800'); "
        "ui.mainloop()"])
    
    track_model_process = subprocess.Popen([python_exe, "-c",
        "import sys; sys.path.append(r'" + current_dir + "'); "
        "sys.path.append(r'" + track_model_dir + "'); "
        "from Track_Model.track_model_UI import TrackModelUI; "
        "ui = TrackModelUI(); ui.mainloop()"])

    root = tk.Tk()
    root.title("Combined UI Process Manager")
    root.geometry("400x250")

    info_text = "All UIs Running in Separate Processes\n\nCTC, 2 Wayside Controllers, and Track Model\nare running independently.\n\nWayside 1: Blocks 0-73, 144-151\nWayside 2: Blocks 70-146"

    label = ttk.Label(root, text=info_text, justify=tk.CENTER, padding=20)
    label.pack(expand=True)
    
    def on_closing():
        # Terminate all subprocesses when closing
        ctc_process.terminate()
        wayside1_process.terminate()
        wayside2_process.terminate()
        track_model_process.terminate()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()

