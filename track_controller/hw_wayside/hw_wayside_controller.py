#HW Wayside_Controller

from __future__ import annotations
import os
import sys

# CRITICAL: Add hw_wayside directory to path BEFORE importing local modules
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

# Now we can import local modules
from typing import Dict, Any, List, Optional, Tuple
import threading
import time
from hw_vital_check import HW_Vital_Check
import importlib.util
import json
import csv
import datetime


plc_module = None

_SWITCH_NAMES = {0: "Left", 1: "Right"} 
_GATE_NAMES = {0: "DOWN", 1: "UP"}

_YARD_TO_M = 0.9144 

# Blocks with hardware elements:
_BLOCKS_WITH_SWITCHES = [13, 28, 57, 63, 77, 85]
_BLOCKS_WITH_LIGHTS = [0, 3, 7, 29, 58, 62, 76, 86, 100, 101, 150, 151]
_BLOCKS_WITH_GATES = [19, 108]


def _encode_light_bits(name: str | None) -> Tuple[int, int]:
    """
    Map human-friendly light name -> two-bit PLC code.
      00: SUPERGREEN
      01: GREEN
      10: YELLOW
      11: RED
    """

    if not name:
        return 0, 0
    
    name = str(name).upper()

    if name == "SUPERGREEN":
        return 0, 0
    if name == "GREEN":
        return 0, 1
    if name == "YELLOW":
        return 1, 0
    
    # default / RED
    return 1, 1


