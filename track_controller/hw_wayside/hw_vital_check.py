"""
Provides safety verification for switch changes, gate control, light signals,
and overall system safety checks. Includes unit conversion.

Author: Oliver Kettelson-Belinkie, 2025
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple


def yards_to_meters(yards: float) -> float:
   
    return float(yards) * 0.9144


def meters_to_yards(m: float) -> float:
   
    return float(m) / 0.9144


def mph_to_mps(mph: float) -> float:
   
    return float(mph) * 0.44704


def mps_to_mph(mps: float) -> float:
   
    return float(mps) / 0.44704


class HW_Vital_Check:
    
    def check_file(self, plc_path: str) -> Dict:
        """
        Check PLC file for forbidden operations.
        """
        reasons: List[str] = []
        try:
            with open(plc_path, "r", encoding="utf-8") as f:
                text = f.read()

            if "import os" in text or "subprocess" in text:
                reasons.append("forbidden import detected")

            if "eval(" in text or "exec(" in text:
                reasons.append("dynamic code execution detected")

            safe = len(reasons) == 0
            return {"safe": safe, "reasons": reasons, "actions": {}}

        except Exception as e:
            return {"safe": False, "reasons": [f"read error: {e}"], "actions": {}}

    def verify_switch_change(self, switch_states: Dict[str, str], block_id: str, new_state: str, *, 
                             block_graph: Optional[Dict[int, Dict[str, Any]]] = None, 
                             occupied_blocks: Optional[List[str]] = None, closed_blocks: Optional[List[str]] = None, 
                             switch_map: Optional[Dict[str, Dict[str, int]]] = None,
    ) -> Tuple[bool, str]:
        """
        If any of the following are true, the change is rejected with a reason:
        - the switch block itself is occupied or closed
        - any of the switch's immediate next blocks (forward_next/reverse_next) are occupied or closed
        """
        try:
            bid = str(block_id)
            occ = set(occupied_blocks or [])
            closed = set(closed_blocks or [])

            # If the switch block itself is occupied/closed, reject
            if bid in occ:
                return False, f"Switch block {bid} is occupied"
            
            if bid in closed:
                return False, f"Switch block {bid} is closed"

            branch_targets = []

            try:
                bid_i = int(bid)

            except Exception:
                bid_i = None

            # Determine numeric desired position
            desired_pos = None
            try:
                # if new_state is numeric-like
                if isinstance(new_state, int):
                    desired_pos = int(new_state)

                else:
                    s = str(new_state).strip()

                    if s.isdigit():
                        desired_pos = int(s)

                    else:
                        su = s.upper()

                        if su.startswith('L'):
                            desired_pos = 0

                        elif su.startswith('R'):
                            desired_pos = 1

            except Exception:
                desired_pos = None

            # If a explicit switch_map is provided, prefer it
            branch_targets = []

            try:
                if switch_map is not None:

                    entry = (switch_map.get(str(bid)) or
                             switch_map.get(int(bid) if bid.isdigit() else None))
                    
                    if entry is not None and desired_pos is not None:
                        
                        key = str(desired_pos)
                        val = entry.get(key) if isinstance(entry, dict) else None

                        if val is None:
                            val = entry.get(desired_pos)

                        if isinstance(val, int) and val >= 0:
                            branch_targets.append(val)

            except Exception:
                pass

            # Inspect block_graph to find branch targets if not found
            try:
                if (block_graph is not None and bid_i is not None and bid_i in block_graph):

                    info = block_graph[bid_i]
                    fwd = info.get('forward_next', -1)
                    rev = info.get('reverse_next', -1)

                    # Map desired_pos to forward/reverse if switch_map didn't provide mapping
                    if not branch_targets:
                        if desired_pos == 0 and isinstance(fwd, int) and fwd >= 0:
                            branch_targets.append(fwd)

                        elif desired_pos == 1 and isinstance(rev, int) and rev >= 0:
                            branch_targets.append(rev)
                   
                    # Collect immediate neighbor candidates
                    neighbor_candidates = []

                    for candidate in (fwd, rev):
                        if isinstance(candidate, int) and candidate >= 0:
                            neighbor_candidates.append(candidate)

            except Exception:
                pass

            # If we found branch targets, walk each a small depth to check for conflicts
            to_check = set()
            depth_limit = 3         # 3 blocks deep check
            try:
                for start in branch_targets:

                    cur = start
                    depth = 0

                    while depth < depth_limit and isinstance(cur, int) and cur >= 0:

                        to_check.add(str(cur))
                        info = block_graph.get(cur, {}) if block_graph else {}
                        nxt = info.get('forward_next', -1)

                        if not isinstance(nxt, int) or nxt < 0:
                            break

                        cur = nxt
                        depth += 1

            except Exception:
                pass

            # Include immediate neighbor candidates
            try:
                for n in neighbor_candidates:
                    to_check.add(str(n))

            except Exception:
                pass

            if not to_check:        # Fallback: check nearby blocks if no targets found
                try:
                    if bid_i is not None:

                        for delta in (-2, -1, 1, 2):
                            to_check.add(str(bid_i + delta))

                except Exception:
                    pass

            inter_occ = to_check.intersection(occ)

            if inter_occ:
                blocks_str = ', '.join(sorted(inter_occ))
                return False, f"Branch conflict: occupied blocks {blocks_str}"
            
            inter_closed = to_check.intersection(closed)

            if inter_closed:
                blocks_str = ', '.join(sorted(inter_closed))
                return False, f"Branch conflict: closed blocks {blocks_str}"

            return True, "OK"

        except Exception as e:
            return False, f"Safety check failed: {e}"

    def verify_gate_change(self, gate_states: Dict[str, str], block_id: str, new_state: str, *,
                           occupied_blocks: Optional[List[str]] = None, closed_blocks: Optional[List[str]] = None,
                           approach_blocks: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """
        Verify gate change is safe (don't open if crossing occupied).
        """
        try:
            occ = set(occupied_blocks or [])
            closed = set(closed_blocks or [])
            s = str(new_state).upper()
            want_open = s in ('UP', '1', 'OPEN')

            # If the gate is marked closed/failed, disallow opening
            if str(block_id) in closed and want_open:
                return False, f"Gate {block_id} is closed/locked"

            # If any approach block is occupied, disallow opening
            for b in (approach_blocks or []):

                if str(b) in occ and want_open:
                    return False, f"Approach occupied: {b}"

            # Otherwise permit
            return True, "OK"
        
        except Exception as e:
            return False, f"Gate safety check failed: {e}"

    def verify_light_change(self, light_states: Dict[str, str], block_id: str, new_state: str, *,
                            occupied_blocks: Optional[List[str]] = None, closed_blocks: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """
        Verify light change is safe (no green or supergreen on occupied blocks).
        """
        try:
            occ = set(occupied_blocks or [])
            closed = set(closed_blocks or [])
            s = str(new_state).upper()

            if str(block_id) in occ and s in ('GREEN', 'SUPERGREEN'):
                return False, f"Block {block_id} occupied — cannot set {s}"

            if str(block_id) in closed and s in ('GREEN', 'SUPERGREEN'):
                return False, f"Block {block_id} closed — cannot set {s}"

            return True, "OK"
        
        except Exception as e:
            return False, f"Light safety check failed: {e}"

    def normalize_vital_input(self, vital_in: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return a normalized vital input dict with standard units and types.
        """

        out = dict(vital_in)

        # Normalize speed
        speed_mph = float(vital_in.get("speed_mph", 0.0))
        out["speed_mps"] = mph_to_mps(speed_mph)

        # Normalize authority
        authority_yards = float(vital_in.get("authority_yards", 0.0))
        out["authority_m"] = yards_to_meters(authority_yards)

        # Ensure lists exist
        out["closed_blocks"] = list(vital_in.get("closed_blocks", []))
        out["occupied_blocks"] = list(vital_in.get("occupied_blocks", []))

        out["emergency"] = bool(vital_in.get("emergency", False))

        return out

    def verify_system_safety(self, block_ids: List, light_states: List, gate_states: List,
                             switch_states: List, occupied_blocks: List, active_plc: Optional[str],
                             vital_in: Dict, *, speed_limit_mph: Optional[float] = None,
    ) -> Dict:
        """
        Verify overall system safety based on vital inputs and states.
        """

        reasons: List[str] = []
        actions: Dict[str, Any] = {}

        v = self.normalize_vital_input(vital_in)

        if v["emergency"]:
            reasons.append("Emergency active")
            actions["all_signals"] = "RED"
            actions["speed_override"] = 0

        # Authority vs movement
        if v.get("authority_m", 0.0) <= 0.0 and v.get("speed_mps", 0.0) > 0.0:
            reasons.append("No authority but speed > 0")
            actions["speed_override"] = 0

        # Closed block protection: occupied & closed overlap
        closed = set(v.get("closed_blocks", []))
        occupied = set(v.get("occupied_blocks", []))
        overlap = closed.intersection(occupied)

        if overlap:
            reasons.append(f"Occupied blocks in closed set: {', '.join(overlap)}")
            actions["protect_blocks"] = list(overlap)

        # Optional overspeed check against provided limit
        if speed_limit_mph is not None:

            cur_mps = v.get("speed_mps", 0.0)
            limit_mps = mph_to_mps(speed_limit_mph)

            if cur_mps > limit_mps * 1.01:  # small tolerance

                reasons.append(
                    f"Overspeed: {mps_to_mph(cur_mps):.1f} mph > limit {speed_limit_mph:.1f} mph"
                )
                # Only override speed if significantly over limit (>10% tolerance)
                if cur_mps > limit_mps * 1.10:
                    actions["speed_override"] = mps_to_mph(limit_mps)

        if active_plc is not None:
            if not isinstance(active_plc, str) or active_plc.strip() == "":
                reasons.append("Active PLC identifier invalid")

        safe = len(reasons) == 0
        return {"safe": safe, "reasons": reasons, "actions": actions}


def compute_commanded_speed(light_state: str, suggested_speed_mph: float, authority_yards: int):
    """
    Compute the commanded speed based on light state and authority.
    """

    if authority_yards <= 0:
        return 0.0, "No authority"

    if light_state == "GREEN":
        return float(suggested_speed_mph), "Signal is GREEN"

    if light_state == "YELLOW":
        return float(suggested_speed_mph) * 0.50, "Signal is YELLOW"

    if light_state == "RED":
        return 0.0, "Signal is RED"

    return float(suggested_speed_mph), "Unknown signal state"


def run_tests():            # Simple unit tests for HW_Vital_Check
   
    vc = HW_Vital_Check()

    tests: List[Tuple[str, float, int]] = [
        ("RED", 30.0, 100),
        ("GREEN", 20.0, 200),
        ("YELLOW", 20.0, 200),
        ("GREEN", 20.0, 0),
    ]

    for light, speed, auth in tests:

        # Test scaffolding: compute commanded speed and run safety report.
        commanded, reason = compute_commanded_speed(light, speed, auth)
      
        vital_in = {
            "speed_mph": speed,
            "authority_yards": auth,
            "closed_blocks": [],
            "occupied_blocks": []
        }

        report = vc.verify_system_safety(
            block_ids=[],
            light_states=[],
            gate_states=[],
            switch_states=[],
            occupied_blocks=[],
            active_plc=None,
            vital_in=vital_in,
            speed_limit_mph=50.0,
        )

if __name__ == "__main__":
    run_tests()