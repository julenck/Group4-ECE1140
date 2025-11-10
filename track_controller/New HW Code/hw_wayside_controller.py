# hw_wayside_controller.py
# Wayside Controller HW module core logic.
# Oliver Kettelson-Belinkie, 2025

from __future__ import annotations
from typing import Dict, List, Any, Optional
from hw_vital_check import HW_Vital_Check
import importlib.util
import json
import threading
import os

class HW_Wayside_Controller:

    light_result: bool = False          # State change result placeholders
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
        self.light_states = getattr(self, "light_states", {b: 0 for b in self.block_ids})
        self.switch_states = getattr(self, "switch_states", {b: 0 for b in self.block_ids})
        self.gate_states = getattr(self, "gate_states", {b: 0 for b in self.block_ids})
        self.active_plc = None
        self.maintenance_active = False
        self.safety_result = True
        self.safety_report = {}
        self.auto_safety_enabled = True
        self.occupied_blocks = getattr(self, "occupied_blocks", [])     # Rely on external modules to set these
        self.closed_blocks   = getattr(self, "closed_blocks", [])
        self.emergency       = getattr(self, "emergency", False)
        self.speed_mph       = getattr(self, "speed_mph", 0.0)
        self.authority_yards = getattr(self, "authority_yards", 0)

        self.vital = HW_Vital_Check()

        self._plc_module = None
        self.active_plc = ""
        # JSON comm filenames (compatible with SW naming)
        self.ctc_comm_file = "ctc_to_wayside.json"
        self.track_comm_file = "track_to_wayside.json"
        # threading/file protection for background PLC loop
        self.file_lock = threading.Lock()
        self.running = True

        # Start background PLC loop (non-blocking)
        try:
            # schedule first run shortly after init
            threading.Timer(0.1, self.run_plc).start()
        except Exception:
            pass

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

        try:
            spec = importlib.util.spec_from_file_location("user_plc", path)

            if spec is None or spec.loader is None:

                return False
            
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            if not hasattr(mod, "tick"):

                return False
            
            # optional init
            if hasattr(mod, "init"):
                try:
                    mod.init(self.block_ids)
                except Exception:
                    pass

            self._plc_module = mod
            self.active_plc = path
            return True
        
        except Exception:

            return False

    def change_plc(self, active: bool, plc_path: str) -> bool:

        if active and plc_path:

            self.active_plc = plc_path
            return True
        
        return False

    # ---------------- logic / outputs ----------------

    def assess_safety(self, block_ids: List, vital_in: Dict) -> Dict:

        # --- Step 1: Run PLC cycle ---

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

    # background PLC loop + file IO
    def run_plc(self) -> None:
       
        if not self.running:
            self.active_plc = ""
            return

        if self.active_plc:
            
            try:
                self.load_inputs_track()
            except Exception:
                pass

            try:
                self.run_plc_cycle()
            except Exception:
                pass

            # write outputs back
            try:
                self.load_track_outputs()
            except Exception:
                pass

        # schedule next run
        if self.running:
            try:
                threading.Timer(0.2, self.run_plc).start()
            except Exception:
                pass

    def stop(self) -> None:
        
        self.running = False

    def load_inputs_track(self) -> None:
        
        data = {}
        try:
            with self.file_lock:

                if not os.path.exists(self.track_comm_file):
                    return
                with open(self.track_comm_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

            occ = data.get("occupied_blocks") or data.get("G-Occupancy")
            if occ is not None:
                
                self.occupied_blocks = list(occ)

            closed = data.get("closed_blocks") or data.get("G-Closed")
            if closed is not None:
                self.closed_blocks = list(closed)

        except Exception:
            # ignore IO errors in background loop
            return

    def load_track_outputs(self) -> None:
        
        try:
            with self.file_lock:
                data = {}
                if os.path.exists(self.track_comm_file):
                    try:
                        with open(self.track_comm_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    except Exception:
                        data = {}

                data["occupied_blocks"] = list(self.occupied_blocks)
                data["light_states"] = dict(self.light_states)
                data["gate_states"] = dict(self.gate_states)
                data["switch_states"] = dict(self.switch_states)

                with open(self.track_comm_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
        except Exception:
            return

    # ---------------- internal plc/runtime helpers ----------------
    def run_plc_cycle(self) -> None:
        if not self._plc_module:
            return

        ctx = {
            "occupied": set(self.occupied_blocks),
            "closed": set(self.closed_blocks),
            "emergency": bool(self.emergency),
            "speed_mph": float(self.speed_mph),
            "authority_yards": int(self.authority_yards),
            "blocks": list(self.block_ids),
        }

        try:
            proposals = (self._plc_module.tick(ctx) or [])
        except Exception:
            return  # never let PLC crash the vital loop

        for item in proposals:
            # Expect tuples like (kind, block_id, value)
            if not isinstance(item, (list, tuple)) or len(item) < 3:
                continue
            kind, bid, val = item[0], item[1], item[2]
            try:
                val = int(val)
            except Exception:
                # skip invalid values
                continue

            if kind == "light":
                ok = True
                if hasattr(self.vital, "verify_light_change"):
                    ok = self.vital.verify_light_change(list(self.light_states.items()), bid, val)
                if ok:
                    # set only if block known
                    if bid in self.light_states:
                        self.light_states[bid] = val

            elif kind == "switch":
                ok = True
                if hasattr(self.vital, "verify_switch_change"):
                    ok = self.vital.verify_switch_change(list(self.switch_states.items()), bid, val)
                if ok:
                    if bid in self.switch_states:
                        self.switch_states[bid] = val

            elif kind == "gate":
                ok = True
                if hasattr(self.vital, "verify_gate_change"):
                    ok = self.vital.verify_gate_change(list(self.gate_states.items()), bid, val)
                if ok:
                    if bid in self.gate_states:
                        self.gate_states[bid] = val