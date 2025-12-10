"""
Handles HW wayside controller initialization, GPIO switch control,
JSON I/O for CTC/track communication, and periodic polling loop.

Author: Oliver Kettelson-Belinkie, 2025
"""

from __future__ import annotations
import os
import sys
import argparse
os.environ["TK_SILENCE_DEPRECATION"] = "1"
import tkinter as tk
from typing import List, Dict
import json
import tempfile

# Ensure we're in project root
_current_dir = os.path.dirname(os.path.abspath(__file__))

if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from hw_wayside_controller import HW_Wayside_Controller
from hw_display import HW_Display
from hw_wayside_controller_ui import HW_Wayside_Controller_UI

GPIO_SWITCH_PIN = 17  # Physical switch GPIO pin

# Try to import lgpio for GPIO handling
try:
    import lgpio

except Exception:
    lgpio = None  # type: ignore

class PhysicalSwitch:
    """
    GPIO switch handler for Raspberry Pi hardware switches.

    Fail-safes on non-Pi systems
    """

    def __init__(self, pin: int = GPIO_SWITCH_PIN):
       
        self.pin = pin
        self.chip = None
        self.last_read_state = None

        if lgpio:
            try:
                self.chip = lgpio.gpiochip_open(4)
                lgpio.gpio_claim_input(self.chip, self.pin, lgpio.SET_PULL_UP)

            except Exception:
                self.chip = None
    
    def present(self) -> bool:      # Check if switch hardware is present
        
        return self.chip is not None

    def read_state(self) -> str:        # Read current switch state ('0' or '1')
      
        if not self.chip:
            return None
        
        try:
            state = lgpio.gpio_read(self.chip, self.pin)
            return "1" if state == 1 else "0"
        
        except Exception:
            return None
    
    def check_for_change(self) -> str:          # Check for state change since last read
        
        current = self.read_state()

        if current is None:
            return None
        
        if self.last_read_state is None:
            self.last_read_state = current
            return None
        
        if current != self.last_read_state:
            self.last_read_state = current
            return current
        
        return None

_physical_switch = PhysicalSwitch()

def apply_physical_switch(controller: HW_Wayside_Controller) -> None:
    """Apply physical switch state to selected block."""
    if not _physical_switch.present():
        return
    
    new_state = _physical_switch.check_for_change()

    if not new_state:
        return
    
    if not controller.maintenance_active:
        print("[HW Main] Physical switch ignored - maintenance mode not active")
        return
    
    selected = controller.get_selected_block()

    if not selected or not controller.has_switch(selected):
        print(f"[HW Main] Physical switch ignored - no valid block selected (selected={selected})")
        return
    
    success, reason = controller.request_switch_change(selected, new_state)
    if success:
        print(f"[HW Main] Physical switch applied to block {selected}: state={new_state}")
    else:
        print(f"[HW Main] Physical switch rejected for block {selected}: {reason}")


# Module-level constants and paths (Matching SW behavior)
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# hw_wayside -> track_controller -> project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_CURRENT_DIR))

# CTC (shared with SW wayside)
CTC_IN_FILE = os.path.join(_PROJECT_ROOT, "ctc_track_controller.json")
CTC_OUT_FILE   = os.path.join(_PROJECT_ROOT, "hw_wayside_to_ctc.json")         # CTC feedback 
TRACK_COMM_FILE = os.path.join(_PROJECT_ROOT, "track_controller", "New_SW_Code", "track_to_wayside.json")  # Shared state between controllers

POLL_MS = 500
ENABLE_LOCAL_AUTH_DECAY = True  # Locally decrement authority based on speed


