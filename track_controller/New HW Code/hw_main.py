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

IN_FILE    = os.environ.get("WAYSIDE_IN",    "ctc_track_controller.json")          # CTC 
TRACK_FILE = os.environ.get("WAYSIDE_TRACK", "track_to_wayside.json")              # Track Model
POLL_MS = 500
ENABLE_LOCAL_AUTH_DECAY = True  # locally decrement authority based on speed 

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
# (You can override these with env vars if you set up a shared folder)
IN_FILE    = os.environ.get("WAYSIDE_IN",    "system_feed.json")          # from CTC to Track Controller
OUT_FILE   = os.environ.get("WAYSIDE_OUT",   "wayside_status.json")       # back to CTC (optional status)
TRACK_FILE = os.environ.get("WAYSIDE_TRACK", "track_to_wayside.json")     # track model snapshot & commands
POLL_MS = 500
ENABLE_LOCAL_AUTH_DECAY = True  # locally decrement authority based on speed (mph) between CTC updates

# ------------------------------------------------------------------------------------
# JSON I/O
# ------------------------------------------------------------------------------------

def _read_ctc_json() -> dict:

    defaults = {
        "speed_mph": 0.0,
        "authority_yards": 0,
        "emergency": False,
        "occupied_blocks": [],
        "closed_blocks": [],
    }

    if not os.path.exists(IN_FILE):
        return defaults

    try:

        with open(IN_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f) or {}

    except Exception as e:

        print(f"[WARN] JSON read failed: {e}")
        return defaults

    trains = raw.get("Trains")

    if not isinstance(trains, dict) or not trains:

        # No trains → just return zeros / defaults
        return defaults

    chosen = None

    # Prefer an active train
    for _, tdata in trains.items():

        try:
            if int(tdata.get("Active", 0)) == 1:
                chosen = tdata
                break

        except Exception:
            continue

    # If nothing is active, fall back to Train 1 if present
    if chosen is None:
        chosen = trains.get("Train 1")

    if chosen is None:
        speed = 0.0
        auth = 0
    else:
        try:
            speed = float(chosen.get("Suggested Speed", 0.0))
        except Exception:
            speed = 0.0
        try:
            auth = int(chosen.get("Suggested Authority", 0))
        except Exception:
            auth = 0

    closed = list(raw.get("Block Closure", []))

    return {
        "speed_mph": speed,
        "authority_yards": auth,
        "emergency": False,         
        "occupied_blocks": [],      # occupancy comes from TRACK_FILE, not this file
        "closed_blocks": closed,
    }

def _safe_read_track_json() -> dict:
    
    if not os.path.exists(TRACK_FILE):
        return {}
    try:
        with open(TRACK_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception as e:
        print(f"[WARN] Track file read failed: {e}")
        return {}

def _atomic_merge_write_track_json(patch: dict) -> None:
    
    try:
        base = _safe_read_track_json()
        base.update(patch or {})
        d = os.path.dirname(TRACK_FILE) or "."

        with tempfile.NamedTemporaryFile("w", delete=False, dir=d, encoding="utf-8") as tmp:

            json.dump(base, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = tmp.name

        os.replace(tmp_path, TRACK_FILE)

    except Exception as e:
        print(f"[WARN] Track file write failed: {e}")

def _safe_read_track_json() -> dict:
    """Read the track snapshot file defensively."""
    if not os.path.exists(TRACK_FILE):
        return {}
    try:
        with open(TRACK_FILE, "r", encoding="utf-8") as f:
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
        d = os.path.dirname(TRACK_FILE) or "."
        with tempfile.NamedTemporaryFile("w", delete=False, dir=d, encoding="utf-8") as tmp:
            json.dump(base, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = tmp.name
        os.replace(tmp_path, TRACK_FILE)
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

        if os.path.exists(IN_FILE):

            with open(IN_FILE, "r", encoding="utf-8") as f:
                base = json.load(f) or {}

        base["G-Occupancy"] = list(occupancy)

        with open(IN_FILE, "w", encoding="utf-8") as f:
            json.dump(base, f, indent=2)

    except Exception as e:
        print(f"[WARN] CTC occupancy write failed: {e}")

# ------------------------------------------------------------------------------------
# Real block discovery 
# ------------------------------------------------------------------------------------

def _discover_block_count() -> int:
    
    try:
        if os.path.exists(TRACK_FILE):

            with open(TRACK_FILE, "r", encoding="utf-8") as f:
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

    track_snapshot = _safe_read_track_json()

    merged_status = {"waysides": {}}

    for controller, ui, blocks in zip(controllers, uis, blocks_by_ws):

        controller.apply_vital_inputs(blocks, vital_in)

        if ENABLE_LOCAL_AUTH_DECAY:
            controller.tick_authority_decay()

        controller.apply_track_snapshot(track_snapshot, limit_blocks=blocks)

        status = controller.assess_safety(blocks, vital_in)
        # identify this controller in output
        ws_id = getattr(controller, "wayside_id", "X")
        merged_status["waysides"][ws_id] = status

        n_total = _discover_block_count()
        cmd = controller.build_commanded_arrays(n_total)
        # Merge only keys we set; preserve everything else in TRACK_FILE
        _atomic_merge_write_track_json(cmd)

        ui._push_to_display()

        n_total = _discover_block_count()
        cmd = controller.build_commanded_arrays(n_total)
        # Merge only keys we set; preserve everything else in TRACK_FILE
        _atomic_merge_write_track_json(cmd)

        ui._push_to_display()

    # Write back to CTC JSON
    n_total = _discover_block_count()
    combined_occ = [0] * n_total

    for controller in controllers:

        occ = controller.build_commanded_arrays(n_total)
        ccombined_occ = [max(int(a), int(b)) for a, b in zip(combined_occ, occ)]
    _write_ctc_occupancy(combined_occ)

    root.after(POLL_MS, _poll_json_loop, root, controllers, uis, blocks_by_ws)


# ------------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------------

def main() -> None:

    # Build block list for Wayside B 
    blocks_B: List[str] = _discover_blocks_B()
    print(f"[INFO] blocks_B: {len(blocks_B)} -> {blocks_B[:8]}")    

    root = tk.Tk()

    root.title("Wayside B")
    root.geometry("900x520")

    ws_b_ctrl = HW_Wayside_Controller("B", blocks_B)
    ws_b_ui = HW_Wayside_Controller_UI(root, ws_b_ctrl, title="Wayside B")
    ws_b_ui.pack(fill="both", expand=True)
    ws_b_ui.update_display(emergency=False, speed_mph=0.0, authority_yards=0)

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