# hw_vital_check.py
# Vital safety checking module for the Wayside Controller HW.
# Oliver Kettelson-Belinkie, 2025

from __future__ import annotations
from typing import List, Dict, Any, Optional

class HW_Vital_Check:
    
    def verify_light_change(self, states: List, block_id: str, new_state: int) -> bool:     #placeholder
        return True

    def verify_switch_change(self, states: List, block_id: str, new_state: int) -> bool:    #placeholder
        return True

    def verify_gate_change(self, states: List, block_id: str, new_state: int) -> bool:      #placeholder
        return True

    def check_light(self, block_id: str, state: int) -> bool:                               #placeholder
        return True

    def check_switch(self, block_id: str, state: int) -> bool:                              #placeholder 
        return True

    def check_gate(self, block_id: str, state: int) -> bool:                                #placeholder
        return True

    def verify_file(self, plc_path: str) -> bool:                                           #placeholder
        return True

    def check_file(self, plc_path: str) -> Dict:                                            #placeholder
        reasons: List[str] = []
        try:

            with open(plc_source_path, "r", encoding="utf-8") as f:
                text = f.read()

            if "import os" in text or "subprocess" in text:
                reasons.append("forbidden import detected")

            if "eval(" in text or "exec(" in text:
                reasons.append("dynamic code execution detected")

            safe = len(reasons) == 0
            return {"safe": safe, "reasons": reasons, "actions": {}}
        
        except Exception as e:
            return {"safe": False, "reasons": [f"read error: {e}"], "actions": {}}

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
    
# ============================================================
# TEST CASE - LAB 12
# ============================================================

def compute_commanded_speed(light_state: str, suggested_speed: float, authority: int):

    """
    - GREEN → normal speed
    - YELLOW → reduced speed
    - RED → 0 mph
    - Authority = 0 → 0 mph regardless of signal
    """

    if authority <= 0:

        return 0, "No authority but speed > 0"

    if light_state == "GREEN":

        return suggested_speed, "Signal is GREEN"

    if light_state == "YELLOW":

        return suggested_speed * 0.50, "Signal is YELLOW"

    if light_state == "RED":

        return 0, "Signal is RED"

    return suggested_speed, "Unknown signal state"


def run_tests():

    vc = HW_Vital_Check()

    tests = [

        ("RED", 30.0, 100),                 # Expect 0 mph due to RED light
        ("GREEN", 20.0, 200),               # Expect 20 mph due to GREEN light
        ("YELLOW", 20.0, 200),              # Expect 10 mph due to YELLOW light
        ("GREEN", 20.0, 0),                 # Expect 0 mph due to no authority
    ]

    for light, speed, auth in tests:

        print(f"Test: Light={light}, Suggested Speed={speed} mph, Authority={auth}")

        commanded, reason = compute_commanded_speed(light, speed, auth)

        print(f" Commanded Speed: {commanded:.2f} mph")

        if reason:

            print(f" Reason: {reason}")

        # Show vital safety system output
        vital_in = {

            "speed_mph": speed,
            "authority_yards": auth
        }

        report = vc.verify_system_safety(
            block_ids=[],
            light_states=[],
            gate_states=[],
            switch_states=[],
            occupied_blocks=[],
            active_plc=None,
            vital_in=vital_in
        )

if __name__ == "__main__":
    run_tests()