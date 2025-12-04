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
# Config
# ---------------------------------------------------------------------

CTC_IN_FILE    =  "ctc_to_hw_wayside.json"         # CTC 
CTC_OUT_FILE   =  "hw_wayside_to_ctc.json"         # CTC feedback
TRACK_IN_FILE  =  "track_to_hw_wayside.json"       # Track Model
TRACK_OUT_FILE = "hw_wayside_to_track.json"        # Track Model feedback

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
    """Read the track snapshot file defensively."""
    if not os.path.exists(TRACK_IN_FILE):
        return {}
    try:
        with open(TRACK_IN_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception as e:
        print(f"[WARN] Track file read failed: {e}")
        return {}

def _atomic_merge_write_track_json(patch: dict) -> None:
    """
    Read-modify-write TRACK_FILE and atomically replace it.
    We only update/insert keys present in 'patch' and preserve everything else.
    """
    try:
        base = _safe_read_track_json()
        base.update(patch or {})
        d = os.path.dirname(TRACK_OUT_FILE) or "."
        with tempfile.NamedTemporaryFile("w", delete=False, dir=d, encoding="utf-8") as tmp:
            json.dump(base, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = tmp.name
        os.replace(tmp_path, TRACK_OUT_FILE)
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
    
    try:
        if os.path.exists(TRACK_IN_FILE):

            with open(TRACK_IN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f) or {}

            occ = data.get("G-Occupancy") or data.get("occupied_blocks")

            if isinstance(occ, list) and len(occ) > 0:
                return len(occ)
            
    except Exception as e:
        print(f"[WARN] Track file read failed: {e}")

    return 152

def _discover_blocks_B() -> List[str]:
    
    n = _discover_block_count()

    def clamp_range(start: int, end_excl: int) -> List[int]:

        start = max(0, start)
        end_excl = min(n, end_excl)
        return list(range(start, end_excl))

    down = clamp_range(70, 146)  # 70..145
    return [str(i) for i in down]

# ------------------------------------------------------------------------------------
# Poll loop driving wayside B
# ------------------------------------------------------------------------------------

def _poll_json_loop(root, controllers: List[HW_Wayside_Controller], uis: List[HW_Wayside_Controller_UI], blocks_by_ws: List[List[str]]):

    """Read feed, run vital/PLC per wayside, merge status, refresh UIs."""

    raw = _read_ctc_json()
    vital_in = _make_vital_in(raw)

    # debug: vital_in payload (removed for clean runtime)

    track_snapshot = _safe_read_track_json()

    merged_status = {"waysides": {}}

    for controller, ui, blocks in zip(controllers, uis, blocks_by_ws):

        controller.apply_vital_inputs(blocks, vital_in)

        if ENABLE_LOCAL_AUTH_DECAY:
            controller.tick_authority_decay()

        controller.apply_track_snapshot(track_snapshot, limit_blocks=blocks)

        controller.tick_train_progress()

        status = controller.assess_safety(blocks, vital_in)
        # identify this controller in output
        ws_id = getattr(controller, "wayside_id", "X")
        merged_status["waysides"][ws_id] = status

        n_total = _discover_block_count()
        cmd = controller.build_commanded_arrays(n_total)
        # Merge only keys we set; preserve everything else in TRACK_FILE
        _atomic_merge_write_track_json(cmd)
        ui._push_to_display()

    # Write back to CTC JSON
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


# ------------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------------

def main() -> None:

    # Build block list for Wayside B 
    blocks_B: List[str] = _discover_blocks_B()
    # info: initial block list (removed for clean runtime)

    root = tk.Tk()

    root.title("Wayside B")
    root.geometry("900x520")

    ws_b_ctrl = HW_Wayside_Controller("B", blocks_B)
    # Attempt to load and start a default PLC for this wayside (non-fatal)
    try:
        ws_b_ctrl.load_plc("Green_Line_PLC_XandLup.py")
        ws_b_ctrl.start_plc()
    except Exception:
        pass

    ws_b_ui = HW_Wayside_Controller_UI(root, ws_b_ctrl, title="Wayside B")
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