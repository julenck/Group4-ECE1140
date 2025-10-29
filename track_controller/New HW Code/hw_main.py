# hw_main.py
# Main entry point for the Wayside Controller HW module.
# Oliver Kettelson-Belinkie, 2025

from __future__ import annotations
import tkinter as tk
from typing import List
import json
import os
from hw_wayside_controller import HW_Wayside_Controller
from hw_display import HW_Display
from hw_wayside_controller_ui import HW_Wayside_Controller_UI

IN_FILE = "system_feed.json"         # from CTC to Track Controller
OUT_FILE = "wayside_status.json"     # back to CTC

def _read_ctc_json() -> dict:

    """Safely read the incoming CTC/Track file."""

    if not os.path.exists(IN_FILE):

        return {}
    try:

        with open(IN_FILE, "r") as f:

            data = json.load(f)

            for key in ["speed_mph", "authority_yards", "emergency", "occupied_blocks", "closed_blocks"]:

                data.setdefault(key, 0 if key != "emergency" else False)        # Default values of emergency false, others 0

                if key in ["occupied_blocks", "closed_blocks"]:

                    data[key] = list(data[key])                                 # Ensure lists

            return data
        
    except Exception as e:                                                      # JSON read errors

        print(f"[WARN] JSON read failed: {e}")                  
        return {}

def _write_ctc_json(data: dict) -> None:

    """Safely write the outgoing Wayside status file."""

    try:
        with open(OUT_FILE, "w") as f:
            json.dump(data, f, indent=2)

    except Exception as e:                                                # JSON write errors   

        print(f"[WARN] JSON write failed: {e}")

def _make_vital_in(raw: dict) -> dict:

    """JSON dict into the vital input format"""

    return {
        "speed_mph": float(raw.get("speed_mph", 0)),
        "authority_yards": int(raw.get("authority_yards", 0)),
        "emergency": bool(raw.get("emergency", False)),
        "occupied_blocks": list(raw.get("occupied_blocks", [])),
        "closed_blocks": list(raw.get("closed_blocks", [])),
    }

def _poll_json_loop(root, controller, ui, blocks):

    """Read CTC input JSON, run vital pipeline, write output JSON."""
    
    raw = _read_ctc_json()
    vital_in = _make_vital_in(raw)
    controller.apply_vital_inputs(blocks, vital_in)

    # Run PLC cycle
    status = controller.assess_safety(blocks, vital_in)
    _write_ctc_json(status)

    # Update UI
    ui._push_to_display()

    root.after(500, _poll_json_loop, root, controller, ui, blocks)      # Poll every 500ms

def main() -> None:

    blocks: List[str] = ["A1", "A2", "A3", "A4", "A5"]      # Example block IDs - Will need to link to PLC data

    root = tk.Tk()
    controller = HW_Wayside_Controller(blocks)
    display = HW_Display(root, available_blocks=blocks)
    ui = HW_Wayside_Controller_UI(controller, display)

    ui.update_display(emergency=False, speed_mph=0.0, authority_yards=0)

    display.set_map_image("Track.png")

    _poll_json_loop(root, controller, ui, blocks)
    root.mainloop()

if __name__ == "__main__":
    main()



'''Goals for the Module:'''

'''
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