# hw_wayside_controller.py
# Wayside Controller HW module core logic.
# Oliver Kettelson-Belinkie, 2025

from __future__ import annotations
from typing import Dict, List, Any, Optional
from hw_vital_check import HW_Vital_Check

class HW_Wayside_Controller:
    
    light_result: bool = False
    switch_result: bool = False
    gate_result: bool = False 
    plc_result: bool = False

    active_trains: Dict[str, Any]
    occupied_blocks: List[str]          # Have to add functionality w/o track model
    light_states: Dict[str, int]
    gate_states: Dict[str, int]
    switch_states: Dict[str, int]

    active_plc: Optional[str]
    maintenance_active: bool
    safety_result: bool
    safety_report: Dict
    auto_safety_enabled: bool

    # Inputs from other modules 
    speed_mph: float
    authority_yards: int
    emergency: bool
    closed_blocks: List[str]

    def __init__(self, block_ids: List[str]) -> None:

        self.block_ids = list(block_ids)
        self.active_trains = {}
        self.occupied_blocks = []
        self.light_states = {b: 0 for b in block_ids}   # 0 = red, 1 = yellow, 2 = green, 3 = very green
        self.gate_states = {b: 0 for b in block_ids}
        self.switch_states = {b: 0 for b in block_ids}  # 0 = straight, 1 = diverging
        self.active_plc = None
        self.maintenance_active = False
        self.safety_result = True
        self.safety_report = {}
        self.auto_safety_enabled = True
        self.speed_mph = 0.0
        self.authority_yards = 0
        self.emergency = False
        self.closed_blocks = []

        self.vital = HW_Vital_Check()

    def apply_vital_inputs(self, block_ids: List, vital_in: Dict) -> None:

        """Primary receive point for external inputs."""

        if "speed_mph" in vital_in: self.speed_mph = float(vital_in["speed_mph"])
        if "authority_yards" in vital_in: self.authority_yards = int(vital_in["authority_yards"])
        if "emergency" in vital_in: self.emergency = bool(vital_in["emergency"])
        if "occupied_blocks" in vital_in: self.occupied_blocks = list(vital_in["occupied_blocks"])
        if "closed_blocks" in vital_in: self.closed_blocks = list(vital_in["closed_blocks"])

        # Mandatory safety assessment after input change
        self.assess_safety(block_ids, vital_in)

    def set_system_safe(self, emergency: bool) -> None:

        """Failure/Emergency input from external system."""

        self.emergency = bool(emergency)
        self.assess_safety(self.block_ids, self._current_vital_in())

    def confirm_switch_state(self, block_id: str, state: int) -> bool:

        return block_id in self.switch_states and self.switch_states[block_id] == int(state)

    # Allow CTC to request a switch change
    def set_switch_state(self, block_id: str, state: int) -> bool:

        if block_id not in self.switch_states:

            return False
        
        self.switch_states[block_id] = int(state)
        self.assess_safety(self.block_ids, self._current_vital_in())
        return True

    # ---------------- PLC handling ----------------

    def load_plc(self, path: str) -> bool:

        ok = self.vital.verify_file(path) and self.vital.check_file(path).get("ok", False)
        self.plc_result = ok

        if ok:
            self.active_plc = path

        return ok

    def change_plc(self, active: bool, plc_path: str) -> bool:

        if active and plc_path:

            self.active_plc = plc_path
            return True
        
        return False

    # ---------------- logic / outputs ----------------
    def assess_safety(self, block_ids: List, vital_in: Dict) -> Dict:

        # Run PLC cycle (no-op placeholder). Real PLC execution would
        # parse/execute the loaded PLC file and update light/switch/gate
        # states. Keep this a safe no-op for now to avoid runtime errors
        # and to make the controller usable during testing.
        self.run_plc_cycle()

        # --- Step 2: Vital safety verification ---
        report = self.vital.verify_system_safety(
            block_ids=block_ids,
            light_states=list(self.light_states.items()),
            gate_states=list(self.gate_states.items()),
            switch_states=list(self.switch_states.items()),
            occupied_blocks=self.occupied_blocks,
            active_plc=self.active_plc,
            vital_in=vital_in,
        )

        # --- Step 3: Enforce results ---
        self.enforce_safety(report.get("actions", {}))
        self.safety_report = report
        return report

    def enforce_safety(self, actions: Dict) -> bool:

        changed = False

        if actions.get("all_signals") == "RED":

            for b in self.light_states:
                if self.light_states[b] != 0:
                    self.light_states[b] = 0
                    changed = True

        if "speed_override" in actions:
            self.speed_mph = float(actions["speed_override"])
        return changed

    def send_final_outputs(self, outputs: Dict) -> None:
        return

    # ---------------- data accessors ----------------

    def get_block_data(self, block_id: str) -> Dict:
        return {
            "block_id": block_id,
            "light": self.light_states.get(block_id, 0),
            "switch": self.switch_states.get(block_id, 0),
            "gate": self.gate_states.get(block_id, 0),
            "occupied": block_id in self.occupied_blocks,
            "closed": block_id in self.closed_blocks,
        }

    # ---------------- internal helpers ----------------

    def _current_vital_in(self) -> Dict:

        return {
            "speed_mph": self.speed_mph,
            "authority_yards": self.authority_yards,
            "emergency": self.emergency,
            "occupied_blocks": list(self.occupied_blocks),
            "closed_blocks": list(self.closed_blocks),
        }

    def _final_outputs(self) -> Dict:

        return {
            "emergency": self.emergency,
            "speed_mph": int(self.speed_mph),
            "authority_yards": int(self.authority_yards),
            "light_states": dict(self.light_states),
            "gate_states": dict(self.gate_states),
            "switch_states": dict(self.switch_states),
            "occupied_blocks": list(self.occupied_blocks),
        }

    def generate_outputs(self, block_ids: List, vital_in: Dict) -> Dict:

        self.assess_safety(block_ids, vital_in)
        return self._final_outputs()

    # ---------------- internal plc/runtime helpers ----------------
    def run_plc_cycle(self) -> None:
        """Placeholder for running a loaded PLC file.

        Currently this is intentionally a no-op to avoid importing and
        executing arbitrary PLC code from disk. If an active PLC is set
        we keep plc_result True (as set by load_plc); otherwise False.
        Future work: run PLC in a safe subprocess or restricted eval.
        """
        if self.active_plc:
            # PLC was previously validated by HW_Vital_Check.verify_file()
            # and check_file(); don't execute it here — just note presence.
            self.plc_result = True
        else:
            self.plc_result = False