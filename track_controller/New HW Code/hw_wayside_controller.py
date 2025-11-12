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

_YARD_TO_M = 0.9144

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
        self._last_auth_ts: Optional[float] = None  # for local authority decay
        self._occupied: set[str] = set()
        self._closed: set[str] = set()

        # outputs (dummy placeholders to mirror a real wayside)
        self._switch_state: Dict[str, str] = {}
        self._light_state: Dict[str, str] = {}
        self._gate_state: Dict[str, str] = {}

        self._failures: Dict[str, Tuple[bool, bool, bool]] = {}

        # ---------- Train tracking ----------
        # Full green-order path 
        self.green_order: List[int] = [
            0,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,
            85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,85,84,83,82,81,80,79,
            78,77,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,
            116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,
            133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,
            150,28,27,26,25,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10,9,8,
            7,6,5,4,3,2,1,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,
            29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,
            50,51,52,53,54,55,56,57,151
        ]
        # Distance to end-of-block (meters) indexed by position in green_order
        self.block_eob_m: List[float] = [
            100, 200, 300, 500, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 
            1700, 2000, 2300, 2600, 2900, 3200, 3500, 3800, 4100, 4400, 4500, 4586.6, 
            4686.6, 4761.6, 4836.6, 4911.6, 4986.6, 5061.6, 5136.6, 5211.6, 5286.6, 
            5361.6, 5436.6, 5511.6, 5586.6, 5886.6, 6186.6, 6486.6, 6786.6, 7086.6, 
            7386.6, 7686.6, 7986.6, 8286.6, 8361.6, 8396.6, 8496.6, 8596.6, 8676.6, 
            8776.6, 8876.6, 8966.6, 9066.6, 9166.6, 9266.6, 9366.6, 9466.6, 9566.6, 
            9728.6, 9828.6, 9928.6, 9978.6, 10028.6, 10068.6, 10118.6, 10168.6, 
            10218.6, 10268.6, 10318.6, 10368.6, 10418.6, 10468.6, 10518.6, 10568.6, 
            10618.6, 10668.6, 10718.6, 10768.6, 10818.6, 10868.6, 10918.6, 10968.6, 
            11018.6, 11068.6, 11118.6, 11168.6, 11218.6, 11268.6, 11318.6, 11368.6, 
            11418.6, 11468.6, 11652.6, 11692.6, 11727.6, 11777.6, 11827.6, 11927.6, 
            12127.6, 12427.6, 12727.6, 13027.6, 13327.6, 13477.6, 13627.6, 13777.6, 
            13927.6, 14077.6, 14227.6, 14377.6, 14527.6, 14627.6, 14727.6, 14827.6, 
            14927.6, 15027.6, 15127.6, 15227.6, 15327.6, 15427.6, 15527.6, 15627.6, 
            15727.6, 15877.6, 16027.6, 16177.6, 16327.6, 16477.6, 16627.6, 16777.6, 
            16927.6, 17227.6, 17527.6, 17827.6, 18127.6, 18327.6, 18427.6, 18477.6, 
            18527.6, 18577.6, 18627.6, 18677.6, 18727.6, 18777.6, 18827.6, 18877.6, 
            18927.6, 18977.6, 19027.6, 19077.6, 19127.6, 19177.6, 19227.6, 19277.6, 
            19327.6, 19377.6, 19427.6, 19477.6, 19527.6, 19577.6, 19627.6, 19677.6, 
            19727.6, 19777.6, 19827.6, 19877.6, 19927.6, 19977.6, 20077.6
        ]
        # Train progress state
        self._train_idx: Optional[int] = None      # index into green_order
        self._train_block: Optional[str] = None    # current block as string
        self._auth_start_m: Optional[float] = None # authority at the moment we began/last reset (meters)
        self._remaining_m: Optional[float] = None  # meters to end of current block

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

            new_auth = int(authority_yards)
            # Reset decay baseline when external authority changes
            if new_auth != self._authority_yds:
                self._authority_yds = new_auth
                self._last_auth_ts = None
                # Also reset SW-style "start authority" in meters
                self._auth_start_m = self._authority_yds * _YARD_TO_M
            else:
                self._authority_yds = new_auth
                if self._auth_start_m is None:
                    self._auth_start_m = self._authority_yds * _YARD_TO_M

            self._emergency = bool(emergency)

            if occupied_blocks is not None:
                self._occupied_source = {str(b) for b in occupied_blocks}
            if closed_blocks is not None:
                self._closed = {str(b) for b in closed_blocks}

            # Initialize train position if we don't have one yet
            if self._train_idx is None:
                self._init_train_position()

    def tick_authority_decay(self) -> None:
        """Optionally reduce authority in yards based on current speed (mph)."""
        now = time.time()
        with self._lock:
            if self._last_auth_ts is None:
                self._last_auth_ts = now
                return
            dt = now - self._last_auth_ts
            self._last_auth_ts = now

            if self._authority_yds > 0 and self._speed_mph > 0 and dt > 0:
                # mph -> yards/sec = mph * 1760 / 3600
                yards_per_sec = self._speed_mph * (1760.0 / 3600.0)
                dec = yards_per_sec * dt
                self._authority_yds = max(0, int(self._authority_yds - dec))

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

            if self._train_idx is None:
                self._init_train_position()

    # --------------- Train progress (SW parity) ----------------

    def _init_train_position(self) -> None:
        """Pick an initial block for the simulated train."""
        # Prefer any occupied block within our partition; else first block in our partition along the green order.
        candidate: Optional[int] = None

        # Try occupancy-derived start
        for b in self.block_ids:
            if b in self._occupied_source:
                candidate = int(b)
                break

        # Fallback to the first block of our partition encountered in green_order
        if candidate is None:
            limit_set = set(self.block_ids)
            for bb in self.green_order:
                if str(bb) in limit_set:
                    candidate = bb
                    break

        if candidate is None:
            return  # nothing we can do yet

        # Map to green_order index
        try:
            idx = self.green_order.index(candidate)
        except ValueError:
            return

        self._train_idx = idx
        self._train_block = str(candidate)
        # Meters remaining to end of this block
        self._remaining_m = float(self.block_eob_m[idx]) if idx < len(self.block_eob_m) else None
        # Initialize start authority if missing
        if self._auth_start_m is None:
            self._auth_start_m = self._authority_yds * _YARD_TO_M

    def tick_train_progress(self) -> None:
        """Advance the simulated train along green_order using (start_auth - current_auth) in meters."""
        with self._lock:
            if self._train_idx is None:
                self._init_train_position()
                if self._train_idx is None:
                    return

            if self._auth_start_m is None:
                self._auth_start_m = self._authority_yds * _YARD_TO_M
                return

            current_m = self._authority_yds * _YARD_TO_M
            traveled_m = max(0.0, self._auth_start_m - current_m)

            # Nothing to do if we don't have remaining distance for current block
            if self._remaining_m is None:
                # try to load it from table
                if self._train_idx < len(self.block_eob_m):
                    self._remaining_m = float(self.block_eob_m[self._train_idx])
                else:
                    return

            # Advance across blocks while we've "consumed" more than the end-of-block distance
            moved = False
            while traveled_m >= self._remaining_m - 1e-6:
                traveled_m -= self._remaining_m
                # move to next block in the ordered path if possible
                if self._train_idx + 1 >= len(self.green_order):
                    # End of route; stop advancing
                    self._remaining_m = None
                    break
                self._train_idx += 1
                next_block = self.green_order[self._train_idx]
                self._train_block = str(next_block)
                # Load new block's distance
                self._remaining_m = float(self.block_eob_m[self._train_idx]) if self._train_idx < len(self.block_eob_m) else None
                moved = True

            # Mark occupancy for UI: union of source occupancy and simulated block
            if self._train_block is not None:
                # keep source occupancy, just add our simulated current block
                occ = set(self._occupied_source)
                occ.add(self._train_block)
                self._occupied_source = occ

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

    @property
    def occupied_source(self):
        return self._occupied_source

    @occupied_source.setter
    def occupied_source(self, value):
        # accept any iterable of block ids and store as a set of strings
        self._occupied_source = {str(b) for b in (value or [])}

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