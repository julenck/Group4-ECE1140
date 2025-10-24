# hw_vital_check.py
# Vital safety checking module for the Wayside Controller HW.
# Oliver Kettelson-Belinkie, 2025

from __future__ import annotations
from typing import List, Dict, Any, Optional

class HW_Vital_Check:
    
    def verify_light_change(self, states: List, block_id: str, new_state: int) -> bool:
        return True

    def verify_switch_change(self, states: List, block_id: str, new_state: int) -> bool:
        return True

    def verify_gate_change(self, states: List, block_id: str, new_state: int) -> bool:
        return True

    def check_light(self, block_id: str, state: int) -> bool:
        return True

    def check_switch(self, block_id: str, state: int) -> bool:
        return True

    def check_gate(self, block_id: str, state: int) -> bool:
        return True

    def verify_file(self, plc_path: str) -> bool:
        return True

    def check_file(self, plc_path: str) -> Dict:
        return {"ok": True, "warnings": [], "errors": []}

    def verify_system_safety(
        self,
        block_ids: List,
        light_states: List,
        gate_states: List,
        switch_states: List,
        occupied_blocks: List,
        active_plc: Optional[str],
        vital_in: Dict,
    ) -> Dict:
        
        """
        Return a report dict: {"safe": bool, "reasons": [str], "actions": {…}}
        vital_in may contain: emergency, speed_mph, authority_yards, suggestions, closed_blocks, etc.
        """

        reasons: List[str] = []
        actions: Dict[str, Any] = {}

        emergency = bool(vital_in.get("emergency", False))
        speed = float(vital_in.get("speed_mph", 0))
        authority = int(vital_in.get("authority_yards", 0))
        closed_blocks = list(vital_in.get("closed_blocks", []))

        if emergency:

            reasons.append("Emergency active")
            actions["all_signals"] = "RED"

        if authority <= 0 and speed > 0:

            reasons.append("No authority but speed > 0")
            actions["speed_override"] = 0

        if closed_blocks:

            reasons.append(f"Closed blocks: {', '.join(closed_blocks)}")
            actions["protect_blocks"] = closed_blocks

        return {"safe": len(reasons) == 0, "reasons": reasons, "actions": actions}