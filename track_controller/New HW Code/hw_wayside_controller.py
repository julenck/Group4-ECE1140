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
from unittest import signals

# Optional import of your PLCs (left dynamic to avoid import errors if absent)
try:
    import Green_Line_PLC_XandLup as plc_module  # noqa: F401
except Exception:
    plc_module = None

# ------------------- Mappings for track model enums  -----------------------
_BLOCKS_WITH_SWITCHES = [13, 28, 57, 63, 77, 85]   
_BLOCKS_WITH_LIGHTS   = [0, 3, 7, 29, 58, 62, 76,
                         86, 100, 101, 150, 151]    
_BLOCKS_WITH_GATES    = [19, 108]                   

_SWITCH_NAMES     = {0: "Left", 1: "Right"}                                # CHANGED
_GATE_NAMES       = {0: "DOWN", 1: "UP"}                                   # CHANGED

def _decode_light_bits(b0: int, b1: int) -> str:
   
    code = f"{int(b0)}{int(b1)}"

    if   code == "00":
        return "SUPERGREEN"
    elif code == "01":
        return "GREEN"
    elif code == "10":
        return "YELLOW"
    elif code == "11":
        return "RED"
    return code

def _encode_light_bits(name: str) -> tuple[int, int]:
    """
    Convert a light name back to its 2-bit representation:

      SUPERGREEN -> (0, 0)
      GREEN      -> (0, 1)
      YELLOW     -> (1, 0)
      RED        -> (1, 1)
    """
    n = (name or "").upper()
    if n == "SUPERGREEN":
        return (0, 0)
    if n == "GREEN":
        return (0, 1)
    if n == "YELLOW":
        return (1, 0)
    if n == "RED":
        return (1, 1)
    # fallback: treat unknown as red for safety
    return (1, 1)

_YARD_TO_M = 0.9144


