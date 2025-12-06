# hw_main.py
# Main entry point for the Wayside Controller HW module.
# Oliver Kettelson-Belinkie, 2025

from __future__ import annotations
import os
os.environ["TK_SILENCE_DEPRECATION"] = "1"
import tkinter as tk
from typing import List, Dict
import json
import tempfile

from hw_wayside_controller import HW_Wayside_Controller
from hw_display import HW_Display
from hw_wayside_controller_ui import HW_Wayside_Controller_UI

# ---------------------------------------------------------------------
# GPIO Setup for Physical Switch Control
# ---------------------------------------------------------------------
# Set to True when running on Raspberry Pi with GPIO connected
ENABLE_GPIO = True

GPIO_SWITCH_PIN = 17  # BCM pin number for the physical switch input

# Try to import GPIO library (only works on Raspberry Pi)
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("[INFO] RPi.GPIO not available - physical switch disabled")

def setup_gpio():
    """Initialize GPIO for physical switch input."""
    if not GPIO_AVAILABLE or not ENABLE_GPIO:
        return False
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GPIO_SWITCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        print(f"[GPIO] Physical switch initialized on GPIO {GPIO_SWITCH_PIN}")
        return True
    except Exception as e:
        print(f"[GPIO] Setup failed: {e}")
        return False

def cleanup_gpio():
    """Clean up GPIO on exit."""
    if GPIO_AVAILABLE and ENABLE_GPIO:
        try:
            GPIO.cleanup()
        except Exception:
            pass

def read_physical_switch() -> str:
    """Read the physical switch state. Returns 'Left' or 'Right'."""
    if not GPIO_AVAILABLE or not ENABLE_GPIO:
        return None
    try:
        # With pull-up: LOW (0) = switch connected to GND = "Left"
        #               HIGH (1) = switch open/floating = "Right"
        state = GPIO.input(GPIO_SWITCH_PIN)
        return "Right" if state == GPIO.HIGH else "Left"
    except Exception:
        return None

def apply_physical_switch(controller: HW_Wayside_Controller) -> None:
    """Read physical switch and apply to selected block if it has a switch."""
    if not GPIO_AVAILABLE or not ENABLE_GPIO:
        return
    
    # Only apply in maintenance mode
    if not getattr(controller, 'maintenance_active', False):
        return
    
    # Get selected block
    selected = controller.get_selected_block()
    if not selected:
        return
    
    # Check if selected block has a switch
    if not controller.has_switch(selected):
        return
    
    # Read physical switch state
    new_state = read_physical_switch()
    if new_state is None:
        return
    
    # Get current commanded state
    with controller._lock:
        current_state = controller._cmd_switch_state.get(selected) or controller._switch_state.get(selected)
    
    # Normalize state names (handle 0/1 or "Left"/"Right")
    def normalize_state(s):
        if s in [0, "0", "Left"]:
            return "Left"
        elif s in [1, "1", "Right"]:
            return "Right"
        return str(s)
    
    current_state = normalize_state(current_state)
    new_state = normalize_state(new_state)
    
    # Only apply if state changed
    if current_state != new_state:
        allowed, reason = controller.request_switch_change(selected, new_state)
        if allowed:
            print(f"[GPIO] Switch {selected} changed to {new_state} (physical switch)")
        else:
            print(f"[GPIO] Switch {selected} change rejected: {reason}")

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------

# Use absolute paths based on project root (matching SW controller exactly)
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_CURRENT_DIR))  # hw_wayside -> track_controller -> project root

CTC_IN_FILE    = os.path.join(_PROJECT_ROOT, "ctc_track_controller.json")      # CTC (shared with SW wayside)
CTC_OUT_FILE   = os.path.join(_PROJECT_ROOT, "hw_wayside_to_ctc.json")         # CTC feedback (optional)
TRACK_COMM_FILE = os.path.join(_PROJECT_ROOT, "track_controller", "New_SW_Code", "track_to_wayside.json")  # Shared state between controllers

POLL_MS = 500
ENABLE_LOCAL_AUTH_DECAY = True  # locally decrement authority based on speed 


# ------------------------------------------------------------------------------------
# JSON I/O
# ------------------------------------------------------------------------------------

def _read_ctc_json() -> dict:

    """
    Safely read incoming CTC feed from ctc_track_controller.json and adapt it
    into the flat shape our HW controller expects:
      - speed_mph / authority_yards : taken from the first Active train
      - occupied_blocks             : all Active train positions
      - closed_blocks               : from Block Closure
    """
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
        # Active flag: may be int, str, or empty
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
            # Handle your typo "Suggestd Authority" as well
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