def _read_ctc_json() -> dict:
    
    defaults = {
        "speed_mph": 0.0,
        "authority_yards": 0,
        "emergency": False,
        "occupied_blocks": [],
        "closed_blocks": [],
    }

    if not os.path.exists(CTC_IN_FILE):
        return defaults

    try:
        with open(CTC_IN_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f) or {}

    except Exception as e:
        print(f"[WARN] JSON read failed: {e}")
        return defaults

    trains = raw.get("Trains", {}) or {}

    occupied: list[int] = []
    speed = 0.0
    auth = 0

    for tid, tinfo in trains.items():

        # Active flag
        active_val = tinfo.get("Active", 0)
        try:
            active = int(active_val) == 1

        except (TypeError, ValueError):
            active = False

        if not active:
            continue

        # Train position -> an occupied block
        pos_val = tinfo.get("Train Position", "")
        try:
            pos_int = int(pos_val)

        except (TypeError, ValueError):
            pos_int = None

        if pos_int is not None:
            occupied.append(pos_int)

        # Take speed/auth from the *first* active train
        if speed == 0.0 and auth == 0:
            s_val = tinfo.get("Suggested Speed", 0) or 0

            # Handle typo "Suggestd Authority" as well
            a_val = (tinfo.get("Suggested Authority")
                     or tinfo.get("Suggestd Authority")
                     or 0)
            try:
                speed = float(s_val)

            except (TypeError, ValueError):
                speed = 0.0

            try:
                auth = int(a_val)

            except (TypeError, ValueError):
                auth = 0

    defaults["speed_mph"] = speed
    defaults["authority_yards"] = auth
    defaults["occupied_blocks"] = occupied
    defaults["closed_blocks"] = list(raw.get("Block Closure", []))

    return defaults


