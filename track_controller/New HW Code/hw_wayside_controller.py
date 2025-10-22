from typing import List, Dict
from hw_vital_check import hw_vital_check

class hw_wayside_controller:
    def __init__(self) -> None:
        self.active_plc: str = ""
        self.maintenance_active: bool = False
        self.auto_safety_enabled: bool = True
        self.light_states: List[int] = []
        self.gate_states: List[int] = []
        self.switch_states: List[int] = []
        self.occupied_blocks: List[int] = []
        self._vital = hw_vital_check()

    # ---- maintenance
    def load_plc(self, path: str) -> bool:
        return self._vital.verify_file(path)

    def change_plc(self, active: bool, plc_path: str) -> bool:
        if not self.maintenance_active:
            return False
        if active and not self._vital.verify_file(plc_path):
            return False
        if active:
            self.active_plc = plc_path
        return True

    def set_switch_state(self, block_id: int, state: int) -> bool:
        if not self.maintenance_active:
            return False
        self._ensure_size(block_id)
        if not self._vital.verify_switch_change(self.switch_states, block_id, state):
            return False
        self.switch_states[block_id] = state
        return True

    # ---- runtime
    def apply_vital_inputs(self, block_ids: List[int], vital_in: Dict) -> None:
        self.occupied_blocks = vital_in.get("occupied_blocks", self.occupied_blocks)

    def assess_safety(self, block_ids: List[int], vital_in: Dict) -> Dict:
        return self._vital.verify_system_safety(
            block_ids, self.light_states, self.gate_states,
            self.switch_states, self.occupied_blocks,
            self.active_plc, vital_in,
        )

    def enforce_safety(self, actions: Dict) -> None:
        for b, s in actions.get("lights", []):
            self._ensure_size(b)
            self.light_states[b] = s

    def set_system_safe(self, emergency: bool) -> None:
        if emergency:
            for i in range(len(self.light_states)):
                self.light_states[i] = 2  # RED

    def generate_outputs(self, block_ids: List[int], vital_in: Dict) -> Dict:
        report = self.assess_safety(block_ids, vital_in)
        if report.get("unsafe") and self.auto_safety_enabled:
            self.enforce_safety(report.get("actions", {}))

        for b in block_ids:
            self._ensure_size(b)

        return {
            "emergency": bool(vital_in.get("emergency", False)),
            "speed_mph": int(vital_in.get("speed_mph", 0)),
            "authority_yards": int(vital_in.get("authority_yards", 0)),
            "light_states": [self.light_states[b] for b in block_ids] if block_ids else self.light_states,
            "gate_states": [self.gate_states[b] if b < len(self.gate_states) else 0 for b in block_ids] if block_ids else self.gate_states,
            "switch_states": [self.switch_states[b] for b in block_ids] if block_ids else self.switch_states,
            "occupied_blocks": self.occupied_blocks,
        }

    # ---- queries
    def get_block_data(self, block_id: int) -> Dict:
        self._ensure_size(block_id)
        return {
            "block_id": block_id,
            "light_state": self.light_states[block_id],
            "gate_state": self.gate_states[block_id],
            "switch_state": self.switch_states[block_id],
            "occupied": (block_id in self.occupied_blocks),
            "active_plc": self.active_plc or "(none)",
        }

    # ---- helpers
    def _ensure_size(self, block_id: int) -> None:
        target = block_id + 1
        while len(self.light_states) < target:
            self.light_states.append(0)
        while len(self.gate_states) < target:
            self.gate_states.append(0)
        while len(self.switch_states) < target:
            self.switch_states.append(0)