class HW_Wayside_Controller:

    def __init__(self, wayside_id: str, block_ids: List[str], server_url: Optional[str] = None, timeout: float = 5.0):
        """Initialize hardware wayside controller.
        
        Args:
            wayside_id: Wayside controller ID (e.g., "A", "B", "1", "2")
            block_ids: List of block IDs controlled by this wayside
            server_url: If provided, uses REST API client to connect to remote server.
                       If None, uses local file-based I/O (default).
                       Example: "http://192.168.1.100:5000" or "http://localhost:5000"
            timeout: Network timeout in seconds for remote API (default: 5.0).
        """
        self.wayside_id = wayside_id
        self.block_ids = [str(b) for b in (block_ids or [])]
        self._lock = threading.Lock()
        
        # Initialize API client if server_url is provided (similar to HW train controller)
        self.server_url = server_url
        self.wayside_api = None
        if server_url:
            try:
                import sys
                # Add track_controller/api to path
                current_dir = os.path.dirname(os.path.abspath(__file__))
                api_dir = os.path.join(os.path.dirname(current_dir), "api")
                if api_dir not in sys.path:
                    sys.path.insert(0, api_dir)
                from wayside_api_client import WaysideAPIClient  # type: ignore[import]
                
                # Convert wayside_id to numeric (e.g., "A" -> 1, "B" -> 2)
                numeric_id = ord(wayside_id) - ord('A') + 1 if isinstance(wayside_id, str) and len(wayside_id) == 1 and wayside_id.isalpha() else int(wayside_id)
                self.wayside_api = WaysideAPIClient(wayside_id=numeric_id, server_url=server_url, timeout=timeout)
                print(f"[HW Wayside {wayside_id}] Using REST API: {server_url}")
            except Exception as e:
                print(f"[HW Wayside {wayside_id}] Warning: Failed to initialize API client: {e}")
                print(f"[HW Wayside {wayside_id}] Falling back to file-based I/O")
                self.wayside_api = None
        else:
            print(f"[HW Wayside {wayside_id}] Using file-based I/O (no server_url)")

        # Vital / feed
        self._emergency = False
        self._speed_mph = 0.0
        self._authority_yds = 0
        self._ctc_authority_yds: int = 0
        self._last_auth_ts: Optional[float] = None  # for local authority decay
        self._last_auth_m: Optional[float] = None  
        self._dist_in_block_m: float = 0.0
        self._closed: set[str] = set()

        # Occupancy sources and the merged view used everywhere
        self._occ_ctc: set[str] = set()    # from CTC (if provided)
        self._occ_track: set[str] = set()  # from Track snapshot arrays
        self._occupied: set[str] = set()   # MERGED VIEW (this is the only one used by UI)

        # Outputs/state for UI (strings coming from track model / PLC)
        self._switch_state: Dict[str, str] = {}  # "Left"/"Right"
        self._light_state: Dict[str, str] = {}   # "RED"/...
        self._gate_state: Dict[str, str] = {}    # "UP"/"DOWN"
        
        # Initialize all switches to position 0 (forward/left) on startup
        for switch_block in _BLOCKS_WITH_SWITCHES:
            self._switch_state[str(switch_block)] = '0'

        # Commanded (PLC) states that override track states when present
        self._cmd_switch_state: Dict[str, str] = {}
        self._cmd_light_state: Dict[str, str] = {}
        self._cmd_gate_state: Dict[str, str] = {}

        # Failures: tuple of three booleans per block (f1, f2, f3)
        self._failures: Dict[str, Tuple[bool, bool, bool]] = {}

        # ------------------------------------------------------------------
        # Train tracking 
        # ------------------------------------------------------------------

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
        self._plc_module = None
        self._plc_period_s = 0.2
        self._plc_timer: Optional[threading.Timer] = None
        self._plc_running = False
        self._selected_block: Optional[str] = None

        # background loop (optional; not used by hw_main.poll loop)
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Multi-train state (parity with SW controller)
        self.active_trains: Dict[str, Dict[str, Any]] = {}
        self.cmd_trains: Dict[str, Dict[str, Any]] = {}  # {"Train 1": {"cmd auth": yards, "cmd speed": mph, "pos": int}}

        # SW-compatible train tracking (add these missing structures)
        self.train_auth_start: Dict[str, int] = {}  # Starting authority for each train
        self.cumulative_distance: Dict[str, float] = {}  # Track actual distance traveled since last reset
        self.train_direction: Dict[str, str] = {}  # Track direction for each train ('forward' or 'reverse')
        self.last_seen_position: Dict[str, int] = {}  # Track last known position for handoff detection
        self.train_idx: Dict[str, int] = {}  # Track index in green_order for each train
        
        # Use absolute paths based on project root (same approach as SW controller)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))  # hw_wayside -> track_controller -> project root
        self.train_comm_file = os.path.join(project_root, "track_controller", "New_SW_Code", "wayside_to_train.json")
        self.ctc_comm_file = os.path.join(project_root, "ctc_track_controller.json")
        
        self._trains_running = False
        self._trains_timer: Optional[threading.Timer] = None

        # Track topology and distances
        self.block_graph: Dict[int, Dict[str, Any]] = {}
        self.block_distances: Dict[int, float] = {}
        self.block_lengths: Dict[int, float] = {}
        self.station_blocks: set = set()
        self.block_speed_limits: Dict[int, float] = {}  # Speed limits in m/s per block
        self.station_names: Dict[int, str] = {}  # Block -> Station name mapping

        self.direction_transitions = [

            (100, 85, 'reverse'),
            (77, 101, 'forward'),
            (1, 13, 'reverse'),
            (28, 29, 'forward')
        ]

        self._load_track_data()

        # Switch map from JSON file if present
        try:
            base = os.path.dirname(__file__)
            sm_path = os.path.join(base, 'switch_map.json')

            if os.path.exists(sm_path):

                with open(sm_path, 'r', encoding='utf-8') as f:

                    self.switch_map = json.load(f) or {}
            else:
                self.switch_map = {}
        except Exception:
            self.switch_map = {}

        # Build switch_map and gate approach lists automatically from `block_graph`
        try:
            self._build_switch_and_gate_maps()
        except Exception:
            pass

        # Per-train bookkeeping
        self.train_idx: Dict[str, int] = {}
        self.train_pos_start: Dict[str, int] = {}
        self.train_auth_start: Dict[str, float] = {}
        self.train_direction: Dict[str, str] = {}
        self.last_seen_position: Dict[str, int] = {}
        self.cumulative_distance: Dict[str, float] = {}
        self.last_ctc_authority: Dict[str, float] = {}  # Track last CTC authority for reactivation detection
        self.station_arrival_time: Dict[str, float] = {}  # Track when train stopped for 10-second dwell
        self.last_station_block: Dict[str, int] = {}  # Track last station position for beacon update
        self.file_lock = threading.Lock()
        self.trains_to_handoff = []
        
        # managed_blocks: blocks this controller writes commands for
        # visible_blocks: blocks this controller can track (extends for smooth handoffs)
        try:
            self.managed_blocks = set(int(b) for b in self.block_ids)
        except Exception:
            self.managed_blocks = set()
        
        # Extend visible_blocks for handoff overlap (can see trains slightly outside managed range)
        # HW Wayside B (XandLdown): managed 70-143, visible 67-146
        # This allows tracking trains a few blocks before/after handoff boundaries
        if self.managed_blocks:
            min_block = min(self.managed_blocks)
            max_block = max(self.managed_blocks)
            # Extend visibility by 3 blocks on each side (similar to SW Wayside 1's overlap)
            self.visible_blocks = set(range(max(0, min_block - 3), min(152, max_block + 4)))
        else:
            self.visible_blocks = set(self.managed_blocks)

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
        occupied_blocks: List[int] | List[str] | None = None,
        closed_blocks: List[int] | List[str] | None = None,
    ):
        with self._lock:
            self._speed_mph = float(speed_mph)

            # --- CHANGED: treat CTC authority separately from our decayed authority ---
            try:
                new_auth = int(authority_yards)
            except (TypeError, ValueError):
                new_auth = 0

            if new_auth != self._ctc_authority_yds:
                # CTC actually changed the command -> reset our local authority to match
                self._ctc_authority_yds = new_auth
                self._authority_yds = new_auth
                self._last_auth_ts = None
                self._auth_start_m = self._authority_yds * _YARD_TO_M

                self._last_auth_m = self._authority_yds * _YARD_TO_M
                self._dist_in_block_m = 0.0

            else:
                # CTC is still sending the same value -> KEEP our decayed authority
                if self._auth_start_m is None:
                    self._auth_start_m = self._authority_yds * _YARD_TO_M

            self._emergency = bool(emergency)

            if occupied_blocks is not None:
                self._occ_ctc = {str(b) for b in occupied_blocks}
            if closed_blocks is not None:
                self._closed = {str(b) for b in closed_blocks}

            if self._train_idx is None:
                self._init_train_position()

            self._recompute_occupied()
            # keep active_trains up-to-date when feed carries Trains (best-effort)
            try:
                raw_trains = {}
                # If incoming occupied_blocks came from CTC and included a full Trains section
                # the caller may have passed a dict in occupied_blocks; guard for that.
                # We don't rely on this, but if available, capture it.
                if isinstance(occupied_blocks, dict):
                    raw_trains = occupied_blocks.get('Trains', {}) or {}
                if raw_trains:
                    self.active_trains = raw_trains
            except Exception:
                pass

    # ---------------- local authority countdown -----------------

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

    # ------------- apply track-model snapshot arrays ------------

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
            # Occupancy from track model
            if isinstance(occ, list):
                self._occ_track = {str(i) for i, v in enumerate(occ) if v and str(i) in limit_set}

            # Switches (0/1 -> Left/Right)
            if isinstance(sw, list):
                for i, v in enumerate(sw):
                    bid = str(i)
                    if bid in limit_set:
                        self._switch_state[bid] = _SWITCH_NAMES.get(int(v), str(v))

            # Lights (PLC-like two-bit per block; we still map them to names)
            if isinstance(lt, list):
                # lt is 24 entries (12 lights × 2 bits)
                for idx, block in enumerate(_BLOCKS_WITH_LIGHTS):
                    if idx * 2 + 1 >= len(lt):
                        break
                    b0 = int(lt[2 * idx])
                    b1 = int(lt[2 * idx + 1])
                    code = f"{b0}{b1}"
                    if code == "00":
                        name = "SUPERGREEN"
                    elif code == "01":
                        name = "GREEN"
                    elif code == "10":
                        name = "YELLOW"
                    else:
                        name = "RED"
                    bid = str(block)
                    if bid in limit_set:
                        self._light_state[bid] = name

            # Gates (0/1 -> DOWN/UP)
            if isinstance(gt, list):
                for i, v in enumerate(gt):
                    if i >= len(_BLOCKS_WITH_GATES):
                        break
                    bid = str(_BLOCKS_WITH_GATES[i])
                    if bid in limit_set:
                        self._gate_state[bid] = _GATE_NAMES.get(int(v), str(v))

            # Failures (flat array of len = 3*blocks)
            if isinstance(fl, list) and len(fl) >= 3:
                count = len(fl) // 3
                for i in range(count):
                    bid = str(i)
                    if bid in limit_set:
                        f1 = bool(fl[3*i + 0]); f2 = bool(fl[3*i + 1]); f3 = bool(fl[3*i + 2])
                        self._failures[bid] = (f1, f2, f3)

            if self._train_idx is None:
                self._init_train_position()

            self._recompute_occupied()

    # ---------------- Train progress (SW parity) -----------------

    def _init_train_position(self) -> None:
        """
        Choose an initial train position based on occupied blocks in this wayside,
        projected onto the global green_order sequence.
        """
        occ_in_partition: List[int] = []
        part = set(self.block_ids)

        for b in self._occ_track:
            if b in part:
                occ_in_partition.append(int(b))
        for b in self._occ_ctc:
            if b in part:
                occ_in_partition.append(int(b))

        # If nothing is occupied, do NOT assume a train exists
        if not occ_in_partition:
            return

        try:
            # Sort occupied candidates by their index in green_order and take the earliest
            occ_in_partition.sort(key=lambda bb: self.green_order.index(bb))
            candidate = occ_in_partition[0]
            idx = self.green_order.index(candidate)
        except ValueError:
            return  # safety: if any block isn't in green_order

        self._train_idx = idx
        self._train_block = str(candidate)
        # Load distance to end-of-block
        self._remaining_m = float(self.block_eob_m[idx]) if idx < len(self.block_eob_m) else None
        if self._auth_start_m is None:
            self._auth_start_m = self._authority_yds * _YARD_TO_M

        self._last_auth_m = self._authority_yds * _YARD_TO_M
        self._dist_in_block_m = 0.0

    def tick_train_progress(self) -> None:
        """Advance the simulated train along green_order using (start_auth - current_auth) in meters."""
        with self._lock:
            # Ensure we have a starting position
            if self._train_idx is None:
                self._init_train_position()
                if self._train_idx is None:
                    return

            # Current authority in meters
            current_m = self._authority_yds * _YARD_TO_M

            # First tick: just establish baseline, don't move yet
            if self._last_auth_m is None:
                self._last_auth_m = current_m
                return

            # Distance implied by authority drop since last tick
            delta_m = max(0.0, self._last_auth_m - current_m)
            self._last_auth_m = current_m

            if delta_m <= 0.0:
                return  # authority not decreasing -> no forward motion

            # Helper: get the length of the current block in meters
            def block_len_for(idx: int) -> float:
                if idx <= 0:
                    return float(self.block_eob_m[0])
                if idx < len(self.block_eob_m):
                    return float(self.block_eob_m[idx] - self.block_eob_m[idx - 1])
                return 0.0

            # Add this tick's distance to our progress inside the current block
            self._dist_in_block_m += delta_m

            moved = False
            # Step forward as long as we've "used up" this block
            while True:
                if self._train_idx is None or self._train_idx >= len(self.green_order):
                    break

                cur_block_len = block_len_for(self._train_idx)
                if cur_block_len <= 0.0:
                    break

                if self._dist_in_block_m + 1e-6 < cur_block_len:
                    # Haven't finished the current block yet
                    break

                # Consume one block length and advance
                self._dist_in_block_m -= cur_block_len

                if self._train_idx + 1 >= len(self.green_order):
                    # Reached end of path
                    self._train_idx = len(self.green_order) - 1
                    self._train_block = str(self.green_order[self._train_idx])
                    self._dist_in_block_m = 0.0
                    moved = True
                    break

                self._train_idx += 1
                self._train_block = str(self.green_order[self._train_idx])
                moved = True

            # Recompute occupancy so UI reflects the current train block
            if moved:
                self._recompute_occupied()

    def traveled_enough(self, sug_auth: int, cmd_auth: int, idx: int, train_id: str) -> bool:
        """Check if train has traveled far enough to move to the next block"""
        # Calculate distance traveled since activation/reset
        traveled = sug_auth - cmd_auth

        # Get cumulative distance that needs to be traveled to complete current block
        cumulative = self.cumulative_distance.get(train_id, 0)

        # Get current block length
        if train_id in self.cmd_trains:
            current_block = self.cmd_trains[train_id]["pos"]
            current_block_length = self.block_lengths.get(current_block, 100)
        else:
            current_block_length = 100

        # Total distance needed to complete current block
        distance_needed = cumulative + current_block_length

        # Move to next block only if traveled distance EXCEEDS distance needed
        return traveled > distance_needed

    def get_next_block(self, current_block: int, block_idx: int, train_id: str):
        """Get next block based on current block, train direction, and switch state."""
        self.occupied_blocks[current_block] = 0

        if current_block not in self.block_graph:
            # Fallback to green_order if block not in graph
            if current_block == 151:
                self.train_idx[train_id] = 0
                return -1
            else:
                if block_idx + 1 < len(self.green_order):
                    next_block = self.green_order[block_idx + 1]
                    self.occupied_blocks[next_block] = 1
                    return next_block
                return -1

        # Check if this block has a switch and use switch_map to determine routing
        block_key = str(current_block)
        switch_map_entry = self.switch_map.get(block_key, None)
        
        if switch_map_entry:
            # This block has a switch - check current switch state
            # Prefer commanded state over track state
            switch_state = self._cmd_switch_state.get(block_key, 
                          self._switch_state.get(block_key, '0'))
            
            # Normalize switch state to '0' or '1'
            if isinstance(switch_state, str):
                if switch_state.upper().startswith('L') or switch_state == '0':
                    switch_pos = '0'
                elif switch_state.upper().startswith('R') or switch_state == '1':
                    switch_pos = '1'
                else:
                    # Try to parse as block number and map back to position
                    try:
                        target_block = int(switch_state)
                        if switch_map_entry.get('0') == target_block:
                            switch_pos = '0'
                        elif switch_map_entry.get('1') == target_block:
                            switch_pos = '1'
                        else:
                            switch_pos = '0'  # Default to forward
                    except (ValueError, TypeError):
                        switch_pos = '0'
            else:
                switch_pos = str(switch_state) if switch_state in ['0', '1'] else '0'
            
            # Get next block from switch map
            next_block = switch_map_entry.get(switch_pos, -1)
            if next_block and next_block != -1:
                print(f"[HW Wayside {self.wayside_id}] Train {train_id} at switch block {current_block}: switch={switch_pos} -> block {next_block}")
                self.occupied_blocks[next_block] = 1
                return next_block
        
        # No switch or switch map failed - use block_graph direction logic
        direction = self.train_direction.get(train_id, 'forward')
        block_info = self.block_graph[current_block]

        if direction == 'forward':
            next_block = block_info['forward_next']
        else:
            next_block = block_info['reverse_next']

        # Check for direction transition points
        for from_block, to_block, new_direction in self.direction_transitions:
            if current_block == from_block and next_block == to_block:
                self.train_direction[train_id] = new_direction
                break

        if next_block == -1:
            # End of line, reset or switch direction if bidirectional
            if block_info['bidirectional']:
                self.train_direction[train_id] = 'reverse' if direction == 'forward' else 'forward'
            self.train_idx[train_id] = 0
            return -1

        self.occupied_blocks[next_block] = 1
        return next_block

    # ------------------ CTC inputs (multi-train) -------------------

    def load_ctc_inputs(self) -> None:
        """Read CTC commands (via API or from ctc_track_controller.json) and populate `self.active_trains`.

        This reads the CTC-supplied train information (Active, Suggested Authority, Suggested Speed, Train Position).
        """
        # Use API client if available, otherwise file I/O
        if self.wayside_api:
            try:
                ctc_commands = self.wayside_api.get_ctc_commands()
                if ctc_commands:
                    # API returns data in expected format
                    trains = ctc_commands.get("Trains", {})
                    # Ensure expected keys exist for robustness
                    for tname, tinfo in list(trains.items()):
                        if not isinstance(tinfo, dict):
                            trains[tname] = {}
                            tinfo = trains[tname]
                        tinfo.setdefault('Train Position', 0)
                        tinfo.setdefault('Active', 0)
                        tinfo.setdefault('Suggested Authority', 0)
                        tinfo.setdefault('Suggested Speed', 0)
                    self.active_trains = trains
                    return
                # else fall through to file I/O
            except Exception as e:
                print(f"[HW Wayside {self.wayside_id}] API load_ctc_inputs failed: {e}, falling back to file I/O")
        
        # Legacy file I/O (fallback or when API not available)
        try:
            if not os.path.exists(self.ctc_comm_file):
                return
            with open(self.ctc_comm_file, 'r', encoding='utf-8') as f:
                data = json.load(f) or {}
            trains = data.get('Trains', {}) or {}
            # Ensure expected keys exist for robustness
            for tname, tinfo in list(trains.items()):
                if not isinstance(tinfo, dict):
                    trains[tname] = {}
                    tinfo = trains[tname]
                tinfo.setdefault('Train Position', 0)
                tinfo.setdefault('Active', 0)
                tinfo.setdefault('Suggested Authority', 0)
                tinfo.setdefault('Suggested Speed', 0)
            self.active_trains = trains
        except Exception:
            pass

    def _load_track_data(self):
        """Load track data from CSV file: section, block_num, length, bidirectional, forward_next, reverse_next, etc.
        
        CSV columns (matching SW format):
        0: section, 1: block_num, 2: length, 3: bidirectional, 4: forward_next, 5: reverse_next,
        6: has_station, 7: speed_mph, 8: speed_m/s, 
        9: fwd_has_beacon, 10: fwd_current_station, 11: fwd_next_station,
        12: rev_has_beacon, 13: rev_current_station, 14: rev_next_station
        """
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            csv_path = os.path.join(current_dir, 'track_data.csv')
            
            if not os.path.exists(csv_path):
                self._load_fallback_data()
                return
            
            cumulative_distance = 0.0
            
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                
                for row in reader:
                    if len(row) < 6:
                        continue
                    
                    section = row[0]
                    block_num = row[1]
                    length = row[2]
                    bidirectional = row[3]
                    forward_next = row[4]
                    reverse_next = row[5]
                    has_station = row[6] if len(row) > 6 else '0'
                    speed_limit_ms = row[8] if len(row) > 8 else '0'  # 9th column (index 8) for speed limit in m/s
                    
                    # Beacon data for forward direction (columns 10, 11, 12 -> indices 9, 10, 11)
                    forward_has_beacon = row[9] if len(row) > 9 else '0'
                    forward_current_station = row[10] if len(row) > 10 else ''
                    forward_next_station = row[11] if len(row) > 11 else ''
                    
                    # Beacon data for reverse direction (columns 13, 14, 15 -> indices 12, 13, 14)
                    reverse_has_beacon = row[12] if len(row) > 12 else '0'
                    reverse_current_station = row[13] if len(row) > 13 else ''
                    reverse_next_station = row[14] if len(row) > 14 else ''
                    
                    if block_num and block_num.strip():
                        try:
                            block_num = int(block_num)
                            length = float(length) if length else 0
                            cumulative_distance += length
                            
                            # Check if this block has a station
                            if has_station.strip() == '1':
                                self.station_blocks.add(block_num)
                            
                            # Parse speed limit (default to 19.44 m/s if not provided)
                            try:
                                speed_limit = float(speed_limit_ms) if speed_limit_ms and speed_limit_ms.strip() else 19.44
                            except ValueError:
                                speed_limit = 19.44
                            self.block_speed_limits[block_num] = speed_limit
                            
                            # Convert next blocks to int or -1 if empty/none
                            if forward_next and forward_next.strip().lower() not in ['', 'none', '-1']:
                                forward_next = int(forward_next)
                            else:
                                forward_next = -1
                                
                            if reverse_next and reverse_next.strip().lower() not in ['', 'none', '-1']:
                                reverse_next = int(reverse_next)
                            else:
                                reverse_next = -1
                            
                            self.block_graph[block_num] = {
                                'length': length,
                                'forward_next': forward_next,
                                'reverse_next': reverse_next,
                                'bidirectional': bidirectional.strip().upper() == 'TRUE',
                                'cumulative_distance': cumulative_distance,
                                'speed_limit_ms': speed_limit,
                                'forward_beacon': {
                                    'has_beacon': forward_has_beacon.strip() == '1',
                                    'current_station': forward_current_station.strip(),
                                    'next_station': forward_next_station.strip()
                                },
                                'reverse_beacon': {
                                    'has_beacon': reverse_has_beacon.strip() == '1',
                                    'current_station': reverse_current_station.strip(),
                                    'next_station': reverse_next_station.strip()
                                }
                            }
                            self.block_distances[block_num] = cumulative_distance
                            self.block_lengths[block_num] = length
                            
                            # Store station name from beacon data if available
                            if forward_current_station.strip():
                                self.station_names[block_num] = forward_current_station.strip()
                            elif reverse_current_station.strip():
                                self.station_names[block_num] = reverse_current_station.strip()
                                
                        except ValueError:
                            continue
            
        except Exception as e:
            print(f"Error loading track data from CSV: {e}")
            self._load_fallback_data()

    def _load_fallback_data(self):
        # Minimal fallback to populate block_graph and distances using existing green_order
        cum = 0.0
        for i, b in enumerate(self.green_order):
            length = 100.0
            cum += length
            self.block_graph[b] = {'length': length, 'forward_next': self.green_order[i+1] if i+1 < len(self.green_order) else -1, 'reverse_next': -1, 'bidirectional': False, 'cumulative_distance': cum}
            self.block_lengths[b] = length
            self.block_distances[b] = cum

    def _build_switch_and_gate_maps(self):
        """Derive `switch_map` and `gate_approach_map` from `block_graph`.

        - `switch_map[block] = {'0': forward_next, '1': reverse_next}` if available.
        - `gate_approach_map[block] = [pred1, pred2, ...]` where predecessors
          are blocks that point at the gate block via forward_next/reverse_next.
        This function writes `switch_map.json` if we generated entries.
        """
        base = os.path.dirname(__file__)
        # Build gate approach map
        gate_map: Dict[str, List[str]] = {}
        for g in _BLOCKS_WITH_GATES:
            preds: List[str] = []
            for blk, info in self.block_graph.items():
                try:
                    fn = info.get('forward_next')
                    rn = info.get('reverse_next')
                    if fn == g or rn == g:
                        preds.append(str(blk))
                except Exception:
                    continue
            gate_map[str(g)] = preds
        self.gate_approach_map = gate_map

        # Build switch map from graph for any missing entries
        generated = False
        try:
            for s in _BLOCKS_WITH_SWITCHES:
                key = str(s)
                if key in self.switch_map and self.switch_map.get(key):
                    continue
                entry = {}
                info = self.block_graph.get(s, {})
                fwd = info.get('forward_next')
                rev = info.get('reverse_next')
                if isinstance(fwd, int) and fwd >= 0:
                    entry['0'] = int(fwd)
                if isinstance(rev, int) and rev >= 0:
                    entry['1'] = int(rev)
                if entry:
                    self.switch_map[key] = entry
                    generated = True
        except Exception:
            generated = False

        # Persist generated switch_map if we created entries and no file existed
        try:
            sm_path = os.path.join(base, 'switch_map.json')
            if generated:
                with open(sm_path, 'w', encoding='utf-8') as f:
                    json.dump(self.switch_map, f, indent=2)
        except Exception:
            pass

    def dist_to_EOB(self, idx: int) -> float:
        if 0 <= idx < len(self.green_order):
            block = self.green_order[idx]
            return self.block_lengths.get(block, 0)
        return 0.0

    def traveled_enough(self, sug_auth: float, cmd_auth: float, idx: int, train_id: str) -> bool:
        # Compute distance traveled since activation
        traveled = float(sug_auth) - float(cmd_auth)
        cumulative = self.cumulative_distance.get(train_id, 0.0)
        # current block length
        if train_id in self.cmd_trains:
            current_block = self.cmd_trains[train_id]['pos']
            current_block_length = self.block_lengths.get(current_block, 100.0)
        else:
            current_block_length = 100.0
        distance_needed = cumulative + current_block_length
        # Changed from > to >= to move exactly when distance is reached, not after overshooting
        return traveled >= distance_needed

    def get_next_block(self, current_block: int, block_idx: int, train_id: str):
        # mark old block unoccupied in our local view
        try:
            if 0 <= current_block < len(self.block_lengths):
                pass
        except Exception:
            pass

        if current_block not in self.block_graph:
            # fallback using green_order
            if current_block == 151:
                self.train_idx[train_id] = 0
                return -1
            else:
                if block_idx + 1 < len(self.green_order):
                    next_block = self.green_order[block_idx + 1]
                    return next_block
                return -1

        direction = self.train_direction.get(train_id, 'forward')
        block_info = self.block_graph[current_block]
        if direction == 'forward':
            next_block = block_info.get('forward_next', -1)
        else:
            next_block = block_info.get('reverse_next', -1)

        for from_block, to_block, new_direction in self.direction_transitions:
            if current_block == from_block and next_block == to_block:
                self.train_direction[train_id] = new_direction
                break

        if next_block == -1:
            if block_info.get('bidirectional'):
                self.train_direction[train_id] = 'reverse' if direction == 'forward' else 'forward'
            self.train_idx[train_id] = 0
            return -1

        return next_block

    # ------------------ multi-train processing loop -----------------

    def start_trains(self, period_s: float = 1.0):
        """Start the periodic train processing loop."""
        self._trains_period = float(period_s)
        if self._trains_running:
            return
        self._trains_running = True
        self._schedule_trains_tick()

    def stop_trains(self):
        self._trains_running = False
        if self._trains_timer:
            try:
                self._trains_timer.cancel()
            except Exception:
                pass
            self._trains_timer = None

    def _schedule_trains_tick(self):
        if not self._trains_running:
            return
        self._trains_timer = threading.Timer(self._trains_period, self._run_trains_tick)
        self._trains_timer.daemon = True
        self._trains_timer.start()

    def _run_trains_tick(self):
        """SW-compatible train processing logic"""
        try:
            # Load CTC inputs and actual train speeds (matching SW behavior)
            self.load_ctc_inputs()
            actual_train_speeds = self.load_train_speeds()

            to_remove = []

            # First pass: clear occupied blocks for trains that have left our visible range
            for train in self.active_trains:
                train_pos = self.active_trains[train]["Train Position"]
                # If train is outside our visible range and we have it marked as occupied somewhere, clear it
                if train_pos not in self.visible_blocks and train_pos != 0:
                    # Check if we were tracking this train and need to clear its old position
                    if train in self.last_seen_position:
                        last_pos = self.last_seen_position[train]
                        if last_pos in self.visible_blocks and 0 <= last_pos < len(self.occupied_blocks):
                            if self.occupied_blocks[last_pos] == 1:
                                self.occupied_blocks[last_pos] = 0

            for train in self.active_trains:
                if train not in self.cmd_trains and self.active_trains[train]["Active"]==1:
                    # Initialize handoff data variables (will be set if handoff occurs)
                    stored_cumulative = 0.0
                    stored_auth_start_m = 0.0
                    train_pos = self.active_trains[train]["Train Position"]
                    sug_auth = self.active_trains[train]["Suggested Authority"]

                    # Always update last seen position for tracking
                    current_last_pos = self.last_seen_position.get(train, 0)

                    # Skip trains not in our managed section
                    # Only Controller 1 (XandLup) manages yard (block 0) - ALL trains start from yard
                    if train_pos == 0 and self.wayside_id != "A":
                        # Controller 2 should not pick up trains from yard
                        self.last_seen_position[train] = train_pos
                        continue

                    # If train is at yard (block 0), ONLY Controller 1 should activate it
                    # Controller 2 should never activate a train at block 0
                    if train_pos == 0:
                        # Additional check: ensure we're Controller 1
                        if self.wayside_id != "A":
                            self.last_seen_position[train] = train_pos
                            continue

                    if train_pos not in self.managed_blocks and train_pos != 0:
                        # Update last seen position even if we're not managing it
                        self.last_seen_position[train] = train_pos
                        continue

                    if train_pos != 0:
                        # Check if this is a handoff from another controller
                        # If train was outside our managed section and is now inside, pick it up
                        last_in_our_section = current_last_pos in self.managed_blocks or current_last_pos == 0
                        now_in_our_section = train_pos in self.managed_blocks
                        is_handoff = not last_in_our_section and now_in_our_section and current_last_pos != 0

                        if not is_handoff:
                            # Not a handoff - apply normal activation rules
                            # Only activate if:
                            # 1. Fresh dispatch from station with authority increase
                            # 2. Train is at a station block (valid starting point)

                            if train_pos not in self.station_blocks and len(self.station_blocks) > 0:
                                # Train is mid-track (not at a station), not a handoff - skip to avoid authority reset
                                self.last_seen_position[train] = train_pos
                                continue

                            # Even if at a station, check if it's a fresh dispatch or just passing through
                            # If we just saw this train at a different position, it's in transit - don't reactivate
                            if current_last_pos != 0 and current_last_pos != train_pos:
                                # Train was already moving and entered this station
                                # This is NOT a fresh dispatch, so skip to avoid reactivation
                                self.last_seen_position[train] = train_pos
                                continue

                            # If train hasn't moved since we last saw it, check if authority has increased (new dispatch)
                            if current_last_pos == train_pos:
                                # Train is stationary at same position
                                # Check if this is a new dispatch by comparing authority
                                last_auth = self.train_auth_start.get(train, 0)
                                if sug_auth <= last_auth:
                                    # Authority hasn't increased - train is just waiting, don't reactivate
                                    continue
                                # Authority increased - this is a new dispatch, proceed with activation below

                    # CTC sends authority in YARDS and speed in MPH
                    sug_auth_yds = float(self.active_trains[train].get('Suggested Authority', 0) or 0)  # yards
                    sug_auth_m = sug_auth_yds * 0.9144  # Convert yards to meters for internal use
                    sug_speed_mph = float(self.active_trains[train].get('Suggested Speed', 0) or 0)  # mph
                    sug_speed_ms = sug_speed_mph * 0.44704  # Convert mph to m/s for internal use

                    # Determine if this is a handoff: last seen outside our managed_blocks and now inside
                    # OR if we've never seen this train before but it's now in our range (first pickup)
                    current_last = self.last_seen_position.get(train, None)
                    
                    # Check if this is a handoff or first-time pickup
                    now_in_section = (train_pos in self.managed_blocks)
                    
                    if current_last is None:
                        # First time seeing this train - check if it's coming from outside our range
                        # This is a handoff if the train is in our section but we never tracked it
                        is_handoff = now_in_section and train_pos != 0
                        print(f"[HW Wayside {self.wayside_id}] First time seeing {train} at {train_pos}, is_handoff={is_handoff}")
                    else:
                        last_in_section = (current_last in self.managed_blocks) or (current_last == 0)
                        is_handoff = (not last_in_section) and now_in_section and current_last != 0
                        print(f"[HW Wayside {self.wayside_id}] {train}: last_pos={current_last}, current_pos={train_pos}, last_in_section={last_in_section}, now_in_section={now_in_section}, is_handoff={is_handoff}")

                    if is_handoff:
                        # Read prior controller outputs (wayside_to_train) to obtain remaining auth/speed
                        print(f"[HW Wayside {self.wayside_id}] Taking over train {train} via handoff at block {train_pos}")
                        try:
                            with open(self.train_comm_file, 'r', encoding='utf-8') as f:
                                train_data = json.load(f)
                                # File stores in mph/yards, convert to m/s and meters
                                current_auth_yds = train_data.get(train, {}).get('Commanded Authority', sug_auth_m * 1.09361)
                                current_speed_mph = train_data.get(train, {}).get('Commanded Speed', sug_speed_mph)
                                current_auth = float(current_auth_yds) * 0.9144  # yards to meters
                                current_speed = float(current_speed_mph) * 0.44704  # mph to m/s

                                # Read stored cumulative distance and auth start for accurate handoff
                                stored_cumulative = train_data.get(train, {}).get('Cumulative Distance', 0)
                                stored_auth_start = train_data.get(train, {}).get('Train Auth Start', current_auth)
                                stored_auth_start_m = float(stored_auth_start) * 0.9144  # yards to meters

                                print(f"[HW Wayside {self.wayside_id}] Read handoff data for {train}: speed={current_speed_mph:.1f} mph ({current_speed:.2f} m/s), auth={current_auth_yds:.0f} yards ({current_auth:.0f} m), cumulative={stored_cumulative:.0f}m, auth_start={stored_auth_start_m:.0f}m")
                        except Exception as e:
                            print(f"[HW Wayside {self.wayside_id}] Failed to read handoff data for {train}, using CTC values: {e}")
                            current_auth = sug_auth_m
                            current_speed = sug_speed_ms
                            stored_cumulative = 0
                            stored_auth_start_m = sug_auth_m  # Use current CTC value as fallback
                        auth_to_use = float(current_auth)
                        speed_to_use = float(current_speed)
                        # Subtract 20m from handoff authority to compensate for 1-second delay overshoot
                        auth_to_use = max(0, auth_to_use - 20.0)
                        print(f"[HW Wayside {self.wayside_id}] Handoff authority adjusted: {current_auth:.0f}m -> {auth_to_use:.0f}m (compensating for lag)")
                    else:
                        auth_to_use = float(sug_auth_m)  # meters
                        speed_to_use = float(sug_speed_ms)  # m/s

                    # Initialize commanded train entry
                    self.cmd_trains[train] = {
                        'cmd auth': auth_to_use,
                        'cmd speed': speed_to_use,
                        'pos': train_pos,
                    }

                    print(f"[HW Wayside {self.wayside_id}] Activated train {train} at block {train_pos} (speed: {speed_to_use:.2f} m/s, auth: {auth_to_use:.0f} m, handoff: {is_handoff})")
                    if is_handoff:
                        print(f"[HW Wayside {self.wayside_id}] Handoff details: stored_cumulative={stored_cumulative:.0f}m, stored_auth_start={stored_auth_start_m:.0f}m")

                    # Track CTC authority for reactivation detection (matching SW behavior)
                    self.last_ctc_authority[train] = auth_to_use

                    # Initialize per-train tracking
                    if train_pos in self.green_order:
                        self.train_idx[train] = self.green_order.index(train_pos)
                    else:
                        self.train_idx[train] = 0
                    self.train_pos_start[train] = self.train_idx[train]
                    # For handoff, use the stored cumulative distance from the previous controller
                    if is_handoff:
                        # Use the stored values from the handoff data instead of calculating
                        self.train_auth_start[train] = stored_auth_start_m
                        self.cumulative_distance[train] = stored_cumulative
                        print(f"[HW Wayside {self.wayside_id}] Using stored handoff data for {train}: auth_start={stored_auth_start_m:.0f}m, cumulative_distance={stored_cumulative:.0f}m")
                    else:
                        self.train_auth_start[train] = auth_to_use  # meters
                        # Initialize cumulative distance heuristics
                        if train_pos == 0:
                            self.cumulative_distance[train] = 0.0
                        elif train_pos in self.station_blocks:
                            # At a station: assume train is at START of block (just finished dwelling)
                            # This gives accurate authority calculation for next station
                            self.cumulative_distance[train] = 0.0
                        else:
                            # Mid-track: assume at end of current block
                            self.cumulative_distance[train] = -float(self.block_lengths.get(train_pos, 100))

                    self.last_seen_position[train] = train_pos
                    
                    # Mark block as occupied (matching SW behavior)
                    self._occupied.add(str(train_pos))

            # Now update each commanded train: decrement authority, possibly move, write outputs
            to_remove = []
            for tname, state in list(self.cmd_trains.items()):
                auth = float(state.get('cmd auth', 0.0))
                speed = float(state.get('cmd speed', 0.0))
                pos = int(state.get('pos', 0))
                
                # Check CTC active status and handle deactivation/reactivation (matching SW behavior)
                tinfo = self.active_trains.get(tname, {})
                is_active = int(tinfo.get('Active', 0) or 0)
                
                if is_active == 0 and tname in self.cmd_trains:
                    # CTC deactivated train - set speed and authority to 0
                    state['cmd auth'] = 0.0
                    state['cmd speed'] = 0.0
                    # Reset last_ctc_authority so ANY new authority from CTC will trigger reactivation
                    self.last_ctc_authority[tname] = 0.0
                    # Don't remove from cmd_trains yet - CTC may reactivate with new authority
                    continue
                elif is_active == 1 and state.get('cmd auth', 0) == 0:
                    # Train has exhausted authority but CTC shows active - check for reactivation
                    new_auth_yds = float(tinfo.get('Suggested Authority', 0) or 0)  # CTC sends in YARDS
                    new_auth = new_auth_yds * 0.9144  # Convert to meters for comparison
                    last_auth = self.last_ctc_authority.get(tname, 0)
                    destination = str(tinfo.get('Station Destination', '') or '').lower()
                    
                    # Check if at destination - stop permanently
                    if pos in [96, 97] and 'castle shannon' in destination:
                        # At Castle Shannon destination - keep stopped
                        state['cmd auth'] = 0.0
                        state['cmd speed'] = 0.0
                        continue
                    
                    # IGNORE CTC authority - use station-specific calculated authority instead
                    # CTC's authority is often wrong or stale
                    if True:  # Always reactivate after dwell, ignoring CTC authority value
                        # Enforce 10-second dwell at stations
                        import time
                        current_time = time.time()
                        stop_time = self.station_arrival_time.get(tname, 0)
                        
                        if stop_time == 0:
                            # Just stopped - record time
                            self.station_arrival_time[tname] = current_time
                            continue
                        elif (current_time - stop_time) < 10.0:
                            # Still dwelling - wait
                            continue
                        
                        # Dwell complete - give exact authority to reach END of NEXT station block
                        self.station_arrival_time[tname] = 0
                        new_speed = float(tinfo.get('Suggested Speed', 0) or 0) * 0.44704  # mph to m/s
                        
                        # CRITICAL: Train stopped partway through current block when authority exhausted
                        # cumulative_distance should be 0 (no blocks completed yet in this new authority grant)
                        # Authority calculation must include FINISHING current block, then reaching destination
                        self.cumulative_distance[tname] = 0.0
                        
                        current_block_length = float(self.block_lengths.get(pos, 100))
                        
                        # Determine which station segment we're on based on position
                        if pos <= 76:
                            # Stopped at block 73, 74, 75, or 76 - heading to Mt Lebanon (77)
                            # Need: finish current block + all blocks to END of 77
                            if pos == 73:
                                needed = 100 + 100 + 100 + 300  # 73 + 74 + 75 + 76 + 77 = 600m
                            elif pos == 74:
                                needed = 100 + 100 + 100 + 300  # 74 + 75 + 76 + 77 = 600m
                            elif pos == 75:
                                needed = 100 + 100 + 300  # 75 + 76 + 77 = 500m
                            elif pos == 76:
                                needed = 100 + 300  # 76 + 77 = 400m
                            else:
                                needed = 500.0
                            calculated_auth = needed
                            
                        elif pos <= 87:
                            # Stopped at blocks 77-87 - heading to Poplar (88)
                            # N-section blocks are 300m each
                            if pos == 77:
                                needed = 300 + 300*8 + 100 + 86.6 + 100  # 77 + (78-85) + 86 + 87 + 88
                            elif pos == 78:
                                needed = 300 + 300*7 + 100 + 86.6 + 100  # 78 + (79-85) + 86 + 87 + 88
                            else:
                                # Calculate remaining distance dynamically
                                remaining_300m_blocks = max(0, 85 - pos) + 1  # blocks from pos to 85 inclusive
                                needed = 300 * remaining_300m_blocks + 100 + 86.6 + 100  # + blocks 86, 87, 88
                            calculated_auth = needed + 50.0  # Small buffer
                            
                        elif pos <= 97:
                            # Stopped at blocks 88-97 - heading to Castle Shannon (96)
                            # These blocks are 75-100m each
                            if pos == 88:
                                needed = 100 + 75*8  # 88 + (89-96)
                            else:
                                remaining = max(0, 96 - pos) + 1
                                needed = remaining * 75.0
                            calculated_auth = needed + 50.0
                        else:
                            calculated_auth = 600.0
                        
                        state['cmd auth'] = calculated_auth
                        state['cmd speed'] = new_speed
                        self.train_auth_start[tname] = calculated_auth
                        self.last_ctc_authority[tname] = 0.0
                        auth = calculated_auth
                        speed = new_speed
                        
                        # Record station block when leaving for beacon update
                        self.last_station_block[tname] = pos

                # BLOCK CTC authority updates during travel to prevent mid-journey authority injection
                # Authority is ONLY set during reactivation after station stops

                # Use actual speed from train model if available (m/s), else fall back to cmd speed
                actual_speed = actual_train_speeds.get(tname, speed)

                # Get block speed limit (matching SW controller behavior)
                speed_limit = self.block_speed_limits.get(pos, 19.44)  # Default ~43 mph in m/s

                # Speed control with deceleration zone to prevent overshooting
                if auth <= 5:
                    target_speed = 0
                elif auth < 50:
                    target_speed = 5.0  # Very slow final approach
                elif auth < 150:
                    # Deceleration zone - slow down as approaching station
                    # At 150m: 15 m/s (~33mph), at 100m: 10 m/s (~22mph), at 50m: 5 m/s
                    target_speed = min(speed_limit, auth * 0.10)
                else:
                    target_speed = speed_limit
                
                # COLLISION PREVENTION: Check for trains ahead and reduce speed if needed
                SAFETY_DISTANCE = 400.0  # meters - minimum safe distance between trains
                CRITICAL_DISTANCE = 200.0  # meters - must stop if train this close
                train_ahead = False
                for other_train, other_state in self.cmd_trains.items():
                    if other_train == tname:
                        continue
                    other_pos = other_state.get('pos', -1)
                    other_speed = other_state.get('cmd speed', 0)
                    # Check if other train is ahead of us in green_order
                    try:
                        our_idx = self.train_idx.get(tname, 0)
                        other_idx = self.train_idx.get(other_train, -1)
                        if other_idx > our_idx and other_idx - our_idx <= 5:  # Within 5 blocks
                            # Calculate approximate distance to other train
                            distance_to_other = 0.0
                            for i in range(our_idx, min(other_idx, len(self.green_order))):
                                block_id = self.green_order[i]
                                distance_to_other += self.block_lengths.get(block_id, 100.0)
                            
                            if distance_to_other < CRITICAL_DISTANCE or (distance_to_other < SAFETY_DISTANCE and other_speed < 1.0):
                                # Critical: stop if train ahead is very close or stopped nearby
                                target_speed = 0
                                train_ahead = True
                                print(f"[HW Wayside {self.wayside_id}] COLLISION AVOID: Train {tname} stopping - train {other_train} ahead at {distance_to_other:.0f}m")
                                break
                            elif distance_to_other < SAFETY_DISTANCE:
                                # Warning: slow down if train ahead within safety distance
                                target_speed = min(target_speed, 5.0)
                                train_ahead = True
                                break
                    except Exception:
                        pass
                
                # Smoothly adjust commanded speed toward target
                ACCEL_RATE = 2.0  # m/s per tick acceleration
                DECEL_RATE = 5.0  # m/s per tick deceleration
                
                if speed < target_speed:
                    speed = min(speed + ACCEL_RATE, target_speed)
                elif speed > target_speed:
                    speed = max(speed - DECEL_RATE, target_speed)
                
                state['cmd speed'] = speed

                # Decrement authority by distance traveled (matching SW logic)
                # Speed is in m/s, so distance per tick (1 second) = speed
                if actual_speed > 0:
                    distance_traveled = actual_speed  # meters per second
                    auth = auth - distance_traveled
                    if auth < 5:
                        auth = 0
                    # Update state immediately so UI sees decreasing authority
                    state['cmd auth'] = auth

                # CRITICAL: Check authority exhaustion BEFORE allowing movement
                # This prevents train from moving to next block then immediately stopping
                if auth <= 0:
                    auth = 0.0
                    state['cmd auth'] = 0.0
                    state['cmd speed'] = 0.0
                    continue

                # Track movement: check whether train traveled enough to move to next block
                sug_auth = self.train_auth_start.get(tname, 0.0)
                idx = self.train_idx.get(tname, 0)
                should_move = self.traveled_enough(sug_auth, auth, idx, tname)

                if should_move:
                    new_pos = self.get_next_block(pos, idx, tname)
                    if new_pos == -1:
                        # Reached end of line: deactivate and cleanup (similar to authority exhaustion)
                        max_retries = 3
                        for retry in range(max_retries):
                            try:
                                with self.file_lock:
                                    if not os.path.exists(self.ctc_comm_file):
                                        break
                                    with open(self.ctc_comm_file, 'r', encoding='utf-8') as f:
                                        data = json.load(f)
                                    data.setdefault('Trains', {})
                                    data['Trains'].setdefault(tname, {})
                                    data['Trains'][tname]['Active'] = 0
                                    data['Trains'][tname]['Train Position'] = pos
                                    with open(self.ctc_comm_file, 'w', encoding='utf-8') as f:
                                        json.dump(data, f, indent=2)
                                break
                            except (json.JSONDecodeError, IOError) as e:
                                if retry < max_retries - 1:
                                    time.sleep(0.01)
                                else:
                                    print(f"Warning: Failed to deactivate {tname} after {max_retries} attempts: {e}")
                        to_remove.append(tname)
                        continue
                    else:
                        # Move into next block: clear old occupancy, update pos and index, add cumulative distance
                        # Clear occupancy from old block
                        self._occupied.discard(str(pos))
                        
                        state['pos'] = new_pos
                        self.train_idx[tname] = self.train_idx.get(tname, 0) + 1
                        self.cumulative_distance[tname] = self.cumulative_distance.get(tname, 0.0) + self.block_lengths.get(pos, 100)
                        
                        # Mark new block as occupied
                        self._occupied.add(str(new_pos))

                        # Write new position immediately to CTC so other controllers see it
                        max_retries = 3
                        for retry in range(max_retries):
                            try:
                                with self.file_lock:
                                    if not os.path.exists(self.ctc_comm_file):
                                        break
                                    with open(self.ctc_comm_file, 'r', encoding='utf-8') as f:
                                        data = json.load(f)
                                    data.setdefault('Trains', {})
                                    data['Trains'].setdefault(tname, {})
                                    data['Trains'][tname]['Train Position'] = new_pos
                                    with open(self.ctc_comm_file, 'w', encoding='utf-8') as f:
                                        json.dump(data, f, indent=2)
                                break
                            except (json.JSONDecodeError, IOError) as e:
                                if retry < max_retries - 1:
                                    time.sleep(0.01)
                                else:
                                    print(f"Warning: Failed to write position for {tname} after {max_retries} attempts: {e}")

                        # If train moved outside visible range, write commanded values for handoff and schedule removal
                        if state['pos'] not in self.visible_blocks and state['pos'] != 0:
                            if tname not in self.trains_to_handoff:
                                # Write commanded values to shared file for next controller (SW-compatible handoff)
                                print(f"[HW Wayside {self.wayside_id}] Handing off train {tname} at block {state['pos']} (speed: {state['cmd speed']:.2f} m/s, auth: {state['cmd auth']:.0f} m)")
                                try:
                                    with self.file_lock:
                                        # Read existing train_comm_file
                                        try:
                                            with open(self.train_comm_file, 'r', encoding='utf-8') as f:
                                                train_data = json.load(f)
                                        except:
                                            train_data = {}

                                        # Update with current commanded values for this train (convert to mph/yards like SW controller)
                                        cmd_speed_mph = state['cmd speed'] * 2.23694  # m/s to mph
                                        cmd_auth_yds = state['cmd auth'] * 1.09361    # meters to yards

                                        print(f"[HW Wayside {self.wayside_id}] Writing handoff data for {tname}: speed={cmd_speed_mph:.1f} mph, auth={cmd_auth_yds:.0f} yards ({state['cmd auth']:.0f}m), cumulative={self.cumulative_distance.get(tname, 0):.0f}m")

                                        if tname not in train_data:
                                            train_data[tname] = {"Commanded Speed": 0, "Commanded Authority": 0, "Beacon": {"Current Station": "", "Next Station": ""}, "Train Speed": 0}

                                        train_data[tname]["Commanded Speed"] = cmd_speed_mph
                                        train_data[tname]["Commanded Authority"] = cmd_auth_yds
                                        # Also store cumulative distance for accurate handoff calculation
                                        train_data[tname]["Cumulative Distance"] = self.cumulative_distance.get(tname, 0)
                                        train_data[tname]["Train Auth Start"] = self.train_auth_start.get(tname, state['cmd auth'])

                                        # Write back to file
                                        with open(self.train_comm_file, 'w', encoding='utf-8') as f:
                                            json.dump(train_data, f, indent=2)

                                        print(f"[HW Wayside {self.wayside_id}] Wrote handoff data for {tname}: speed={cmd_speed_mph:.1f} mph, auth={cmd_auth_yds:.0f} yards")

                                except Exception as e:
                                    print(f"[HW Wayside {self.wayside_id}] Warning: Failed to write handoff data for {tname}: {e}")

                                self.trains_to_handoff.append(tname)

            # Write commanded outputs to train file (similar to SW behavior)
            try:
                self.load_train_outputs(list(to_remove))
            except Exception:
                try:
                    # fallback to simpler writer
                    self.write_wayside_to_train(self.train_comm_file)
                except Exception:
                    pass

            # Cleanup removed trains (authority exhausted or end-of-line)
            for tr in to_remove:
                if tr in self.cmd_trains:
                    self.cmd_trains.pop(tr, None)
                if tr in self.train_idx:
                    self.train_idx.pop(tr, None)
                if tr in self.train_pos_start:
                    self.train_pos_start.pop(tr, None)
                if tr in self.train_auth_start:
                    self.train_auth_start.pop(tr, None)
                # Don't remove train_direction - preserve it for reactivation (matching SW behavior)
                # if tr in self.train_direction:
                #     self.train_direction.pop(tr, None)

            # Handle handoff removals
            if self.trains_to_handoff:
                for train in list(self.trains_to_handoff):
                    if train in self.cmd_trains:
                        pos = self.cmd_trains[train]['pos']
                        if pos not in self.visible_blocks and pos != 0:
                            # Remove tracking but leave any required CTC writes to whoever owns it
                            if train in self.cmd_trains:
                                self.cmd_trains.pop(train, None)
                    if train in self.trains_to_handoff:
                        try:
                            self.trains_to_handoff.remove(train)
                        except Exception:
                            pass

        finally:
            if self._trains_running:
                self._schedule_trains_tick()

    def load_train_speeds(self) -> Dict[str, float]:
        """Load actual train speeds (via API or from Train_Model/train_data.json); returns mapping Train N -> m/s"""
        train_speeds: Dict[str, float] = {}
        
        # Use API client if available, otherwise file I/O
        if self.wayside_api:
            try:
                api_speeds = self.wayside_api.get_train_speeds()
                if api_speeds:
                    # API returns speeds in mph with train names as keys
                    # Convert to m/s (multiply by 0.44704)
                    for train_name, velocity_mph in api_speeds.items():
                        velocity_ms = velocity_mph * 0.44704
                        train_speeds[train_name] = velocity_ms
                    return train_speeds
                # else fall through to file I/O
            except Exception as e:
                print(f"[HW Wayside {self.wayside_id}] API load_train_speeds failed: {e}, falling back to file I/O")
        
        # Legacy file I/O (fallback or when API not available)
        try:
            base = os.path.dirname(__file__)
            # Train_Model dir is sibling of track_controller
            tm_path = os.path.join(base, '..', '..', 'Train_Model', 'train_data.json')
            tm_path = os.path.normpath(tm_path)
            if os.path.exists(tm_path):
                with open(tm_path, 'r', encoding='utf-8') as f:
                    tdata = json.load(f)
                for i in range(1, 6):
                    key = f'train_{i}'
                    tname = f'Train {i}'
                    if key in tdata:
                        outputs = tdata[key].get('outputs', {})
                        velocity_mph = float(outputs.get('velocity_mph', 0.0) or 0.0)
                        # convert mph to m/s
                        velocity_ms = velocity_mph * 0.44704
                        train_speeds[tname] = velocity_ms
        except Exception:
            pass
        return train_speeds

    def load_train_outputs(self, trains_to_remove: List[str] = []):
        """Write commanded speed/authority to trains (via API or wayside_to_train.json).

        This mirrors SW behavior: update only trains in our managed_blocks (or yard handled by controller 1).
        """
        # Get actual train speeds first
        actual_train_speeds = self.load_train_speeds()
        
        # Use API client if available
        if self.wayside_api:
            try:
                for tkey in [f'Train {i}' for i in range(1, 6)]:
                    if tkey in trains_to_remove:
                        # Send zero commands for removed trains
                        self.wayside_api.send_train_commands(
                            train_name=tkey,
                            commanded_speed=0.0,
                            commanded_authority=0.0,
                            current_station="",
                            next_station=""
                        )
                    elif tkey in self.cmd_trains:
                        train_pos = int(self.cmd_trains[tkey]["pos"])
                        # Controller 2 should not write outputs for yard (block 0)
                        if train_pos == 0 and 0 not in self.managed_blocks:
                            continue
                        if train_pos in self.managed_blocks or (train_pos == 0 and 0 in self.managed_blocks):
                            # Convert m/s to mph for commanded speed
                            cmd_speed_m_s = float(self.cmd_trains[tkey].get('cmd speed', 0.0) or 0.0)
                            cmd_auth_m = float(self.cmd_trains[tkey].get('cmd auth', 0.0) or 0.0)
                            cmd_speed_mph = cmd_speed_m_s * 2.23694
                            cmd_auth_yds = cmd_auth_m * 1.09361
                            
                            # Get beacon data
                            current_station = ""
                            next_station = ""
                            if train_pos in self.block_graph:
                                train_direction = self.train_direction.get(tkey, 'forward')
                                block_data = self.block_graph[train_pos]
                                
                                if train_direction == 'forward' and block_data.get('forward_beacon', {}).get('has_beacon'):
                                    current_station = block_data['forward_beacon']['current_station']
                                    next_station = block_data['forward_beacon']['next_station']
                                elif train_direction == 'reverse' and block_data.get('reverse_beacon', {}).get('has_beacon'):
                                    current_station = block_data['reverse_beacon']['current_station']
                                    next_station = block_data['reverse_beacon']['next_station']
                            
                            # Send via API
                            self.wayside_api.send_train_commands(
                                train_name=tkey,
                                commanded_speed=cmd_speed_mph,
                                commanded_authority=cmd_auth_yds,
                                current_station=current_station,
                                next_station=next_station
                            )
                return  # Successfully sent via API
            except Exception as e:
                print(f"[HW Wayside {self.wayside_id}] API load_train_outputs failed: {e}, falling back to file I/O")
        
        # Legacy file I/O (fallback or when API not available)
        try:
            # Read existing file or create fresh structure
            try:
                with open(self.train_comm_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = {}
            # Ensure trains keys
            for i in range(1, 6):
                tkey = f'Train {i}'
                if tkey not in data:
                    data[tkey] = {"Commanded Speed": 0, "Commanded Authority": 0, "Beacon": {"Current Station": "", "Next Station": ""}, "Train Speed": 0}

            actual_train_speeds = self.load_train_speeds()

            for tkey in [f'Train {i}' for i in range(1, 6)]:
                if tkey in trains_to_remove:
                    data[tkey]["Commanded Speed"] = 0
                    data[tkey]["Commanded Authority"] = 0
                    data[tkey]["Train Speed"] = 0
                elif tkey in self.cmd_trains:
                    train_pos = int(self.cmd_trains[tkey]["pos"])
                    # Controller 2 should not write outputs for yard (block 0)
                    # We don't know controller id here; mimic SW: skip if pos==0 and not manager of yard
                    if train_pos == 0 and 0 not in self.managed_blocks:
                        continue
                    if train_pos in self.managed_blocks or (train_pos == 0 and 0 in self.managed_blocks):
                        # Our internal cmd speed may be in m/s or mph depending on upstream; assume m/s and convert to mph
                        cmd_speed_m_s = float(self.cmd_trains[tkey].get('cmd speed', 0.0) or 0.0)
                        cmd_auth_m = float(self.cmd_trains[tkey].get('cmd auth', 0.0) or 0.0)
                        # convert m/s to mph and meters to yards to match SW expectations
                        data[tkey]["Commanded Speed"] = cmd_speed_m_s * 2.23694
                        data[tkey]["Commanded Authority"] = cmd_auth_m * 1.09361
                        data[tkey]["Train Speed"] = actual_train_speeds.get(tkey, 0.0) * 2.23694
                        
                        # CRITICAL: Write handoff metadata (matching SW behavior)
                        # This allows SW to properly calculate traveled distance after handoff FROM HW
                        data[tkey]["Cumulative Distance"] = self.cumulative_distance.get(tkey, 0)
                        data[tkey]["Train Auth Start"] = self.train_auth_start.get(tkey, cmd_auth_m)

                        # Populate beacon data based on train position and direction (matching SW behavior)
                        if train_pos in self.block_graph:
                            train_direction = self.train_direction.get(tkey, 'forward')
                            block_data = self.block_graph[train_pos]
                            
                            # Always update beacon when train moves to new block with beacon data
                            if train_direction == 'forward' and block_data.get('forward_beacon', {}).get('has_beacon'):
                                data[tkey]["Beacon"]["Current Station"] = block_data['forward_beacon']['current_station']
                                data[tkey]["Beacon"]["Next Station"] = block_data['forward_beacon']['next_station']
                            elif train_direction == 'reverse' and block_data.get('reverse_beacon', {}).get('has_beacon'):
                                data[tkey]["Beacon"]["Current Station"] = block_data['reverse_beacon']['current_station']
                                data[tkey]["Beacon"]["Next Station"] = block_data['reverse_beacon']['next_station']
                            # If no beacon at current block, keep existing beacon data (don't clear it)

                        # CRITICAL: Update train status back to CTC for real-time position tracking
                        # This allows CTC to display train positions to the dispatcher
                        if self.wayside_api:
                            try:
                                self.wayside_api.update_train_status(
                                    train_name=tkey,
                                    position=int(train_pos),
                                    state="moving" if actual_train_speeds.get(tkey, 0) > 0 else "stopped",
                                    active=1 if tkey in self.cmd_trains else 0
                                )
                                print(f"[HW Wayside {self.wayside_id}] Updated CTC: {tkey} at block {train_pos}")
                            except Exception as e:
                                print(f"[HW Wayside {self.wayside_id}] Failed to update train status to CTC: {e}")

            # Atomic write
            d = os.path.dirname(self.train_comm_file) or '.'
            import tempfile
            with tempfile.NamedTemporaryFile('w', delete=False, dir=d, encoding='utf-8') as tmp:
                json.dump(data, tmp, indent=2)
                tmp.flush()
                os.fsync(tmp.fileno())
                tmp_path = tmp.name
            os.replace(tmp_path, self.train_comm_file)
        except Exception as e:
            print(f"[WARN] load_train_outputs failed: {e}")

    # ---------------------- PLC operations ----------------------

    def load_plc(self, path: str) -> bool:
        """Dynamically load a PLC python file by path (relative or absolute).

        We set `_plc_module` so `run_plc` can call its `process_states_*` function.
        """
        try:
            if not path:
                self._plc_loaded = False
                self._plc_name = None
                self._plc_module = None
                return False

            # Resolve path relative to this file if necessary
            if not os.path.isabs(path):
                base = os.path.dirname(__file__)
                candidate = os.path.join(base, path)
            else:
                candidate = path

            if not os.path.exists(candidate):
                # try without directory (module import by name)
                module_name = os.path.splitext(os.path.basename(path))[0]
                try:
                    mod = importlib.import_module(module_name)
                    self._plc_module = mod
                    self._plc_loaded = True
                    self._plc_name = path
                    return True
                except Exception:
                    self._plc_loaded = False
                    return False

            spec = importlib.util.spec_from_file_location("wayside_plc", candidate)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[attr-defined]
                self._plc_module = mod
                self._plc_loaded = True
                self._plc_name = path
                return True
        except Exception:
            pass
        self._plc_loaded = False
        self._plc_module = None
        return False

    def start_plc(self, period_s: float = 0.2):
        """Start periodic PLC execution (non-blocking)."""
        self._plc_period_s = float(period_s)
        if self._plc_running:
            return
        self._plc_running = True
        self._schedule_plc_tick()

    def stop_plc(self):
        self._plc_running = False
        if self._plc_timer:
            try:
                self._plc_timer.cancel()
            except Exception:
                pass
            self._plc_timer = None

    def _schedule_plc_tick(self):
        if not self._plc_running:
            return
        self._plc_timer = threading.Timer(self._plc_period_s, self._run_plc_tick)
        self._plc_timer.daemon = True
        self._plc_timer.start()

    def _run_plc_tick(self):
        try:
            # Safe guard
            if not self._plc_loaded or not self._plc_module:
                return
            
            # Don't run PLC in maintenance mode - manual control takes precedence
            if getattr(self, 'maintenance_active', False):
                return

            # Build an occupancy slice intended for PLC functions.
            # Many PLCs expect a contiguous slice covering their region; we provide the
            # full occupancy list so PLC implementations can index as they expect.
            with self._lock:
                # create occupancy array length max block id + 1
                occ_ints = []
                # merge occupancy sources
                merged = set(self._occ_ctc) | set(self._occ_track)
                max_idx = 0
                for b in merged:
                    try:
                        max_idx = max(max_idx, int(b))
                    except Exception:
                        pass
                n = max(152, max_idx + 1)
                occ_ints = [0] * n
                for b in merged:
                    try:
                        i = int(b)
                        if 0 <= i < n:
                            occ_ints[i] = 1
                    except Exception:
                        continue

            # Select and call PLC function based on PLC module contents
            switches = []
            signals = []
            crossing = []

            # Common function names we support
            if hasattr(self._plc_module, 'process_states_green_xlup'):
                switches, signals, crossing = self._plc_module.process_states_green_xlup(occ_ints)
            elif hasattr(self._plc_module, 'process_states_green_xldown'):
                switches, signals, crossing = self._plc_module.process_states_green_xldown(occ_ints)
            else:
                # Unsupported PLC signature
                return

            # Map PLC outputs into our commanded dicts (choose mapping heuristics)
            with self._lock:
                # Use HW_Vital_Check to validate PLC proposals before staging
                try:
                    bv = HW_Vital_Check()
                except Exception:
                    bv = None

                # Map switches: prefer index-to-block mapping based on _BLOCKS_WITH_SWITCHES order
                for idx, blk in enumerate(_BLOCKS_WITH_SWITCHES):
                    try:
                        val = switches[idx]
                        # Proposed state mapping (string) kept for UI; pass numeric to verifier when possible
                        proposed_str = _SWITCH_NAMES.get(int(val), str(val))
                        allowed = True
                        reason = ""
                        if bv:
                            allowed, reason = bv.verify_switch_change(
                                dict(self._switch_state), str(blk), val,
                                block_graph=self.block_graph,
                                occupied_blocks=list(self._occupied),
                                closed_blocks=list(self._closed),
                                switch_map=getattr(self, 'switch_map', None),
                            )
                        if allowed:
                            self._cmd_switch_state[str(blk)] = proposed_str
                        else:
                            # Reject: leave previous commanded state if present, else do nothing
                            print(f"[PLCSAFE] Switch {blk} change rejected by safety: {reason}")
                    except Exception:
                        continue

                # Map gates
                for idx, blk in enumerate(_BLOCKS_WITH_GATES):
                    try:
                        val = crossing[idx] if idx < len(crossing) else (signals[idx * 2] if idx * 2 < len(signals) else 0)
                        proposed = _GATE_NAMES.get(int(val), str(val))
                        allowed = True
                        reason = ""
                        if bv:
                            approach = None
                            try:
                                approach = getattr(self, 'gate_approach_map', {}).get(str(blk), None)
                            except Exception:
                                approach = None
                            allowed, reason = bv.verify_gate_change(
                                dict(self._gate_state), str(blk), proposed,
                                occupied_blocks=list(self._occupied),
                                closed_blocks=list(self._closed),
                                approach_blocks=approach,
                            )
                        if allowed:
                            self._cmd_gate_state[str(blk)] = proposed
                        else:
                            # Safe fallback: ensure gates stay DOWN
                            self._cmd_gate_state[str(blk)] = 'DOWN'
                            print(f"[PLCSAFE] Gate {blk} change rejected by safety: {reason}")
                    except Exception:
                        continue

                # Map lights: PLC returns pairs; try to map sequentially into _BLOCKS_WITH_LIGHTS
                try:
                    for i, blk in enumerate(_BLOCKS_WITH_LIGHTS):
                        b0 = int(signals[2 * i]) if 2 * i < len(signals) else 0
                        b1 = int(signals[2 * i + 1]) if 2 * i + 1 < len(signals) else 1
                        if b0 == 0 and b1 == 0:
                            name = 'SUPERGREEN'
                        elif b0 == 0 and b1 == 1:
                            name = 'GREEN'
                        elif b0 == 1 and b1 == 0:
                            name = 'YELLOW'
                        else:
                            name = 'RED'
                        allowed = True
                        reason = ""
                        if bv:
                            allowed, reason = bv.verify_light_change(
                                dict(self._light_state), str(blk), name,
                                occupied_blocks=list(self._occupied),
                                closed_blocks=list(self._closed),
                            )
                        if allowed:
                            self._cmd_light_state[str(blk)] = name
                        else:
                            # Safe fallback: force RED
                            self._cmd_light_state[str(blk)] = 'RED'
                            print(f"[PLCSAFE] Light {blk} change rejected by safety: {reason}")
                except Exception:
                    pass

        finally:
            # Schedule next tick regardless of exceptions
            if self._plc_running:
                self._schedule_plc_tick()

    def change_plc(self, enable: bool, *_args, **_kwargs):
        # Toggle PLC active state; when enabling we also start the PLC periodic
        # execution so uploaded PLC code actually runs. When disabling we stop
        # the PLC timer to avoid stray background ticks.
        self._plc_loaded = bool(enable)
        if enable:
            try:
                self.start_plc(self._plc_period_s)
            except Exception:
                pass
        else:
            try:
                self.stop_plc()
            except Exception:
                pass

    def write_wayside_to_train(self, filepath: str = 'wayside_to_train.json') -> None:
        """Write minimal wayside->train outputs in the SW-compatible shape.

        This is intentionally small: if this controller has a simulated train block
        we populate Train 1 fields; otherwise leave zeros. Uses atomic tempfile write.
        """
        try:
            base = {}
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    base = json.load(f) or {}
        except Exception:
            base = {}

        # Ensure train keys exist
        for i in range(1, 6):
            tkey = f"Train {i}"
            if tkey not in base:
                base[tkey] = {"Commanded Speed": 0, "Commanded Authority": 0, "Beacon": {"Current Station": "", "Next Station": ""}, "Train Speed": 0}

        # Populate Train 1 from our simulated state if present
        try:
            if self._train_block is not None:
                base["Train 1"]["Commanded Speed"] = float(self._speed_mph)
                base["Train 1"]["Commanded Authority"] = int(self._authority_yds)
                base["Train 1"]["Train Speed"] = float(self._speed_mph)
            else:
                base["Train 1"]["Commanded Speed"] = 0
                base["Train 1"]["Commanded Authority"] = 0
                base["Train 1"]["Train Speed"] = 0
        except Exception:
            pass

        # Atomic write
        try:
            d = os.path.dirname(filepath) or '.'
            import tempfile
            with tempfile.NamedTemporaryFile('w', delete=False, dir=d, encoding='utf-8') as tmp:
                json.dump(base, tmp, indent=2)
                tmp.flush()
                os.fsync(tmp.fileno())
                tmp_path = tmp.name
            os.replace(tmp_path, filepath)
        except Exception as e:
            print(f"[WARN] wayside->train write failed: {e}")

    # ------------------------- UI hooks -------------------------

    def on_selected_block(self, block_id: str):
        with self._lock:
            self._selected_block = str(block_id)
    
    def get_selected_block(self) -> Optional[str]:
        """Return the currently selected block ID."""
        with self._lock:
            return self._selected_block

    # ------------------ manual switch control (UI) ------------------

    def request_switch_change(self, block_id: str, new_state: str) -> Tuple[bool, str]:
        """Request a manual switch change from the UI.

        Returns (allowed: bool, reason: str). If allowed, the requested state is
        staged into `_cmd_switch_state` so it will be written out like a PLC
        command. The change is rejected if safety checks fail.
        """
        try:
            with self._lock:
                # Maintenance gate: only allow manual switch changes while in maintenance
                if not getattr(self, 'maintenance_active', False):
                    return False, "Manual switch changes require Maintenance mode"

                # Prepare inputs for the safety check
                switch_states = dict(self._switch_state)
                occupied = list(self._occupied)
                closed = list(self._closed)
                bv = HW_Vital_Check()
                allowed, reason = bv.verify_switch_change(
                    switch_states, block_id, new_state,
                    block_graph=self.block_graph,
                    occupied_blocks=occupied,
                    closed_blocks=closed,
                    switch_map=getattr(self, 'switch_map', None),
                )
                if not allowed:
                    return False, reason

                # If allowed, stage as a commanded switch so build_commanded_arrays will prefer it
                self._cmd_switch_state[str(block_id)] = str(new_state)
                return True, "Staged"
        except Exception as e:
            return False, f"Exception: {e}"

    # ----------------------- UI getters -------------------------

    def get_current_train_block(self) -> Optional[str]:
        with self._lock:
            return self._train_block

    def get_next_station_for_block(self, block: int) -> str:
        """Find the next station block ahead of the given block position."""
        try:
            # Find position in green_order
            if block not in self.green_order:
                return "-"
            idx = self.green_order.index(block)
            
            # Search forward through the route for next station
            for i in range(idx + 1, min(idx + 50, len(self.green_order))):  # Look up to 50 blocks ahead
                check_block = self.green_order[i]
                if check_block in self.station_blocks:
                    # Return station name if we have one
                    if check_block in self.station_names:
                        return self.station_names[check_block]
                    return f"Block {check_block}"
            return "-"
        except Exception:
            return "-"

    def get_block_ids(self) -> List[str]:
        return list(self.block_ids)

    def get_ui_block_list(self) -> List[str]:
        """Return a block list intended for the UI: union of managed blocks and any
        blocks that have switches (from switch_map) so switch blocks like 63 appear.
        """
        s = set(str(b) for b in self.block_ids)
        try:
            sm = getattr(self, 'switch_map', {}) or {}
            for k in sm.keys():
                s.add(str(k))
        except Exception:
            pass
        # Also include station blocks / any interesting graph nodes
        try:
            for b in getattr(self, 'station_blocks', set()):
                s.add(str(b))
        except Exception:
            pass
        # return sorted numeric ordering when possible
        try:
            return sorted(list(s), key=lambda x: int(x))
        except Exception:
            return sorted(list(s))

    def get_occupancy_sources(self) -> Dict[str, List[str]]:
        """Return a dict showing occupancy sources: CTC, Track, Simulated train."""
        try:
            src = {
                'ctc': sorted([str(x) for x in (self._occ_ctc or [])]),
                'track': sorted([str(x) for x in (self._occ_track or [])]),
                'sim': [str(self._train_block)] if self._train_block else [],
                'merged': sorted([str(x) for x in (self._occupied or [])]),
            }
            return src
        except Exception:
            return {'ctc': [], 'track': [], 'sim': [], 'merged': []}

    def get_block_state(self, block_id: str) -> Dict[str, Any]:
        b = str(block_id)
        with self._lock:
            occupied_here = (b in self._occupied)

            # For blocks we manage, show commanded values from active trains instead of simulated values
            speed_mph = 0.0
            authority_yards = 0

            if b in self.block_ids:
                # Check if any train is currently commanded to occupy this block
                for train_id, train_data in self.cmd_trains.items():
                    if str(train_data.get('pos', '')) == b:
                        # This train is commanded to be at this block - show its commanded values
                        # Convert internal units: m/s -> mph, meters -> yards
                        speed_ms = train_data.get('cmd speed', 0.0)
                        auth_m = train_data.get('cmd auth', 0)
                        speed_mph = float(speed_ms) * 2.23694  # m/s to mph
                        authority_yards = int(float(auth_m) * 1.09361)  # meters to yards
                        break
                else:
                    # No train commanded to this block, show simulated values for maintenance mode
                    speed_mph = self._speed_mph
                    authority_yards = self._authority_yds

            state = {
                "block_id": b,
                "speed_mph": speed_mph,
                "authority_yards": authority_yards,
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
        # include explicit switch_map entry if present
        sw_map = None
        try:
            sm = getattr(self, 'switch_map', None) or {}
            entry = sm.get(str(block_id)) or sm.get(int(block_id) if str(block_id).isdigit() else None)
            if entry is not None:
                # normalize keys to '0'/'1' for display
                sw_map = {str(k): v for k, v in entry.items()}
        except Exception:
            sw_map = None

        # Resolve the current effective switch display value. We present a
        # single `switch` field to the UI. Prefer the staged/commanded
        # state when present, otherwise fall back to the track state. If a
        # `switch_map` exists and we can determine numeric position (0/1),
        # map that to the concrete target block (e.g. 77 or 100) and show
        # that target as the displayed value.
        display_switch = None
        try:
            bid = str(block_id)
            # Effective state prefers staged/commanded state
            eff = None
            if bid in self._cmd_switch_state:
                eff = self._cmd_switch_state.get(bid)
            elif bid in self._switch_state:
                eff = self._switch_state.get(bid)

            # Convert eff to numeric position if possible
            eff_pos = None
            if eff is not None:
                try:
                    if isinstance(eff, str) and eff.upper().startswith('L'):
                        eff_pos = 0
                    elif isinstance(eff, str) and eff.upper().startswith('R'):
                        eff_pos = 1
                    elif str(eff).isdigit():
                        eff_pos = int(str(eff))
                except Exception:
                    eff_pos = None

            if sw_map and eff_pos is not None:
                try:
                    tgt = sw_map.get(str(eff_pos)) or sw_map.get(eff_pos)
                    if tgt is not None:
                        display_switch = str(int(tgt))
                except Exception:
                    display_switch = None

            # If we couldn't resolve to a numeric target, show the textual state
            if display_switch is None:
                display_switch = str(eff) if eff is not None else str(st.get("switch", "-"))
        except Exception:
            display_switch = str(st.get("switch", "-"))

        return {
            "block_id": st.get("block_id"),
            "light": st.get("light"),
            "switch": display_switch,
            "switch_map": sw_map,
            "gate": st.get("gate"),
            "occupied": st.get("occupied"),
            "closed": (block_id in self._closed),
        }

    def get_active_trains(self) -> List[Dict[str, Any]]:
        """Return a list of active train summaries for the UI.

        Each entry contains: name, active (bool), position (int or None),
        cmd_speed, cmd_auth.
        """
        out: List[Dict[str, Any]] = []
        with self._lock:
            # Prefer visible trains from CTC active_trains dict; include up to 5 logical trains
            seen = set()
            # First, include any trains from active_trains (CTC view)
            for tname, info in (self.active_trains or {}).items():
                try:
                    active = int(info.get('Active', 0)) == 1
                except Exception:
                    active = False
                try:
                    pos = int(info.get('Train Position'))
                except Exception:
                    pos = None
                
                # ONLY show trains within our managed blocks (simulate limited visibility)
                if pos is not None and str(pos) not in self.block_ids:
                    continue
                
                cmd = self.cmd_trains.get(tname, {})
                # Calculate next station based on train position
                next_station = '-'
                try:
                    if pos is not None:
                        next_station = self.get_next_station_for_block(pos)
                except Exception:
                    next_station = '-'
                # Prefer controller's per-train commanded values if available,
                # otherwise fall back to wayside-wide values.
                if cmd and (cmd.get('cmd speed', None) is not None):
                    try:
                        cmd_speed_mph = float(cmd.get('cmd speed', 0.0)) * 2.23694
                    except Exception:
                        cmd_speed_mph = float(self._speed_mph)
                else:
                    cmd_speed_mph = float(self._speed_mph)

                if cmd and (cmd.get('cmd auth', None) is not None):
                    try:
                        # cmd auth is stored internally in meters; convert to yards
                        cmd_auth_yds = int(float(cmd.get('cmd auth', 0.0)) * 1.09361)
                    except Exception:
                        cmd_auth_yds = int(self._authority_yds)
                else:
                    cmd_auth_yds = int(self._authority_yds)

                out.append({
                    'name': tname,
                    'active': active,
                    'position': pos,
                    'cmd_speed': cmd_speed_mph,
                    'cmd_auth': cmd_auth_yds,
                    'next_station': next_station,
                })
                seen.add(tname)

            # Fill in any remaining known commanded trains that CTC didn't list
            for tname, cmd in (self.cmd_trains or {}).items():
                if tname in seen:
                    continue
                out.append({
                    'name': tname,
                    'active': False,
                    'position': cmd.get('pos'),
                    'cmd_speed': cmd.get('cmd speed', 0),
                    'cmd_auth': cmd.get('cmd auth', 0),
                    'next_station': cmd.get('next_station') or cmd.get('beacon') or '-',
                })

        return out

    def has_switch(self, block_id: str) -> bool:
        """Return True if this block is a hardware switch managed by this wayside.

        We consider blocks explicitly listed in `_BLOCKS_WITH_SWITCHES` or present
        in `self.switch_map` as having a switch.
        """
        try:
            bid = str(block_id)
            if bid in (str(x) for x in _BLOCKS_WITH_SWITCHES):
                return True
            if getattr(self, 'switch_map', None) and bid in self.switch_map:
                return True
        except Exception:
            pass
        return False

    # ---------------- build commanded arrays to write back ---------------

    def build_commanded_arrays(self, n_total_blocks: int) -> Dict[str, List[int]]:
        """
        Produce arrays
          - G-switches: 6 entries, 0/1
          - G-gates:    2 entries, 0/1
          - G-lights:   24 entries (12 lights × 2 bits), each entry 0/1
        Plus:
          - G-Commanded Speed: length n_total_blocks, mph per block
          - G-Commanded Authority: length n_total_blocks, yards per block
        """
        inv_switch = {"Left": 0, "Right": 1}
        inv_gate = {"DOWN": 0, "UP": 1}

        # hardware arrays
        switches = [0] * len(_BLOCKS_WITH_SWITCHES)      # 6 entries
        gates    = [0] * len(_BLOCKS_WITH_GATES)         # 2 entries
        lights   = [0] * (2 * len(_BLOCKS_WITH_LIGHTS))  # 12 lights × 2 bits = 24

        # per-block speed/authority arrays
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

            # -------- Per-block speed/authority --------
            if self._train_block is not None:
                try:
                    i = int(self._train_block)
                except ValueError:
                    i = -1
                if 0 <= i < int(n_total_blocks):
                    cmd_speed[i] = int(self._speed_mph)
                    cmd_auth[i]  = int(self._authority_yds)

        return {
            "G-switches": switches,
            "G-lights": lights,
            "G-gates": gates,
            "G-Commanded Speed": cmd_speed,
            "G-Commanded Authority": cmd_auth,
        }

    # ---------------- build occupancy array for CTC ----------------------

    def build_occupancy_array(self, n_total_blocks: int) -> List[int]:
        """
        Return a 0/1 occupancy array of length n_total_blocks, where 1 means
        this block is occupied according to this controller's merged view.
        Used by hw_main.py to combine occupancy from all waysides and
        write a single array back to CTC, just like the SW module.
        """
        arr = [0] * int(n_total_blocks)

        with self._lock:
            for b in self._occupied:
                try:
                    i = int(b)
                except (TypeError, ValueError):
                    continue
                if 0 <= i < int(n_total_blocks):
                    arr[i] = 1

        return arr