class HW_Wayside_Controller:
    def __init__(self, wayside_id: str, block_ids: List[str]):
        self.wayside_id = wayside_id
        self.block_ids = [str(b) for b in (block_ids or [])]
        self._lock = threading.Lock()

        # Vital / feed
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

        self._last_occ_array: Optional[List[int]] = None

        # Outputs/state for UI (strings)
        self._switch_state: Dict[str, str] = {}  # "Left"/"Right"
        self._light_state: Dict[str, str] = {}   # "RED"/...
        self._gate_state: Dict[str, str] = {}    # "UP"/"DOWN"

        self._cmd_switch_state: Dict[str, str] = {}  # NEW
        self._cmd_light_state: Dict[str, str] = {}   # NEW
        self._cmd_gate_state: Dict[str, str] = {}    # NEW

        # Failures: tuple of three booleans per block (f1, f2, f3)
        self._failures: Dict[str, Tuple[bool, bool, bool]] = {}

        # Train tracking (SW parity)
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
        self._train_idx: Optional[int] = None      # index into green_order
        self._train_block: Optional[str] = None    # current block as string
        self._auth_start_m: Optional[float] = None # authority at the moment we began/last reset (meters)
        self._remaining_m: Optional[float] = None  # meters to end of current block

        # Misc
        self.maintenance_active = False
        self._plc_loaded = False
        self._plc_name = None
        self._selected_block: Optional[str] = None

        # background loop (optional)
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # -------------------------- helpers --------------------------

    def _recompute_occupied(self) -> None:
        """Merge CTC occupancy, Track occupancy, and the simulated train block."""
        occ = set(self._occ_ctc) | set(self._occ_track)
        if self._train_block:
            occ.add(self._train_block)
        self._occupied = occ

    # -------------------------- lifecycle ------------------------

    def start(self, period_s: float = 0.1):
        if self._running:
            return
        self._running = True
        def loop():
            while self._running:
                time.sleep(period_s)
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    # ------------------ inputs from feed (CTC) -------------------

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
            else:
                self._authority_yds = new_auth

            self._emergency = bool(emergency)

            if occupied_blocks is not None:
                self._occ_ctc = {str(b) for b in occupied_blocks}
            if closed_blocks is not None:
                self._closed = {str(b) for b in closed_blocks}

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
                        val = int(sw[idx])
                        self._switch_state[bid] = _SWITCH_NAMES.get(val, str(val))

            # -------- Lights (24 entries = 12 × 2 bits) --------
            if isinstance(lt, list) and len(lt) == 2 * len(_BLOCKS_WITH_LIGHTS):
                for idx, block in enumerate(_BLOCKS_WITH_LIGHTS):
                    bid = str(block)
                    if bid not in limit_set:
                        continue
                    try:
                        b0 = int(lt[2 * idx])
                        b1 = int(lt[2 * idx + 1])
                    except (IndexError, ValueError):
                        continue

                    #   00 -> SUPERGREEN, 01 -> GREEN, 10 -> YELLOW, 11 -> RED
                    name = _decode_light_bits(b0, b1)
                    self._light_state[bid] = name

            # -------- Gates (2 entries) --------
            if isinstance(gt, list) and len(gt) == len(_BLOCKS_WITH_GATES):
                for idx, block in enumerate(_BLOCKS_WITH_GATES):
                    bid = str(block)
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
        self._plc_loaded = True
        self._plc_name = path
        return True

    def change_plc(self, enable: bool, *_args, **_kwargs):
        self._plc_loaded = bool(enable)

    def run_plc(self) -> None:
        if plc_module is None or not hasattr(plc_module, "process_states_green_xlup"):
            return

        with self._lock:
            occ = list(self._last_occ_array) if isinstance(self._last_occ_array, list) else None

        if not occ or len(occ) < 151:
            return

        try:
            # Match the SW controller's occupancy slicing for X&L up:
            #   occ1 = occupied[0:73]
            #   occ2 = occupied[144:151]
            occ1 = occ[0:73]
            occ2 = occ[144:151]
            plc_occ = occ1 + occ2

            switches, signals, crossing = plc_module.process_states_green_xlup(plc_occ)
        except Exception:
            return

        with self._lock:
            # reset last commanded states
            self._cmd_switch_state.clear()
            self._cmd_light_state.clear()
            self._cmd_gate_state.clear()

            # Map PLC switches: 4 entries -> first 4 switch blocks.
            for idx, val in enumerate(switches):
                if idx >= len(_BLOCKS_WITH_SWITCHES):
                    break
                bid = str(_BLOCKS_WITH_SWITCHES[idx])
                self._cmd_switch_state[bid] = _SWITCH_NAMES.get(int(val), str(val))

            # Map PLC signals: 16 bits -> 8 lights (first 8 light blocks).
            for block_idx in range(min(len(_BLOCKS_WITH_LIGHTS), len(signals) // 2)):
                bid = str(_BLOCKS_WITH_LIGHTS[block_idx])
                try:
                    b0 = int(signals[2 * block_idx])
                    b1 = int(signals[2 * block_idx + 1])
                except (IndexError, ValueError):
                    continue

                # CHANGED: same 00/01/10/11 mapping via helper
                name = _decode_light_bits(b0, b1)
                self._cmd_light_state[bid] = name

                # Map PLC crossing -> first gate block
                if crossing and _BLOCKS_WITH_GATES:
                    bid = str(_BLOCKS_WITH_GATES[0])
                    try:
                        val = int(crossing[0])
                    except Exception:
                        val = 0
                    self._cmd_gate_state[bid] = _GATE_NAMES.get(val, str(val))

    # ------------------------- UI hooks -------------------------

    def on_selected_block(self, block_id: str):
        with self._lock:
            self._selected_block = str(block_id)

    # ----------------------- UI getters -------------------------

    def get_current_train_block(self) -> Optional[str]:
        with self._lock:
            return self._train_block

    def get_block_ids(self) -> List[str]:
        return list(self.block_ids)

    def get_block_state(self, block_id: str) -> Dict[str, Any]:

        b = str(block_id)

        with self._lock:
            occupied_here = (b in self._occupied)

            # per-block speed/auth
            if b == self._train_block and b in self.block_ids:
                spd = self._speed_mph
                auth = self._authority_yds
            else:
                spd = 0.0
                auth = 0

            state = {
                "block_id": b,
                "speed_mph": spd,
                "authority_yards": auth,
                "occupied": occupied_here,
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


    # --------- Compatibility wrappers for older HW API ----------

    def apply_vital_inputs(self, block_ids, vital_in: Dict) -> bool:
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
        inv_switch = {"Left": 0, "Right": 1}
        inv_gate   = {"DOWN": 0, "UP": 1}

        # SW-style hardware arrays
        switches = [0] * len(_BLOCKS_WITH_SWITCHES)      # 6 entries
        gates    = [0] * len(_BLOCKS_WITH_GATES)         # 2 entries
        lights   = [0] * (2 * len(_BLOCKS_WITH_LIGHTS))  # 12 lights × 2 bits = 24

        # NEW: per-block speed/authority arrays (same as before)
        cmd_speed = [0] * int(n_total_blocks)
        cmd_auth  = [0] * int(n_total_blocks)

        with self._lock:
            # -------- Switches (6 entries) --------
            for idx, block in enumerate(_BLOCKS_WITH_SWITCHES):
                bid = str(block)
                # Prefer PLC commanded switch if present, else the track state
                s = self._cmd_switch_state.get(bid, self._switch_state.get(bid))
                if s in inv_switch:
                    switches[idx] = inv_switch[s]

            # -------- Gates (2 entries) --------
            for idx, block in enumerate(_BLOCKS_WITH_GATES):
                bid = str(block)
                g = self._cmd_gate_state.get(bid, self._gate_state.get(bid))
                if g in inv_gate:
                    gates[idx] = inv_gate[g]

            # -------- Lights (24 entries = 12 × 2 bits) --------
            for idx, block in enumerate(_BLOCKS_WITH_LIGHTS):
                bid = str(block)
                # Prefer PLC commanded light, fall back to track state
                name = self._cmd_light_state.get(bid, self._light_state.get(bid))
                b0, b1 = _encode_light_bits(name)
                lights[2 * idx]     = b0
                lights[2 * idx + 1] = b1

            # -------- Per-block speed/authority (unchanged semantics) ----
            if self._train_block is not None:
                try:
                    i = int(self._train_block)
                except ValueError:
                    i = -1
                if 0 <= i < int(n_total_blocks):
                    cmd_speed[i] = int(self._speed_mph)
                    cmd_auth[i]  = int(self._authority_yds)

        return {
            # SW-style I/O arrays (same shape/codes as your track_to_wayside.json)
            "G-switches": switches,
            "G-lights": lights,
            "G-gates": gates,

            # Extra info the HW wayside exports for UI / downstream logic
            "G-Commanded Speed": cmd_speed,
            "G-Commanded Authority": cmd_auth,
        }

        # ---------------- build occupancy array for CTC ----------------------  # NEW
    def build_occupancy_array(self, n_total_blocks: int) -> List[int]:
        """
        Return a 0/1 occupancy array of length n_total_blocks, where 1 means
        this block is occupied according to this controller's merged view.

        This is used by hw_main.py to combine occupancy from all waysides and
        write a single array back to CTC, just like the SW module.
        """
        arr = [0] * int(n_total_blocks)

        with self._lock:
            # self._occupied is a set of block IDs as strings
            for b in self._occupied:
                try:
                    i = int(b)
                except (TypeError, ValueError):
                    continue
                if 0 <= i < int(n_total_blocks):
                    arr[i] = 1

        return arr