def _safe_read_track_json() -> dict:        # Matching SW behavior
   
    if not os.path.exists(TRACK_COMM_FILE):
        return {}
    
    try:
        with open(TRACK_COMM_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
        
    except Exception as e:
        print(f"[WARN] Track file read failed: {e}")
        return {}

def _atomic_write_track_json(patch: dict) -> None:      # Write to track communication JSON file
   
    try:
        base = _safe_read_track_json()
        base.update(patch or {})
        d = os.path.dirname(TRACK_COMM_FILE) or "."

        with tempfile.NamedTemporaryFile("w", delete=False, dir=d, encoding="utf-8") as tmp:
            json.dump(base, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = tmp.name

        os.replace(tmp_path, TRACK_COMM_FILE)

    except Exception as e:
        print(f"[WARN] Track file write failed: {e}")

def _make_vital_in(raw: dict) -> dict:      # Create vital input dict from raw CTC data
   
    return {
        "speed_mph": float(raw.get("speed_mph", 0)),
        "authority_yards": int(raw.get("authority_yards", 0)),
        "emergency": bool(raw.get("emergency", False)),
        "occupied_blocks": list(raw.get("occupied_blocks", [])),
        "closed_blocks": list(raw.get("closed_blocks", [])),
    }

def _write_ctc_occupancy(occupancy: List[int]) -> None:     # Write occupancy array back to CTC JSON
    
    try:
        base: Dict = {}

        if os.path.exists(CTC_IN_FILE):
            with open(CTC_IN_FILE, "r", encoding="utf-8") as f:
                base = json.load(f) or {}

        base["G-Occupancy"] = list(occupancy)

        with open(CTC_OUT_FILE, "w", encoding="utf-8") as f:
            json.dump(base, f, indent=2)

    except Exception as e:
        print(f"[WARN] CTC occupancy write failed: {e}")


def _discover_block_count() -> int:

    return 152

def _discover_blocks_B() -> List[str]:
    """
    Block allocation:
    - SW Wayside 1 (XandLup): 0-69, 144-150
    - HW Wayside B (XandLdown): 70-143
    """
    n = _discover_block_count()

    def clamp_range(start: int, end_excl: int) -> List[int]:
       
        start = max(0, start)
        end_excl = min(n, end_excl)
        return list(range(start, end_excl))

    # Managed blocks: 70-143 
    down = clamp_range(70, 144) 
    return [str(i) for i in down]


def _poll_json_loop(root, controllers: List[HW_Wayside_Controller], uis: List[HW_Wayside_Controller_UI], blocks_by_ws: List[List[str]]):
    """
    Reads CTC feed, runs vital checks and PLC logic per wayside,
    updates UIs, and writes outputs (matching SW behavior).
    """

    raw = _read_ctc_json()
    vital_in = _make_vital_in(raw)

    # Read shared track state
    track_snapshot = _safe_read_track_json()

    merged_status = {"waysides": {}}

    for controller, ui, blocks in zip(controllers, uis, blocks_by_ws):

        controller.apply_vital_inputs(blocks, vital_in)

        if ENABLE_LOCAL_AUTH_DECAY:
            controller.tick_authority_decay()

        # Apply track snapshot
        controller.apply_track_snapshot(track_snapshot, limit_blocks=blocks)

        controller.tick_train_progress()
        
        # Poll physical switch
        try:
            apply_physical_switch(controller)

        except Exception:
            pass

        status = controller.assess_safety(blocks, vital_in)

        # identify this controller in output
        ws_id = getattr(controller, "wayside_id", "X")
        merged_status["waysides"][ws_id] = status

        # Write commanded arrays to shared track file (like SW does)
        n_total = _discover_block_count()
        cmd = controller.build_commanded_arrays(n_total)
        _atomic_write_track_json(cmd)
        
        ui._push_to_display()

    # Write back to CTC JSON (occupancy)
    n_total = _discover_block_count()
    combined_occ = [0] * n_total

    for controller in controllers:

        occ = controller.build_occupancy_array(n_total)
        combined_occ = [max(a, b) for a, b in zip(combined_occ, occ)]

    _write_ctc_occupancy(combined_occ)

    # Let each controller optionally write wayside->train outputs
    for controller in controllers:
        try:
            controller.write_wayside_to_train()

        except Exception:
            pass

    root.after(POLL_MS, _poll_json_loop, root, controllers, uis, blocks_by_ws)


def main() -> None:
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Hardware Wayside Controller")
    parser.add_argument("--server", type=str, help="Server URL for API mode (e.g., http://localhost:5000)")
    parser.add_argument("--timeout", type=float, default=5.0, help="API timeout in seconds (default: 5.0)")
    args = parser.parse_args()

    # Build block list for Wayside B
    blocks_B: List[str] = _discover_blocks_B()

    root = tk.Tk()
    root.title("Green Line Wayside Controller B (HW)")
    root.geometry("900x750")

    ws_b_ctrl = HW_Wayside_Controller(
        "B", blocks_B, server_url=args.server, timeout=args.timeout
    )
    # Load and start a default PLC
    try:
        plc_path = os.path.join(
            os.path.dirname(__file__), "Green_Line_PLC_XandLdown.py"
        )
        ws_b_ctrl.load_plc(plc_path)
        ws_b_ctrl.start_plc()

    except Exception:
        pass

    ws_b_ui = HW_Wayside_Controller_UI(
        root, ws_b_ctrl, title="Green Line Wayside Controller B (HW)"
    )

    ws_b_ui.pack(fill="both", expand=True)
    ws_b_ui.update_display(emergency=False, speed_mph=0.0, authority_yards=0)

    # Start multi-train processing loop
    try:
        ws_b_ctrl.start_trains(period_s=1.0)
    except Exception:
        pass

    # Start polling loop
    controllers = [ws_b_ctrl]
    uis = [ws_b_ui]
    blocks = [blocks_B]

    _poll_json_loop(root, controllers, uis, blocks)
    root.mainloop()

if __name__ == "__main__":
    main()


'''
Goals for the Module:
6.0 Wayside receive suggested speed & authority from CTC 
6.1 Wayside automatically moves switches based on PLC program execution 
6.2 Wayside automatically sets Traffic light color based on PLC program execution 
6.3 Wayside receives train presence from Track Model 
6.4 Wayside sends track occupancy to CTC 
6.5 Railway crossing lights and gates activated 
6.6 PLC language based only on Boolean variables. 
6.7 Load PLC file 
6.8 In maintenance mode, manually set a switch position 
6.9 Has safety critical architecture
'''