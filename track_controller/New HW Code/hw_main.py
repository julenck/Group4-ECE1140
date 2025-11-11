# hw_main.py
# Main entry point for the Wayside Controller HW module.
# Oliver Kettelson-Belinkie, 2025

from __future__ import annotations
import os
os.environ["TK_SILENCE_DEPRECATION"] = "1"
import tkinter as tk
from typing import List, Dict
import json

from hw_wayside_controller import HW_Wayside_Controller
from hw_display import HW_Display
from hw_wayside_controller_ui import HW_Wayside_Controller_UI

IN_FILE = "system_feed.json"         # from CTC to Track Controller
OUT_FILE = "wayside_status.json"     # back to CTC
TRACK_FILE = "track_to_wayside.json" # used to discover real block count (G-Occupancy)
POLL_MS = 500

# ------------------------------------------------------------------------------------
# JSON I/O
# ------------------------------------------------------------------------------------

def _read_ctc_json() -> dict:
    """Safely read incoming feed with conservative defaults."""
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
        with open(IN_FILE, "r") as f:
            data = json.load(f) or {}
        # coerce & fill
        data.setdefault("speed_mph", defaults["speed_mph"])
        data.setdefault("authority_yards", defaults["authority_yards"])
        data.setdefault("emergency", defaults["emergency"])
        data.setdefault("occupied_blocks", defaults["occupied_blocks"])
        data.setdefault("closed_blocks", defaults["closed_blocks"])
        data["occupied_blocks"] = list(data["occupied_blocks"])
        data["closed_blocks"] = list(data["closed_blocks"])
        return data
    except Exception as e:
        print(f"[WARN] JSON read failed: {e}")
        return defaults

def _write_ctc_json(data: dict) -> None:
    """Safely write outgoing Wayside status (merged)."""
    try:
        with open(OUT_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[WARN] JSON write failed: {e}")

def _make_vital_in(raw: dict) -> dict:
    """Adapt feed into vital-input shape used by controller."""
    return {
        "speed_mph": float(raw.get("speed_mph", 0)),
        "authority_yards": int(raw.get("authority_yards", 0)),
        "emergency": bool(raw.get("emergency", False)),
        "occupied_blocks": list(raw.get("occupied_blocks", [])),
        "closed_blocks": list(raw.get("closed_blocks", [])),
    }

# ------------------------------------------------------------------------------------
# Real block discovery & SW-like partitioning
# ------------------------------------------------------------------------------------

def _discover_block_count() -> int:
    """
    Read TRACK_FILE and return the length of G-Occupancy if present.
    Falls back to 152 (SW uses 152 indices for the Green Line).
    """
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

def _build_blocks_like_sw() -> Dict[str, List[str]]:
    """
    Mirror the SW controller's Green Line XL partitioning:

    - XL Up  -> [0:73] + [144:151]   -> Wayside A
    - XL Down-> [70:146]             -> Wayside B
    """
    n = _discover_block_count()  # usually 152

    def clamp_range(start: int, end_excl: int) -> List[int]:
        start = max(0, start)
        end_excl = min(n, end_excl)
        return list(range(start, end_excl))

    up_main = clamp_range(0, 73)       # 0..72
    up_tail = clamp_range(144, 151)    # 144..150
    down    = clamp_range(70, 146)     # 70..145

    blocks_A = [str(i) for i in (up_main + up_tail)]
    blocks_B = [str(i) for i in down]
    return {"A": blocks_A, "B": blocks_B}

# ------------------------------------------------------------------------------------
# Poll loop driving both waysides (unchanged call pattern)
# ------------------------------------------------------------------------------------

def _poll_json_loop(root, controllers: List[HW_Wayside_Controller], uis: List[HW_Wayside_Controller_UI], blocks_by_ws: List[List[str]]):
    """Read feed, run vital/PLC per wayside, merge status, refresh UIs."""
    raw = _read_ctc_json()
    vital_in = _make_vital_in(raw)

    merged_status = {"waysides": {}}

    for controller, ui, blocks in zip(controllers, uis, blocks_by_ws):
        controller.apply_vital_inputs(blocks, vital_in)
        status = controller.assess_safety(blocks, vital_in)
        # identify this controller in output
        ws_id = getattr(controller, "wayside_id", "X")
        merged_status["waysides"][ws_id] = status
        ui._push_to_display()

    _write_ctc_json(merged_status)
    root.after(POLL_MS, _poll_json_loop, root, controllers, uis, blocks_by_ws)

# ------------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------------

def main() -> None:
    # Build real block lists the same way SW slices the Green Line
    parts = _build_blocks_like_sw()
    blocks_A: List[str] = parts.get("A", [])
    blocks_B: List[str] = parts.get("B", [])

    print(f"[INFO] blocks_A: {len(blocks_A)} -> {blocks_A[:8]}")
    print(f"[INFO] blocks_B: {len(blocks_B)} -> {blocks_B[:8]}")    

    root = tk.Tk()

    # Only create Wayside B UI/controller here. Wayside A is handled by
    # the SW module externally per the user's request.
    root.title("Wayside B")
    root.geometry("900x520")

    ws_b_ctrl = HW_Wayside_Controller("B", blocks_B)
    ws_b_ui = HW_Wayside_Controller_UI(root, ws_b_ctrl, title="Wayside B")
    ws_b_ui.pack(fill="both", expand=True)
    ws_b_ui.update_display(emergency=False, speed_mph=0.0, authority_yards=0)

    # Start polling loop with only Wayside B
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