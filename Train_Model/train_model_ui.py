import os, json, time, tkinter as tk
from tkinter import ttk
import threading
import sys
import importlib, importlib.util

import os

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)  # Track_and_Train
TRACK_MODEL_DIR = os.path.join(BASE_DIR, "Track_Model")
TRAIN_MODEL_DIR = os.path.join(BASE_DIR, "Train_Model")

# Track JSONs
STATIC_JSON_PATH = os.path.join(TRACK_MODEL_DIR, "track_model_static.json")
CONTROLLER_JSON_PATH = os.path.join(
    TRACK_MODEL_DIR, "track_model_Track_controller.json"
)

# Train JSONs
TRAIN_DATA_PATH = os.path.join(TRAIN_MODEL_DIR, "train_data.json")

# Import core logic
from train_model_core import (
    TRAIN_STATES_FILE,
    TRAIN_DATA_FILE,
    TRACK_INPUT_FILE,
    TrainModel,
    safe_read_json,
    safe_write_json,
    ensure_train_data,
    read_track_input,
    merge_inputs,
    update_track_motion,  # renamed: motion only
    DEFAULT_SPECS,
    compute_passengers_disembarking,
    sync_wayside_to_train_data,
)

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Remove the direct "import requests" and use dynamic import instead
try:
    requests = (
        importlib.import_module("requests")
        if importlib.util.find_spec("requests")
        else None
    )
except Exception:
    requests = None


