from typing import List, Dict
from hw_wayside_controller import hw_wayside_controller
from hw_display import hw_display

class hw_wayside_controller_ui:
    """UI orchestrator for HW (screen-only app)."""
    def __init__(self, controller: hw_wayside_controller, display: hw_display) -> None:
        self.controller = controller
        self.display = display
        self.maintenance_active: bool = False

        # wire handlers
        self.display.on_select_block = self._on_select_block
        self.display.on_upload_plc = self._on_upload_plc
        self.display.on_set_switch = self._on_set_switch
        self.display.on_toggle_maintenance = self._on_toggle_maintenance

    # ---- public runtime entry
    def apply_vital_inputs(self, block_ids: List[int], vital_in: Dict) -> None:
        self.controller.apply_vital_inputs(block_ids, vital_in)
        outs = self.controller.generate_outputs(block_ids, vital_in)
        self.display.update_blocks(block_ids or list(range(len(self.controller.light_states))))
        self.display.show_vital(
            emergency=outs["emergency"],
            speed_mph=outs["speed_mph"],
            authority_yards=outs["authority_yards"],
            light_states=outs["light_states"],
            gate_states=outs["gate_states"],
            switch_states=outs["switch_states"],
            occupied_blocks=outs["occupied_blocks"],
        )

    # ---- handlers
    def _on_select_block(self, block_id: int) -> None:
        data = self.controller.get_block_data(block_id)
        self.display.show_block_info(data)

    def _on_upload_plc(self, path: str) -> None:
        if not self.maintenance_active:
            self.display.set_status("Enable maintenance to upload PLC.")
            return
        if not self.controller.load_plc(path):
            self.display.set_status("PLC invalid.")
            return
        if self.controller.change_plc(True, path):
            self.display.set_status(f"PLC activated: {path}")
        else:
            self.display.set_status("Failed to activate PLC (maintenance off?).")

    def _on_set_switch(self, block_id: int, state: int) -> None:
        if not self.maintenance_active:
            self.display.set_status("Enable maintenance to set switches.")
            return
        ok = self.controller.set_switch_state(block_id, state)
        self.display.set_status("Switch updated." if ok else "Unsafe switch request.")
        # refresh block view
        self._on_select_block(block_id)

    def _on_toggle_maintenance(self, enabled: bool) -> None:
        self.maintenance_active = enabled
        self.controller.maintenance_active = enabled
        self.display.set_maintenance_enabled(enabled)
        self.display.set_status("Maintenance ON" if enabled else "Maintenance OFF")
