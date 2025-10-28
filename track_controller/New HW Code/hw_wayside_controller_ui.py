# hw_wayside_controller_ui.py
# Wayside Controller HW module UI logic.
# Oliver Kettelson-Belinkie, 2025

from __future__ import annotations
from typing import Dict, List
from hw_wayside_controller import HW_Wayside_Controller
from hw_display import HW_Display
import os
from tkinter import filedialog

class HW_Wayside_Controller_UI:

    toggle_maintenance_mode: bool = False
    selected_block: int | None = None
    maintenance_active: bool = False

    def __init__(self, controller: HW_Wayside_Controller, display: HW_Display) -> None:

        self.controller = controller
        self.display = display

        self.display.set_handlers(
            on_upload_plc=self._on_upload_plc_clicked,
            on_select_block=self.select_block,
            on_set_switch=self.set_switch_state,
            on_toggle_maintenance=self._on_toggle_maintenance,
        )

    def select_block(self, block_id: str) -> None:

        self.selected_block = block_id  # store for UI
        data = self.controller.get_block_data(block_id)
        self.show_block_data(data)

    def show_block_data(self, data: Dict) -> None:

        print("[BLOCK DATA]", data)

    def update_display(self, emergency: bool, speed_mph: float, authority_yards: int) -> None:

        # Push inputs to controller (these originate from external modules; UI just forwards)

        self.controller.apply_vital_inputs(

            self.controller.block_ids,
            {"emergency": emergency, "speed_mph": speed_mph, "authority_yards": authority_yards},
        )
        self._push_to_display()


    def _on_toggle_maintenance(self, active: bool):

        self.controller.maintenance_active = active
        self.display.show_status("Maintenance ON" if active else "Maintenance OFF")

    def set_plc(self, path: str) -> bool:

        ok = self.controller.load_plc(path)

        if ok:
            self.controller.change_plc(True, path)      
        self._push_to_display()
        return ok

    def set_switch_state(self, block_id: str, state: int) -> bool:

        ok = self.controller.set_switch_state(block_id, state)
        self._push_to_display()
        return ok

    def show_safety_report(self, report: Dict) -> None:

        self.display.show_safety(report)

    # frame builders
    def build_input_frame(self) -> None: pass
    def build_display_frame(self) -> None: pass
    def build_maintenance_frame(self) -> None: pass

    def _ask_plc_path(self) -> str:

        return filedialog.askopenfilename(
            title="Select PLC file",
            filetypes=[("Python PLC files", "*.py"), ("All files", "*.*")],
        )

    def _on_upload_plc_clicked(self):
        path = self._ask_plc_path()
        if not path:
            self.display.show_status("PLC load canceled")
            return

        ok = self.controller.load_plc(path)
        if ok:
            self.display.show_status(f"PLC loaded: {os.path.basename(path)}")
            # Run one safety + PLC pass so new states appear
            vital_in = {"speed_mph": 0, "authority_yards": 0, "emergency": False,
                        "occupied_blocks": [], "closed_blocks": []}
            self.controller.assess_safety(list(self.controller.light_states.keys()), vital_in)
            self._push_to_display()
        else:
            self.display.show_status("PLC load failed (see console)")

    # ----- internal helper -----

    def _push_to_display(self) -> None:
        # Convert internal dicts to the (bid, state) list-tuples expected
        # by the display API.
        outs = {
            "emergency": self.controller.emergency,
            "speed_mph": int(self.controller.speed_mph),
            "authority_yards": int(self.controller.authority_yards),
            "light_states": list(self.controller.light_states.items()),
            "gate_states": list(self.controller.gate_states.items()),
            "switch_states": list(self.controller.switch_states.items()),
            "occupied_blocks": list(self.controller.occupied_blocks),
            "active_plc": self.controller.active_plc or "",
        }
        self.display.show_vital(**outs)