# NEW
class TrainModelUI(ttk.Frame):
    def __init__(self, parent, train_id=None, server_url=None):
        super().__init__(parent)
        self.grid(row=0, column=0, sticky="nsew")
        self.config(width=450)
        self.pack_propagate(False)

        self.train_id = train_id
        self.server_url = server_url
        self.train_data_path = TRAIN_DATA_FILE
        
        # Initialize API client if server_url provided (Phase 3 REST API integration)
        self.api_client = None
        if server_url and train_id:
            try:
                # Import the Train Model API client
                train_model_dir = os.path.dirname(os.path.abspath(__file__))
                sys.path.insert(0, train_model_dir)
                from train_model_api_client import TrainModelAPIClient
                self.api_client = TrainModelAPIClient(train_id=train_id, server_url=server_url)
                print(f"[Train Model {train_id}] Using REST API: {server_url}")
            except Exception as e:
                print(f"[Train Model {train_id}] Warning: Failed to initialize API client: {e}")
                print(f"[Train Model {train_id}] Falling back to file-based I/O")
                self.api_client = None
        elif server_url and not train_id:
            print(f"[Train Model] Warning: server_url provided but train_id is None - using file I/O")
        elif not server_url:
            print(f"[Train Model {train_id or 'root'}] Using file-based I/O (no server_url)")

        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except Exception:
            style.theme_use("clam")
        style.configure("Header.TLabelframe", font=("Segoe UI", 10, "bold"))
        style.configure("Data.TLabel", font=("Consolas", 9))
        style.configure("Status.On.TLabel", foreground="#0a7d12")
        style.configure("Status.Off.TLabel", foreground="#b00")

        td = ensure_train_data(self.train_data_path)
        if self.train_id is not None and f"train_{self.train_id}" in td:
            self.specs = td[f"train_{self.train_id}"].get(
                "specs", td.get("specs", DEFAULT_SPECS)
            )
        else:
            self.specs = td.get("specs", DEFAULT_SPECS)

        self.model = TrainModel(self.specs)
        self._last_disembark_state = {"station": None, "count": 0}
        self._last_beacon_inputs = {}
        self._stop_event = threading.Event()
        self._last_mtimes = {"track": 0.0, "ctrl": 0.0, "train_data": 0.0}
        threading.Thread(target=self._watch_files, daemon=True).start()

        # TrainModelUI layout: 2 rows
        # row 0 = left column (info/env/specs/failure/control)
        # row 1 = announcements panel (full-width)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        self.columnconfigure(0, weight=1)

        # LEFT COLUMN
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        left.columnconfigure(0, weight=0)
        left.columnconfigure(1, weight=0)
        left.rowconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        left.rowconfigure(2, weight=1)

        # Build left-side panels
        self.create_info_panel(left)
        self.create_env_panel(left)
        self.create_specs_panel(left)
        self.create_failure_panel(left)
        self.create_control_panel(left)

        # --- MOVE ANNOUNCEMENTS OUT OF LEFT ---
        bottom = ttk.Frame(self)
        bottom.grid(row=1, column=0, sticky="ew", padx=6, pady=6)
        bottom.columnconfigure(0, weight=1)
        bottom.config(height=120)
        bottom.grid_propagate(False)

        self.create_announcements_panel(bottom)

        self.update_loop()

    def create_info_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Dynamics", style="Header.TLabelframe")
        frame.grid(row=0, column=0, sticky="NSEW", padx=4, pady=4)
        self.info_labels = {}
        fields = [
            "Velocity (mph)",
            "Acceleration (ft/s²)",
            "Position (yds)",
            "Authority Remaining (yds)",
            "Train Temperature (°F)",
            "Set Temperature (°F)",
            "Current Station",
            "Next Station",
            "Speed Limit (mph)",
        ]
        for i, key in enumerate(fields):
            ttk.Label(frame, text=key + ":", style="Data.TLabel").grid(
                row=i, column=0, sticky="w", padx=8, pady=2
            )
            lbl = ttk.Label(frame, text="--", style="Data.TLabel")
            lbl.grid(row=i, column=1, sticky="w", padx=4, pady=2)
            self.info_labels[key] = lbl
        frame.columnconfigure(1, weight=1)

    def create_env_panel(self, parent):
        frame = ttk.LabelFrame(
            parent, text="Env / Doors / Lights", style="Header.TLabelframe"
        )
        frame.grid(row=0, column=1, sticky="NSEW", padx=4, pady=4)
        self.env_labels = {}
        # FIX: use enumerate instead of unpacking into (i, key) from a list of strings
        for i, key in enumerate(
            ["Left Door", "Right Door", "Interior Lights", "Exterior Lights"]
        ):
            ttk.Label(frame, text=key + ":", style="Data.TLabel").grid(
                row=i, column=0, sticky="w", padx=8, pady=2
            )
            lbl = ttk.Label(frame, text="--", style="Data.TLabel")
            lbl.grid(row=i, column=1, sticky="w", padx=4, pady=2)
            self.env_labels[key] = lbl
        frame.columnconfigure(1, weight=1)

    def create_specs_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Specs", style="Header.TLabelframe")
        frame.grid(row=1, column=0, sticky="NSEW", padx=4, pady=4)
        for k, v in self.specs.items():
            ttk.Label(frame, text=f"{k}: {v}", style="Data.TLabel").pack(
                anchor="w", padx=8, pady=0
            )

    def create_failure_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Failures", style="Header.TLabelframe")
        frame.grid(row=1, column=1, sticky="NSEW", padx=4, pady=4)
        self.fail_labels = {}
        for row, key in enumerate(
            ["Engine Failure", "Brake Failure", "Signal Failure", "Emergency Brake"]
        ):
            ttk.Label(frame, text=key + ":", style="Data.TLabel").grid(
                row=row, column=0, sticky="w", padx=6, pady=2
            )
            lbl = ttk.Label(frame, text="Off", style="Status.Off.TLabel")
            lbl.grid(row=row, column=1, sticky="w", padx=4, pady=2)
            self.fail_labels[key] = lbl
        ttk.Button(
            frame, text="Toggle Engine", command=self.toggle_engine_failure
        ).grid(row=0, column=2, padx=4, pady=2)
        ttk.Button(frame, text="Toggle Brake", command=self.toggle_brake_failure).grid(
            row=1, column=2, padx=4, pady=2
        )
        ttk.Button(
            frame, text="Toggle Signal", command=self.toggle_signal_failure
        ).grid(row=2, column=2, padx=4, pady=2)
        ttk.Button(
            frame, text="Toggle E‑Brake", command=self.toggle_emergency_brake
        ).grid(row=3, column=2, padx=4, pady=2)
        frame.columnconfigure(1, weight=1)

    def create_control_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Controls", style="Header.TLabelframe")
        frame.grid(row=2, column=0, sticky="NSEW", padx=4, pady=4)
        ttk.Label(
            frame,
            text="Controlled by Train Controller (train_states.json)",
            style="Data.TLabel",
        ).pack(anchor="w", padx=8, pady=2)
        self.btn_emergency = ttk.Button(
            frame, text="Toggle Emergency Brake", command=self.toggle_emergency_brake
        )
        self.btn_emergency.pack(fill="x", padx=8, pady=6)

    def create_announcements_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Announcements", style="Header.TLabelframe")
        frame.grid(row=2, column=1, sticky="NSEW", padx=4, pady=4)
        self.announcement_box = tk.Text(
            frame, height=4, wrap="word", state="disabled", bg="white"
        )
        self.announcement_box.pack(fill="both", expand=True, padx=6, pady=6)

    # === Flag toggles (unchanged semantics) ===
    def toggle_emergency_brake(self):
        self._toggle_flag("emergency_brake")

    def toggle_engine_failure(self):
        self._toggle_flag("engine_failure")

    def toggle_brake_failure(self):
        self._toggle_flag("brake_failure")

    def toggle_signal_failure(self):
        self._toggle_flag("signal_failure")

    def _toggle_flag(self, flag_name: str):
        flag_map = {
            "engine_failure": "train_model_engine_failure",
            "brake_failure": "train_model_brake_failure",
            "signal_failure": "train_model_signal_failure",
        }
        if flag_name == "emergency_brake":
            all_states = safe_read_json(TRAIN_STATES_FILE)
            if self.train_id is None:
                current = bool(all_states.get(flag_name, False))
                all_states[flag_name] = not current
                new_val = all_states[flag_name]
            else:
                key = f"train_{self.train_id}"
                sect = all_states.get(key, {})
                current = bool(sect.get(flag_name, False))  # FIX: read actual value
                sect[flag_name] = not current
                all_states[key] = sect
                new_val = sect[flag_name]
            safe_write_json(TRAIN_STATES_FILE, all_states)
        else:
            train_data = safe_read_json(self.train_data_path)
            if not isinstance(train_data, dict):
                train_data = {}
            mapped_flag = flag_map.get(flag_name, flag_name)
            if self.train_id is None:
                if "inputs" not in train_data:
                    train_data["inputs"] = {}
                inputs = train_data["inputs"]
                current = bool(inputs.get(mapped_flag, False))
                inputs[mapped_flag] = not current
                new_val = inputs[mapped_flag]
            else:
                key = f"train_{self.train_id}"
                if key not in train_data:
                    train_data[key] = {}
                sect = train_data[key]
                if "inputs" not in sect:
                    sect["inputs"] = {}
                inputs = sect["inputs"]
                current = bool(inputs.get(mapped_flag, False))
                inputs[mapped_flag] = not current
                sect["inputs"] = inputs
                train_data[key] = sect
                new_val = inputs[mapped_flag]
            safe_write_json(self.train_data_path, train_data)

        key_map = {
            "engine_failure": "Engine Failure",
            "brake_failure": "Brake Failure",
            "signal_failure": "Signal Failure",
            "emergency_brake": "Emergency Brake",
        }
        ui_key = key_map.get(flag_name)
        if ui_key and ui_key in self.fail_labels:
            self.fail_labels[ui_key].config(
                text="On" if new_val else "Off",
                style="Status.On.TLabel" if new_val else "Status.Off.TLabel",
            )
        self.after(50, lambda: self._run_cycle(schedule=False))

    # === Controller state IO ===
    def get_train_state(self):
        """Read Train Controller outputs from train_states.json"""
        all_states = safe_read_json(TRAIN_STATES_FILE)
        if self.train_id is None:
            # Legacy mode: read from outputs section at root
            if 'outputs' in all_states:
                return all_states['outputs']
            return all_states
        else:
            # Multi-train: read from outputs section of train_X
            key = f"train_{self.train_id}"
            section = all_states.get(key, {})
            if 'outputs' in section:
                return section['outputs']
            return section

    def update_train_state(self, updates: dict):
        # Remote mode: only if requests is available
        if self.server_url and self.train_id is not None and requests is not None:
            try:
                response = requests.post(
                    f"{self.server_url}/api/train/{self.train_id}/state",
                    json=updates,
                    timeout=2.0,
                )
                if response.status_code != 200:
                    print(
                        f"[Train Model] Server update returned {response.status_code}"
                    )
            except Exception as e:
                print(f"[Train Model] Error updating state on server: {e}")
            return

        # Local mode: write to file (inputs section)
        all_states = safe_read_json(TRAIN_STATES_FILE)
        
        # CRITICAL: If read failed and returned empty dict, DON'T write!
        # This prevents resetting the entire state due to race conditions
        if not all_states and os.path.exists(TRAIN_STATES_FILE):
            # File exists but read failed (race condition) - skip this write
            print(f"[Train Model] Skipping write due to read failure (race condition)")
            return
        
        if self.train_id is None:
            # Legacy mode: write to inputs section at root
            if 'inputs' not in all_states:
                all_states['inputs'] = {}
            all_states['inputs'].update(updates)
        else:
            key = f"train_{self.train_id}"
            # Preserve existing outputs section if train exists
            if key not in all_states:
                all_states[key] = {'inputs': {}, 'outputs': {}}
            
            # CRITICAL: Preserve existing outputs - don't overwrite!
            # Save existing outputs if they exist
            if 'outputs' in all_states[key]:
                existing_outputs = all_states[key]['outputs'].copy()
            else:
                existing_outputs = None
            
            # Update only inputs section
            if 'inputs' not in all_states[key]:
                all_states[key]['inputs'] = {}
            all_states[key]['inputs'].update(updates)
            
            # Restore outputs (preserve them!)
            if existing_outputs is not None:
                all_states[key]['outputs'] = existing_outputs
            else:
                all_states[key]['outputs'] = {}
                
        safe_write_json(TRAIN_STATES_FILE, all_states)

    def write_train_data(self, specs, outputs, td_inputs):
        # Outputs = Train Model computed values (motion + temperature + doors + station)
        outputs_to_write = {
            "velocity_mph": outputs.get("velocity_mph", 0.0),
            "acceleration_ftps2": outputs.get("acceleration_ftps2", 0.0),
            "position_yds": outputs.get("position_yds", 0.0),
            "authority_yds": outputs.get("authority_yds", 0.0),
            "temperature_F": outputs.get("temperature_F", 70.0),
            "station_name": outputs.get("station_name", ""),
            "next_station": outputs.get("next_station", ""),
            "left_door_open": outputs.get("left_door_open", False),
            "right_door_open": outputs.get("right_door_open", False),
            "door_side": td_inputs.get("side_door", ""),
            "commanded_speed": td_inputs.get("commanded speed", 0.0),
            "speed_limit": outputs.get("speed_limit", 0.0)
        }
        
        # Keep all inputs as-is (they update the outputs through the model)
        filtered_inputs = dict(td_inputs) if isinstance(td_inputs, dict) else {}
        
        # PHASE 3: Use API client if available, otherwise fall back to file I/O
        if self.api_client:
            # Use REST API to write physics outputs
            try:
                self.api_client.update_physics(
                    velocity=outputs_to_write["velocity_mph"],
                    position=outputs_to_write["position_yds"],
                    acceleration=outputs_to_write["acceleration_ftps2"],
                    temperature=outputs_to_write["temperature_F"]
                )
                # Update beacon data (station info, doors)
                self.api_client.update_beacon_data(
                    station_name=outputs_to_write["station_name"],
                    next_station=outputs_to_write["next_station"],
                    left_door_open=outputs_to_write["left_door_open"],
                    right_door_open=outputs_to_write["right_door_open"],
                    door_side=outputs_to_write["door_side"],
                    commanded_speed=outputs_to_write["commanded_speed"],
                    speed_limit=outputs_to_write["speed_limit"]
                )
                return  # Success! Don't write to file
            except Exception as e:
                print(f"[Train Model {self.train_id}] API write failed: {e}, falling back to file I/O")
                # Fall through to file I/O on error
        
        # Legacy file I/O (fallback or when API client not available)
        data = safe_read_json(self.train_data_path)
        if not isinstance(data, dict):
            data = {}
        data.setdefault("specs", data.get("specs", self.specs))
        data.setdefault("inputs", data.get("inputs", {}))
        data.setdefault("outputs", data.get("outputs", {}))
        
        if self.train_id is None:
            current_inputs = data.get("inputs", {})
            # Preserve failure flags from current inputs
            for flag in [
                "train_model_engine_failure",
                "train_model_signal_failure",
                "train_model_brake_failure",
            ]:
                if flag in current_inputs:
                    filtered_inputs[flag] = current_inputs[flag]
            data["specs"] = specs
            data["inputs"] = filtered_inputs
            data["outputs"] = outputs_to_write
        else:
            key = f"train_{self.train_id}"
            if key not in data:
                data[key] = {}
            current_inputs = data.get(key, {}).get("inputs", {})
            # Preserve failure flags from current inputs
            for flag in [
                "train_model_engine_failure",
                "train_model_signal_failure",
                "train_model_brake_failure",
            ]:
                if flag in current_inputs:
                    filtered_inputs[flag] = current_inputs[flag]
            data[key]["specs"] = specs
            data[key]["inputs"] = filtered_inputs
            data[key]["outputs"] = outputs_to_write
        safe_write_json(self.train_data_path, data)

    def update_loop(self):
        if not self.winfo_exists():
            return
        self._run_cycle(schedule=True)

    def _run_cycle(self, schedule: bool):
        # Sync wayside controller data to train inputs first
        # (Skip if using API - server handles this sync automatically)
        if not self.api_client:
            sync_wayside_to_train_data()
        
        td = ensure_train_data(self.train_data_path)
        ctrl = self.get_train_state()
        idx = max(((self.train_id or 1) - 1), 0)
        track_in = read_track_input(idx)

        if self.train_id is not None and f"train_{self.train_id}" in td:
            td_inputs_check = td[f"train_{self.train_id}"].get("inputs", {})
        else:
            td_inputs_check = td.get("inputs", {})

        signal_failure_active = td_inputs_check.get("train_model_signal_failure", False)
        beacon_read_blocked = False

        beacon_source = {}
        for k in [
            "speed limit",
            "side_door",
            "current station",
            "next station",
            "passengers_boarding",
        ]:
            if k in track_in:
                beacon_source[k] = track_in[k]
            elif k in td_inputs_check:
                beacon_source[k] = td_inputs_check[k]

        if signal_failure_active:
            beacon_changed = any(
                k in beacon_source
                and k in self._last_beacon_inputs
                and beacon_source[k] != self._last_beacon_inputs[k]
                for k in ["speed limit", "side_door", "current station", "next station"]
            )
            if beacon_changed:
                beacon_read_blocked = True
                for k in [
                    "speed limit",
                    "side_door",
                    "current station",
                    "next station",
                    "passengers_boarding",
                ]:
                    if k in self._last_beacon_inputs:
                        track_in[k] = self._last_beacon_inputs[k]
            else:
                for k in [
                    "speed limit",
                    "side_door",
                    "current station",
                    "next station",
                    "passengers_boarding",
                ]:
                    if k in beacon_source:
                        self._last_beacon_inputs[k] = beacon_source[k]
        else:
            for k in [
                "speed limit",
                "side_door",
                "current station",
                "next station",
                "passengers_boarding",
            ]:
                if k in beacon_source:
                    self._last_beacon_inputs[k] = beacon_source[k]

        if self.train_id is not None and f"train_{self.train_id}" in td:
            td_section = td[f"train_{self.train_id}"]
            td_inputs = td_section.get("inputs", td.get("inputs", {}))
            specs_for_write = td_section.get("specs", td.get("specs", DEFAULT_SPECS))
        else:
            td_inputs = td.get("inputs", {})
            specs_for_write = td.get("specs", DEFAULT_SPECS)

        onboard_fallback = td_inputs.get("passengers_onboard", 0)
        merged_inputs = merge_inputs(td_inputs, track_in, ctrl, onboard_fallback)

        outputs = self.model.update(
            commanded_speed=merged_inputs.get("commanded speed", 0.0),
            commanded_authority=merged_inputs.get("commanded authority", 0.0),
            speed_limit=merged_inputs.get("speed limit", 0.0),
            current_station=merged_inputs.get("current station", ""),
            next_station=merged_inputs.get("next station", ""),
            side_door=merged_inputs.get("side_door", ""),
            power_command=ctrl.get("power_command", 0.0),
            emergency_brake=ctrl.get("emergency_brake", False),
            service_brake=ctrl.get("service_brake", False),
            engine_failure=merged_inputs.get("train_model_engine_failure", False),
            brake_failure=merged_inputs.get("train_model_brake_failure", False),
            set_temperature=ctrl.get("set_temperature", 0.0),
            left_door=ctrl.get("left_door", False),
            right_door=ctrl.get("right_door", False),
            driver_velocity=ctrl.get("driver_velocity", 0.0),
        )

        passengers_onboard = int(merged_inputs.get("passengers_onboard", 0))
        disembarking, self._last_disembark_state = compute_passengers_disembarking(
            self._last_disembark_state,
            outputs["station_name"],
            outputs["velocity_mph"],
            passengers_onboard,
            self.model.crew_count,
        )
        # Update motion state in track_model_Train_Model.json (no passengers_disembarking feedback)
        update_track_motion(
            idx,  # train index derived earlier
            outputs["acceleration_ftps2"],
            outputs["velocity_mph"],
        )

        self.write_train_data(specs_for_write, outputs, td_inputs)

        remaining_authority = outputs["authority_yds"]  # FIX: define before use

        if signal_failure_active and self._last_beacon_inputs:
            controller_updates = {
                "train_velocity": outputs["velocity_mph"],
                "train_temperature": outputs["temperature_F"],
                "commanded_authority": remaining_authority,
                "current_station": self._last_beacon_inputs.get("current station", ""),
                "next_stop": self._last_beacon_inputs.get("next station", ""),
                "station_side": self._last_beacon_inputs.get("side_door", ""),
                "beacon_read_blocked": beacon_read_blocked,
            }
        else:
            controller_updates = {
                "train_velocity": outputs["velocity_mph"],
                "train_temperature": outputs["temperature_F"],
                "commanded_authority": remaining_authority,
                "current_station": merged_inputs.get("current station", ""),
                "next_stop": merged_inputs.get("next station", ""),
                "station_side": merged_inputs.get("side_door", ""),
                "beacon_read_blocked": beacon_read_blocked,
            }
        self.update_train_state(controller_updates)

        self._update_ui(outputs, ctrl, merged_inputs, disembarking)
        if schedule and self.winfo_exists():
            try:
                self.after(int(self.model.dt * 1000), self.update_loop)
            except tk.TclError:
                # Widget destroyed, stop scheduling
                pass

    def _update_ui(self, outputs, ctrl, merged_inputs, disembarking):
        try:
            self.info_labels["Velocity (mph)"].config(text=f"{outputs['velocity_mph']:.2f}")
            self.info_labels["Acceleration (ft/s²)"].config(
                text=f"{outputs['acceleration_ftps2']:.2f}"
            )
            self.info_labels["Position (yds)"].config(text=f"{outputs['position_yds']:.1f}")
            self.info_labels["Authority Remaining (yds)"].config(
                text=f"{outputs['authority_yds']:.1f}"
            )
            self.info_labels["Train Temperature (°F)"].config(
                text=f"{outputs['temperature_F']:.1f}"
            )
            self.info_labels["Set Temperature (°F)"].config(
                text=f"{ctrl.get('set_temperature', 0.0):.1f}"
            )
            self.info_labels["Current Station"].config(
                text=f"{outputs['station_name'] or ''}"
            )
            self.info_labels["Next Station"].config(text=f"{outputs['next_station'] or ''}")
            # FIX: speed limit is part of merged inputs, not outputs
            self.info_labels["Speed Limit (mph)"].config(
                text=f"{merged_inputs.get('speed limit', 0.0):.0f}"
            )
        except tk.TclError:
            # Widget has been destroyed, stop updating
            return

        try:
            def door_style(open_):
                return "Status.On.TLabel" if open_ else "Status.Off.TLabel"

            self.env_labels["Left Door"].config(
                text="Open" if outputs["left_door_open"] else "Closed",
                style=door_style(outputs["left_door_open"]),
            )
            self.env_labels["Right Door"].config(
                text="Open" if outputs["right_door_open"] else "Closed",
                style=door_style(outputs["right_door_open"]),
            )
            self.env_labels["Interior Lights"].config(
                text="On" if ctrl.get("interior_lights") else "Off",
                style=door_style(ctrl.get("interior_lights")),
            )
            self.env_labels["Exterior Lights"].config(
                text="On" if ctrl.get("exterior_lights") else "Off",
                style=door_style(ctrl.get("exterior_lights")),
            )
        except tk.TclError:
            return

        try:
            def set_flag(lbl_key, on):
                self.fail_labels[lbl_key].config(
                    text="On" if on else "Off",
                    style="Status.On.TLabel" if on else "Status.Off.TLabel",
                )

            set_flag(
                "Engine Failure",
                bool(merged_inputs.get("train_model_engine_failure", False)),
            )
            set_flag(
                "Brake Failure", bool(merged_inputs.get("train_model_brake_failure", False))
            )
            set_flag(
                "Signal Failure",
                bool(merged_inputs.get("train_model_signal_failure", False)),
            )
            set_flag("Emergency Brake", bool(ctrl.get("emergency_brake", False)))
        except tk.TclError:
            return

        try:
            self.announcement_box.config(state="normal")
            self.announcement_box.delete("1.0", "end")
            announcement = ctrl.get("announcement", "")
            if announcement:
                self.announcement_box.insert("1.0", announcement)
            else:
                self.announcement_box.insert(
                    "1.0", f"Running\nDisembark: {disembarking}"
                )
            self.announcement_box.config(state="disabled")
        except Exception:
            pass

    def _watch_files(self):
        paths = {
            "track": os.path.abspath(TRACK_INPUT_FILE),
            "ctrl": os.path.abspath(TRAIN_STATES_FILE),
            "train_data": os.path.abspath(self.train_data_path),
        }
        while not self._stop_event.is_set():
            try:
                changed = False
                for key, p in paths.items():
                    mt = os.path.getmtime(p) if os.path.exists(p) else 0.0
                    if mt != self._last_mtimes.get(key, 0.0):
                        self._last_mtimes[key] = mt
                        changed = True
                if changed:
                    try:
                        self.after(1, lambda: self._run_cycle(schedule=False))
                    except tk.TclError:
                        # Widget destroyed, stop trying to update
                        break
            except Exception:
                pass
            time.sleep(0.2)

    def on_close(self):
        self._stop_event.set()
        self.destroy()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train Model UI")
    parser.add_argument(
        "--train-id",
        type=int,
        default=None,
        help="Train ID for multi-train mode (default: legacy single-train)",
    )
    parser.add_argument(
        "--server",
        type=str,
        default=None,
        help="Server URL for remote mode (e.g., http://192.168.1.100:5000)",
    )
    args = parser.parse_args()

    # Create root window for standalone mode
    root = tk.Tk()
    root.title(f"Train Model - Train {args.train_id if args.train_id else 'Single'}")
    root.geometry("1450x900")
    
    # Create TrainModelUI frame inside root window
    app = TrainModelUI(root, train_id=args.train_id, server_url=args.server)
    app.pack(fill="both", expand=True)
    
    root.mainloop()