def _safe_read_track_json() -> dict:
    """Read the shared track state file (matching SW behavior)."""
    if not os.path.exists(TRACK_COMM_FILE):
        return {}
    try:
        with open(TRACK_COMM_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception as e:
        print(f"[WARN] Track file read failed: {e}")
        return {}

def _atomic_write_track_json(patch: dict) -> None:
    """
    Update track state file with HW controller's outputs (matching SW behavior).
    Reads current state, updates HW's portion, writes atomically.
    """
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

def _make_vital_in(raw: dict) -> dict:
    
    return {
        "speed_mph": float(raw.get("speed_mph", 0)),
        "authority_yards": int(raw.get("authority_yards", 0)),
        "emergency": bool(raw.get("emergency", False)),
        "occupied_blocks": list(raw.get("occupied_blocks", [])),
        "closed_blocks": list(raw.get("closed_blocks", [])),
    }

def _write_ctc_occupancy(occupancy: List[int]) -> None:
    
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

# ------------------------------------------------------------------------------------
# Real block discovery 
# ------------------------------------------------------------------------------------

def _discover_block_count() -> int:
    """Return block count - fixed at 152 since no track model."""
    return 152

def _discover_blocks_B() -> List[str]:
    """Return block IDs for Wayside B (XandLdown).
    
    Block ranges for command authority (managed_blocks):
    - SW Wayside 1 (XandLup): 0-69, 144-150
    - HW Wayside B (XandLdown): 70-143
    
    These are the MANAGED blocks (what we write commands for).
    visible_blocks can extend further for handoff tracking.
    """
    n = _discover_block_count()

    def clamp_range(start: int, end_excl: int) -> List[int]:

        start = max(0, start)
        end_excl = min(n, end_excl)
        return list(range(start, end_excl))

    # Managed blocks: 70-143 (no overlap with SW1's 144-150)
    down = clamp_range(70, 144)  # 70..143
    return [str(i) for i in down]

# ------------------------------------------------------------------------------------
# Poll loop driving wayside B
# ------------------------------------------------------------------------------------

def _poll_json_loop(root, controllers: List[HW_Wayside_Controller], uis: List[HW_Wayside_Controller_UI], blocks_by_ws: List[List[str]]):

    """Read CTC feed, run vital/PLC per wayside, refresh UIs (matching SW behavior)."""

    raw = _read_ctc_json()
    vital_in = _make_vital_in(raw)

    # Read shared track state (like SW does)
    track_snapshot = _safe_read_track_json()

    merged_status = {"waysides": {}}

    for controller, ui, blocks in zip(controllers, uis, blocks_by_ws):

        controller.apply_vital_inputs(blocks, vital_in)

        if ENABLE_LOCAL_AUTH_DECAY:
            controller.tick_authority_decay()

        # Apply track snapshot (like SW does, even if mostly empty)
        controller.apply_track_snapshot(track_snapshot, limit_blocks=blocks)

        controller.tick_train_progress()

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

    # Poll physical switch and apply to selected block (if GPIO enabled)
    for controller in controllers:
        try:
            apply_physical_switch(controller)
        except Exception:
            pass

    root.after(POLL_MS, _poll_json_loop, root, controllers, uis, blocks_by_ws)


# ------------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------------

def main() -> None:

    # Build block list for Wayside B 
    blocks_B: List[str] = _discover_blocks_B()
    # info: initial block list (removed for clean runtime)

    # Initialize GPIO for physical switch (if enabled and available)
    gpio_initialized = setup_gpio()

    root = tk.Tk()

    root.title("Green Line Wayside Controller B (HW)")
    root.geometry("900x750")
    
    # Cleanup GPIO on window close
    def on_closing():
        cleanup_gpio()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)

    ws_b_ctrl = HW_Wayside_Controller("B", blocks_B)
    # Attempt to load and start a default PLC for this wayside (non-fatal)
    try:
        ws_b_ctrl.load_plc("Green_Line_PLC_XandLdown.py")
        ws_b_ctrl.start_plc()
    except Exception:
        pass

    ws_b_ui = HW_Wayside_Controller_UI(root, ws_b_ctrl, title="Green Line Wayside Controller B (HW)")
    ws_b_ui.pack(fill="both", expand=True)
    ws_b_ui.update_display(emergency=False, speed_mph=0.0, authority_yards=0)
    # Start multi-train processing loop (background)
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