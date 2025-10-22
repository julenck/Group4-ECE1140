from typing import List, Dict

class hw_vital_check:
    """Validation logic for PLC files and system safety.
    This is a stub you can extend with real rules.
    """
    def verify_light_change(self, states: List[int], block_id: int, new_state: int) -> bool:
        return True

    def verify_switch_change(self, states: List[int], block_id: int, new_state: int) -> bool:
        return True

    def verify_gate_change(self, states: List[int], block_id: int, new_state: int) -> bool:
        return True

    def verify_file(self, plc_path: str) -> bool:
        return plc_path.lower().endswith((".plc", ".txt", ".json"))

    def verify_system_safety(
        self,
        block_ids: list,
        light_states: list,
        gate_states: list,
        switch_states: list,
        occupied_blocks: list,
        active_plc: str,
        vital_in: dict,
    ) -> Dict:
        """Simple rule: if emergency=True, set all lights RED (2)."""
        emergency = bool(vital_in.get("emergency", False))
        actions = {"lights": [], "gates": [], "switches": []}
        reasons, unsafe = [], False
        if emergency:
            unsafe = True
            reasons.append("emergency active; forcing RED signals")
            for b in block_ids:
                actions["lights"].append((b, 2))
        return {"unsafe": unsafe, "reasons": reasons, "actions": actions}
