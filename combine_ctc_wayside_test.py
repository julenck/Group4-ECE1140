import tkinter as tk
from tkinter import ttk 
import os
import sys
import threading
import subprocess
import time

# Add parent directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import track_controller.New_SW_Code.sw_wayside_controller_ui as wayside_sw
import ctc.ctc_ui_temp as ctc_ui
from train_controller.train_manager import TrainManagerUI
import json

def reset_json_files():
    """Reset JSON state files to default values for a clean startup."""
    print("[Main] Resetting JSON state files...")
    
    # Reset train_states.json to default empty state
    train_states_default = {
        "commanded_speed": 0.0,
        "commanded_authority": 0.0,
        "speed_limit": 0.0,
        "train_velocity": 0.0,
        "current_station": "",
        "next_stop": "",
        "station_side": "",
        "train_temperature": 0.0,
        "train_model_engine_failure": False,
        "train_model_signal_failure": False,
        "train_model_brake_failure": False,
        "train_controller_engine_failure": False,
        "train_controller_signal_failure": False,
        "train_controller_brake_failure": False,
        "beacon_read_blocked": False,
        "manual_mode": False,
        "driver_velocity": 0.0,
        "service_brake": False,
        "right_door": False,
        "left_door": False,
        "interior_lights": False,
        "exterior_lights": False,
        "set_temperature": 70.0,
        "temperature_up": False,
        "temperature_down": False,
        "announcement": "",
        "announce_pressed": False,
        "emergency_brake": False,
        "kp": None,
        "ki": None,
        "engineering_panel_locked": False,
        "power_command": 0.0
    }
    
    train_states_path = os.path.join("train_controller", "data", "train_states.json")
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(train_states_path), exist_ok=True)
            # Write with explicit flush and close
            with open(train_states_path, 'w') as f:
                json.dump(train_states_default, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            print(f"[Main] Reset {train_states_path}")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"[Main] Retry {attempt + 1}/{max_retries} resetting train_states.json...")
                time.sleep(0.5)
            else:
                print(f"[Main] Warning: Could not reset train_states.json: {e}")
    
    # Reset ctc_track_controller.json - all trains start at position 0 (yard)
    ctc_track_default = {
        "Trains": {
            "Train 1": {"Active": 0, "Suggested Speed": 0, "Suggested Authority": 0, "Train Position": 0, "Train State": 0},
            "Train 2": {"Active": 0, "Suggested Speed": 0, "Suggested Authority": 0, "Train Position": 0, "Train State": 0},
            "Train 3": {"Active": 0, "Suggested Speed": 0, "Suggested Authority": 0, "Train Position": 0, "Train State": 0},
            "Train 4": {"Active": 0, "Suggested Speed": 0, "Suggested Authority": 0, "Train Position": 0, "Train State": 0},
            "Train 5": {"Active": 0, "Suggested Speed": 0, "Suggested Authority": 0, "Train Position": 0, "Train State": 0}
        },
        "Block Closure": [],
        "Switch Suggestion": [],
        "Block Failure": [],
        "Gates": [],
        "Lights": [],
        "Switch Actual": []
    }
    
    ctc_track_path = "ctc_track_controller.json"
    try:
        with open(ctc_track_path, 'w') as f:
            json.dump(ctc_track_default, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        print(f"[Main] Reset {ctc_track_path}")
    except Exception as e:
        print(f"[Main] Warning: Could not reset ctc_track_controller.json: {e}")
    
    # Small delay to ensure file system releases locks
    time.sleep(0.5)
    print("[Main] JSON reset complete")

def start_api_server():
    """Start the unified API server in a separate process."""
    print("[Main] Starting Unified API Server...")
    print("[Main] This may take a few seconds...")
    
    # Start server with visible output so we can see any errors
    server_process = subprocess.Popen(
        [sys.executable, "start_unified_server.py"],
        # Don't capture output - let it print to console
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
    )
    
    # Wait longer for server to start and check if it's running
    print("[Main] Waiting for server to start...")
    time.sleep(5)  # Give it more time
    
    # Check if process is still running
    if server_process.poll() is not None:
        print("[Main] ERROR: Server process exited unexpectedly!")
        print("[Main] Check the server console window for errors")
        return None
    
    print("[Main] API Server started successfully")
    return server_process

def run_ctc_ui(server_url): 
    dispatcher_ui = ctc_ui.CTCUI(server_url=server_url)
    dispatcher_ui.run()

def run_wayside_sw_ui_1(server_url): 
    vital1 = wayside_sw.sw_vital_check.sw_vital_check()
    controller1 = wayside_sw.sw_wayside_controller.sw_wayside_controller(
        vital1,
        "track_controller\\New_SW_Code\\Green_Line_PLC_XandLup.py",
        server_url=server_url,
        wayside_id=1
    )
    ui1 = wayside_sw.sw_wayside_controller_ui(controller1)

    ui1.title("Green Line Wayside Controller - X and L Up (Blocks 0-73, 144-150) - Remote Mode")
    ui1.geometry("1200x800")

    ui1.mainloop()

def run_wayside_sw_ui_2(server_url):
    vital2 = wayside_sw.sw_vital_check.sw_vital_check()
    controller2 = wayside_sw.sw_wayside_controller.sw_wayside_controller(
        vital2,
        "track_controller\\New_SW_Code\\Green_Line_PLC_XandLdown.py",
        server_url=server_url,
        wayside_id=2
    )
    ui2 = wayside_sw.sw_wayside_controller_ui(controller2)

    ui2.title("Green Line Wayside Controller - X and L Down (Blocks 70-143) - Remote Mode")
    ui2.geometry("1200x800")
    
    ui2.mainloop()

def main():
    # Reset JSON files for clean startup
    print("=" * 80)
    print("  INTEGRATED RAILWAY SYSTEM TEST")
    print("=" * 80)
    reset_json_files()
    
    # Start API server
    server_process = start_api_server()
    
    if server_process is None:
        print("\n" + "=" * 80)
        print("  ERROR: Server failed to start!")
        print("=" * 80)
        print("\nPlease check:")
        print("1. Flask is installed: pip install flask flask-cors")
        print("2. unified_api_server.py exists in current directory")
        print("3. No other process is using port 5000")
        print("\nPress Enter to exit...")
        input()
        return
    
    server_url = "http://localhost:5000"
    
    print(f"\n[Main] Server URL: {server_url}")
    print("[Main] Starting UI components...")
    
    # Start CTC UI in thread
    ctc_thread = threading.Thread(target=run_ctc_ui, args=(server_url,))
    ctc_thread.daemon = True
    ctc_thread.start() 

    # Start Wayside UI 1 (X and L Up) in thread
    wayside_thread_1 = threading.Thread(target=run_wayside_sw_ui_1, args=(server_url,))
    wayside_thread_1.daemon = True
    wayside_thread_1.start() 

    # Start Wayside UI 2 (X and L Down) in thread
    wayside_thread_2 = threading.Thread(target=run_wayside_sw_ui_2, args=(server_url,))
    wayside_thread_2.daemon = True
    wayside_thread_2.start()

    # Create a simple status window
    root = tk.Tk()
    root.title("System Status")
    root.geometry("400x250")

    info_text = """All Systems Running:

• Unified API Server (http://localhost:5000)
• CTC Dispatcher (Remote Mode)
• Wayside Controller 1 (Remote Mode)
  Blocks 0-73, 144-150
• Wayside Controller 2 (Remote Mode)
  Blocks 70-143

All components connected via REST API"""

    label = ttk.Label(root, text=info_text, justify=tk.CENTER, font=("Arial", 10))
    label.pack(expand=True, padx=20, pady=20)
    
    def on_closing():
        print("\n[Main] Shutting down...")
        if server_process:
            server_process.terminate()
            print("[Main] Server terminated")
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Start the main loop
    root.mainloop()

if __name__ == "__main__":
    main()

