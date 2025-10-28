# hw_wayside_controller_ui.py
# Wayside Controller HW module UI logic.
# Oliver Kettelson-Belinkie, 2025

from __future__ import annotations
from typing import Dict, List
from hw_wayside_controller import HW_Wayside_Controller
from hw_display import HW_Display

class HW_Wayside_Controller_UI:

    toggle_maintenance_mode: bool = False
    selected_block: int | None = None
    maintenance_active: bool = False

    def __init__(self, controller: HW_Wayside_Controller, display: HW_Display) -> None:

        self.controller = controller
        self.display = display

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

    # ----- internal helper -----

    def _push_to_display(self) -> None:
        
        outs = {
            "emergency": self.controller.emergency,
            "speed_mph": int(self.controller.speed_mph),
            "authority_yards": int(self.controller.authority_yards),
            "light_states": dict(self.controller.light_states),
            "gate_states": dict(self.controller.gate_states),
            "switch_states": dict(self.controller.switch_states),
            "occupied_blocks": list(self.controller.occupied_blocks),
        }
        self.display.show_vital(**outs)