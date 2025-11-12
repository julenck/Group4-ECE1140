"""
HW wayside controller: mirrors the SW controller shape but stays hardware-agnostic.
- Holds block set for this wayside
- Accepts feed updates (speed/authority/emergency/occupancy/closures)
- Exposes read-only getters used by the UI
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
import threading
import time

# Optional import of your PLCs (left dynamic to avoid import errors if absent)
try:
    import Green_Line_PLC_XandLup as plc_module  # noqa: F401
except Exception:
    plc_module = None

_LIGHT_NAMES = {0: "RED", 1: "YELLOW", 2: "GREEN", 3: "SUPERGREEN"}
_SWITCH_NAMES = {0: "Left", 1: "Right"}  # placeholder until final mapping
_GATE_NAMES = {0: "DOWN", 1: "UP"}

class HW_Wayside_Controller:
    def __init__(self, wayside_id: str, block_ids: List[str]):
        self.wayside_id = wayside_id
        self.block_ids = [str(b) for b in (block_ids or [])]
        self._lock = threading.Lock()

        # dynamic state shared with UI
        self._selected_block: Optional[str] = None
        self._emergency = False
        self._speed_mph = 0.0
        self._authority_yds = 0
        self._occupied: set[str] = set()
        self._closed: set[str] = set()

        # outputs (dummy placeholders to mirror a real wayside)
        self._switch_state: Dict[str, str] = {}
        self._light_state: Dict[str, str] = {}
        self._gate_state: Dict[str, str] = {}

        self._failures: Dict[str, Tuple[bool, bool, bool]] = {}

        # plc/vital flags
        self.maintenance_active = False
        self._plc_loaded = False
        self._plc_name = None

        # background loop (optional: can be driven externally)
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # --------------- lifecycle (optional) ----------------

    def start(self, period_s: float = 0.1):
        if self._running:
            return
        self._running = True
        def loop():
            while self._running:
                # placeholder for periodic compute
                time.sleep(period_s)
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    # --------------- inputs from feed ----------------

    def update_from_feed(
        self,
        *, speed_mph: float, authority_yards: int, emergency: bool,
        occupied_blocks: List[str] | None = None,
        closed_blocks: List[str] | None = None,
    ):
        with self._lock:
            self._speed_mph = float(speed_mph)
            self._authority_yds = int(authority_yards)
            self._emergency = bool(emergency)
            if occupied_blocks is not None:
                self._occupied = {str(b) for b in occupied_blocks}
            if closed_blocks is not None:
                self._closed = {str(b) for b in closed_blocks}

    def apply_track_snapshot(self, snapshot: Dict[str, Any], *, limit_blocks: List[str]) -> None:
        """
        Map arrays from the track model JSON to this controller's block states.
        Only updates blocks in 'limit_blocks' (Wayside B partition).
        """
        if not isinstance(snapshot, dict):
            return

        occ = snapshot.get("G-Occupancy")
        sw = snapshot.get("G-switches")
        lt = snapshot.get("G-lights")
        gt = snapshot.get("G-gates")
        fl = snapshot.get("G-Failures")

        limit_set = set(str(b) for b in (limit_blocks or []))

        with self._lock:
            # Occupancy
            if isinstance(occ, list):
                self._occupied = {str(i) for i, v in enumerate(occ) if v and str(i) in limit_set}

            # Switches (0/1 -> Left/Right)
            if isinstance(sw, list):
                for i, v in enumerate(sw):
                    bid = str(i)
                    if bid in limit_set:
                        name = _SWITCH_NAMES.get(int(v), str(v))
                        self._switch_state[bid] = name

            # Lights (0..3 -> enum names)
            if isinstance(lt, list):
                for i, v in enumerate(lt):
                    bid = str(i)
                    if bid in limit_set:
                        name = _LIGHT_NAMES.get(int(v), str(v))
                        self._light_state[bid] = name

            # Gates (0/1 -> DOWN/UP)
            if isinstance(gt, list):
                for i, v in enumerate(gt):
                    bid = str(i)
                    if bid in limit_set:
                        name = _GATE_NAMES.get(int(v), str(v))
                        self._gate_state[bid] = name

            # Failures (flat array of len = 3*blocks)
            if isinstance(fl, list) and len(fl) >= 3:
                for i in range(0, len(fl) // 3):
                    bid = str(i)
                    if bid in limit_set:
                        f1 = bool(fl[3*i + 0])
                        f2 = bool(fl[3*i + 1])
                        f3 = bool(fl[3*i + 2])
                        self._failures[bid] = (f1, f2, f3)

    # --------------- PLC operations (no-ops by default) ----------------

    def load_plc(self, path: str) -> bool:
        # keep permissive; validate elsewhere
        self._plc_loaded = True
        self._plc_name = path
        return True

    def change_plc(self, enable: bool, *_args, **_kwargs):
        self._plc_loaded = bool(enable)

    # --------------- UI hooks ----------------

    def on_selected_block(self, block_id: str):
        with self._lock:
            self._selected_block = str(block_id)

    # --------------- getters used by the UI ----------------

    def get_block_ids(self) -> List[str]:
        return list(self.block_ids)

    def get_block_state(self, block_id: str) -> Dict[str, Any]:
        b = str(block_id)
        with self._lock:
            state = {
                "block_id": b,
                "speed_mph": self._speed_mph if b in self.block_ids else 0.0,
                "authority_yards": self._authority_yds if b in self.block_ids else 0,
                "occupied": (b in self._occupied),
                "switch": self._switch_state.get(b, "-"),
                "light": self._light_state.get(b, "-"),
                "gate": self._gate_state.get(b, "-"),
                "status": "EMERGENCY" if self._emergency else ("MAINT" if self.maintenance_active else "OK"),
            }
            if b in self._failures:
                f1, f2, f3 = self._failures[b]
                if any((f1, f2, f3)):
                    state["status"] = "EMERGENCY"
                    state["fault_block"] = b
                    state["emergency"] = True
            return state

    # ---------------- Compatibility wrappers for older HW API ----------------
    def apply_vital_inputs(self, block_ids, vital_in: Dict) -> bool:
        """Backward-compatible shim used by older UI/main code.

        Converts the older (block_ids, vital_in) into the new `update_from_feed`
        internal representation.
        """
        try:
            self.update_from_feed(
                speed_mph=float(vital_in.get("speed_mph", 0)),
                authority_yards=int(vital_in.get("authority_yards", 0)),
                emergency=bool(vital_in.get("emergency", False)),
                occupied_blocks=vital_in.get("occupied_blocks", None),
                closed_blocks=vital_in.get("closed_blocks", None),
            )
            return True
        except Exception:
            return False

    def assess_safety(self, block_ids, vital_in: Dict) -> Dict:
        """Lightweight safety report for compatibility.

        This mirrors the earlier HW behavior: it runs a simple check and
        returns a dict: {safe, reasons, actions}.
        """
        # ensure local state updated
        self.apply_vital_inputs(block_ids, vital_in)

        reasons = []
        actions = {}

        emergency = bool(vital_in.get("emergency", False))
        speed = float(vital_in.get("speed_mph", 0))
        authority = int(vital_in.get("authority_yards", 0))

        if emergency:
            reasons.append("Emergency active")
            actions["all_signals"] = "RED"

        if authority <= 0 and speed > 0:
            reasons.append("No authority but speed > 0")
            actions["speed_override"] = 0

        return {"safe": len(reasons) == 0, "reasons": reasons, "actions": actions}

    def get_block_data(self, block_id: str) -> Dict[str, Any]:
        """Compatibility wrapper returning the older block-data shape used by the UI."""
        st = self.get_block_state(block_id)
        return {
            "block_id": st.get("block_id"),
            "light": st.get("light"),
            "switch": st.get("switch"),
            "gate": st.get("gate"),
            "occupied": st.get("occupied"),
            "closed": (block_id in self._closed),
        }
    
    def build_commanded_arrays(self, n_total_blocks: int) -> Dict[str, List[int]]:
        """
        Produce arrays sized to the full Green line length for:
          - G-Commanded Switches (0/1)
          - G-Commanded Lights   (0..3)
          - G-Commanded Gates    (0/1)
        Defaults to 0 when we have no state for a block.
        """
        # inverse maps to numeric enums
        inv_switch = {"Left": 0, "Right": 1}
        inv_light = {"RED": 0, "YELLOW": 1, "GREEN": 2, "SUPERGREEN": 3}
        inv_gate = {"DOWN": 0, "UP": 1}

        cmd_switches = [0] * int(n_total_blocks)
        cmd_lights = [0] * int(n_total_blocks)
        cmd_gates = [0] * int(n_total_blocks)

        with self._lock:
            for b in self.block_ids:
                i = int(b)
                # Use our current state as the commanded value (can be replaced with PLC output later)
                s = self._switch_state.get(b)
                l = self._light_state.get(b)
                g = self._gate_state.get(b)

                if s in inv_switch:
                    cmd_switches[i] = inv_switch[s]
                if l in inv_light:
                    cmd_lights[i] = inv_light[l]
                if g in inv_gate:
                    cmd_gates[i] = inv_gate[g]

        return {
            "G-Commanded Switches": cmd_switches,
            "G-Commanded Lights": cmd_lights,
            "G-Commanded Gates": cmd_gates,
            # Intentionally leaving spelling as-is for this key; not filling it here:
            # "G-Commanded Authorty": [...]
            # "G-Commanded Speed": [...]
        }