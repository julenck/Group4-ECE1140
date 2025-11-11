import os, json, time, random, tkinter as tk
from tkinter import ttk
import threading

# === File paths ===
TRAIN_STATES_FILE = "../train_controller/data/train_states.json"
TRAIN_SPECS_FILE = "train_data.json"
TRACK_INPUT_FILE = "../Track_Model/track_model_Train_Model.json"
CTC_OUTPUT_FILE = "../CTC/train_model_to_ctc.json"

# Ensure cwd
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# === Safe IO ===
def safe_read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def safe_write_json(path, data):
    payload = json.dumps(data, indent=4)
    out_dir = os.path.dirname(os.path.abspath(path))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    tmp = path + ".tmp"
    # Try atomic with retries (handles Windows locks)
    for attempt in range(3):
        try:
            with open(tmp, "w") as f:
                f.write(payload)
            os.replace(tmp, path)
            return
        except PermissionError:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
            time.sleep(0.1 * (attempt + 1))
        except Exception:
            break
    # Fallback non-atomic
    with open(path, "w") as f:
        f.write(payload)

# === Train Data shape ===
DEFAULT_SPECS = {
    "length_ft": 66.0, "width_ft": 10.0, "height_ft": 11.5,
    "mass_lbs": 90100, "max_power_hp": 169,
    "max_accel_ftps2": 1.64, "service_brake_ftps2": -3.94,
    "emergency_brake_ftps2": -8.86, "capacity": 222, "crew_count": 2
}

def ensure_train_data():
    data = safe_read_json(TRAIN_SPECS_FILE)
    specs = data.get("specs", {})
    specs = {**DEFAULT_SPECS, **specs}
    inputs = data.get("inputs", {})
    outputs = data.get("outputs", {})
    fixed = {"specs": specs, "inputs": inputs, "outputs": outputs}
    if data != fixed:
        safe_write_json(TRAIN_SPECS_FILE, fixed)
    return fixed

# === Track input loader (maps underscores -> spaces) ===
def read_track_input():
    t = safe_read_json(TRACK_INPUT_FILE)
    block = t.get("block", {})
    beacon = t.get("beacon", {})
    train = t.get("train", {})
    # Map to unified keys (spaces)
    mapped = {
        "commanded speed": block.get("commanded_speed"),
        "commanded authority": block.get("commanded_authority"),
        "speed limit": beacon.get("speed_limit"),
        "side_door": beacon.get("station_side"),
        "current station": beacon.get("current_station"),
        "next station": beacon.get("next_stop"),
    }
    # Optional boarding queue support
    q = train.get("passengers_boarding_")
    if isinstance(q, list) and q:
        mapped["passengers_boarding"] = int(q[0])
    return {k: v for k, v in mapped.items() if v is not None}

# === Merge inputs (precedence: Track > train_data.inputs > controller fallbacks) ===
def merge_inputs(td_inputs: dict, track_in: dict, ctrl: dict, onboard_fallback: int):
    merged = dict(td_inputs) if td_inputs else {}
    # Override with Track
    merged.update({k: v for k, v in track_in.items() if v is not None})
    # Controller fallbacks for station fields if still missing
    merged.setdefault("next station", ctrl.get("next_stop", ""))
    merged.setdefault("side_door", ctrl.get("station_side", "Right"))
    # Passengers fields
    merged.setdefault("passengers_boarding", 0)
    merged.setdefault("passengers_onboard", onboard_fallback)
    return merged

# === CTC write (disembarking only) ===
def write_ctc_output(passengers_disembarking: int):
    safe_write_json(CTC_OUTPUT_FILE, {"passengers_disembarking": int(passengers_disembarking)})

# === Train Model core (keep your existing implementation) ===
class TrainModel:
    def __init__(self, specs):
        self.crew_count = specs.get("crew_count", 2)
        self.max_accel_ftps2 = specs.get("max_accel_ftps2", 1.64)
        self.service_brake_ftps2 = specs.get("service_brake_ftps2", -3.94)
        self.emergency_brake_ftps2 = specs.get("emergency_brake_ftps2", -8.86)
        self.velocity_mph = 0.0
        self.acceleration_ftps2 = 0.0
        self.position_yds = 0.0
        self.authority_yds = 0.0
        self.temperature_F = 68.0
        self.dt = 0.5

    def regulate_temperature(self, set_temperature):
        diff = set_temperature - self.temperature_F
        rate = 0.25
        if abs(diff) > 0.2:
            self.temperature_F += rate if diff > 0 else -rate
        return self.temperature_F

    def update(self, commanded_speed, commanded_authority, speed_limit,
               current_station, next_station, side_door, power_command=0,
               emergency_brake=False, service_brake=False,
               engine_failure=False, brake_failure=False,  # NEW failure flags
               set_temperature=70.0, left_door=False, right_door=False):
        # Emergency brake overrides all
        if emergency_brake:
            self.acceleration_ftps2 = self.emergency_brake_ftps2
        else:
            # Target-following accel
            target = min(float(commanded_speed or 0.0), float(speed_limit or commanded_speed or 0.0))
            target_ftps = target / 0.681818
            cur_ftps = self.velocity_mph / 0.681818
            dv = target_ftps - cur_ftps
            accel_cmd = max(-self.max_accel_ftps2, min(self.max_accel_ftps2, dv / self.dt))

            # Service brake only if NOT failed
            if service_brake and not brake_failure:
                self.acceleration_ftps2 = self.service_brake_ftps2
            else:
                # Engine failure disables propulsion (no positive accel), allow coasting/braking
                if engine_failure and accel_cmd > 0:
                    self.acceleration_ftps2 = 0.0
                else:
                    self.acceleration_ftps2 = accel_cmd

        self.velocity_mph = max(0.0, self.velocity_mph + self.acceleration_ftps2 * self.dt * 0.681818)
        self.position_yds += (self.velocity_mph / 0.681818) * self.dt / 3.0
        self.authority_yds = float(commanded_authority or 0.0)
        self.regulate_temperature(set_temperature)
        return {
            "velocity_mph": self.velocity_mph,
            "acceleration_ftps2": self.acceleration_ftps2,
            "position_yds": self.position_yds,
            "authority_yds": self.authority_yds,
            "station_name": current_station or "",
            "next_station": next_station or "",
            "left_door_open": bool(left_door),
            "right_door_open": bool(right_door),
            "speed_limit": float(speed_limit or 0.0),
            "temperature_F": self.temperature_F
        }

# === UI ===
class TrainModelUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Train Model")
        self.geometry("820x560")
        self.minsize(760, 520)

        # Styles
        style = ttk.Style(self)
        try: style.theme_use("vista")
        except Exception: style.theme_use("clam")
        style.configure("Header.TLabelframe", font=("Segoe UI", 10, "bold"))
        style.configure("Data.TLabel", font=("Consolas", 9))
        style.configure("Status.On.TLabel", foreground="#0a7d12")
        style.configure("Status.Off.TLabel", foreground="#b00")
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))

        # State
        td = ensure_train_data()
        self.specs = td["specs"]
        self.model = TrainModel(self.specs)
        self._last_disembark_station = None
        self._last_disembarking = 0
        self._last_beacon_inputs = {}  # NEW: freeze beacon on signal failure

        # Real-time file watch state
        self._stop_event = threading.Event()
        self._last_mtimes = {
            "track": 0.0,
            "ctrl": 0.0,
            "train_data": 0.0
        }
        # Start background watcher
        threading.Thread(target=self._watch_files, daemon=True).start()

        # Hook close to stop thread
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Layout (compact two-column)
        self.columnconfigure(0, weight=1)
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="NSEW", padx=6, pady=6)
        left.columnconfigure(0, weight=1)
        left.columnconfigure(1, weight=1)

        self.create_info_panel(left)   # row 0 col 0
        self.create_env_panel(left)    # row 0 col 1
        self.create_specs_panel(left)  # row 1 col 0
        self.create_failure_panel(left)# row 1 col 1
        self.create_control_panel(left)  # will include E-brake toggle
        self.create_announcements_panel(left)  # row 2 col 1

        # Kick off periodic loop
        self.update_loop()

    # Panels (keep your existing implementations; only key ones shown)
    def create_info_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Dynamics", style="Header.TLabelframe")
        frame.grid(row=0, column=0, sticky="NSEW", padx=4, pady=4)
        self.info_labels = {}
        fields = [
            "Velocity (mph)", "Acceleration (ft/s²)", "Position (yds)",
            "Authority Remaining (yds)", "Train Temperature (°F)",
            "Set Temperature (°F)", "Current Station", "Next Station", "Speed Limit (mph)"
        ]
        for i, key in enumerate(fields):
            ttk.Label(frame, text=key + ":", style="Data.TLabel").grid(row=i, column=0, sticky="w", padx=8, pady=2)
            lbl = ttk.Label(frame, text="--", style="Data.TLabel")
            lbl.grid(row=i, column=1, sticky="w", padx=4, pady=2)
            self.info_labels[key] = lbl
        frame.columnconfigure(1, weight=1)

    def create_env_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Env / Doors / Lights", style="Header.TLabelframe")
        frame.grid(row=0, column=1, sticky="NSEW", padx=4, pady=4)
        self.env_labels = {}
        for i, key in enumerate(["Left Door", "Right Door", "Interior Lights", "Exterior Lights"]):
            ttk.Label(frame, text=key + ":", style="Data.TLabel").grid(row=i, column=0, sticky="w", padx=8, pady=2)
            lbl = ttk.Label(frame, text="--", style="Data.TLabel")
            lbl.grid(row=i, column=1, sticky="w", padx=4, pady=2)
            self.env_labels[key] = lbl
        frame.columnconfigure(1, weight=1)

    def create_specs_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Specs", style="Header.TLabelframe")
        frame.grid(row=1, column=0, sticky="NSEW", padx=4, pady=4)
        for k, v in self.specs.items():
            ttk.Label(frame, text=f"{k}: {v}", style="Data.TLabel").pack(anchor="w", padx=8, pady=0)

    def create_failure_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Failures", style="Header.TLabelframe")
        frame.grid(row=1, column=1, sticky="NSEW", padx=4, pady=4)

        # Status labels
        self.fail_labels = {}
        row = 0
        for key in ["Engine Failure", "Brake Failure", "Signal Failure", "Emergency Brake"]:
            ttk.Label(frame, text=key + ":", style="Data.TLabel").grid(row=row, column=0, sticky="w", padx=6, pady=2)
            lbl = ttk.Label(frame, text="Off", style="Status.Off.TLabel")
            lbl.grid(row=row, column=1, sticky="w", padx=4, pady=2)
            self.fail_labels[key] = lbl
            row += 1

        # Toggle buttons
        ttk.Button(frame, text="Toggle Engine", command=self.toggle_engine_failure).grid(row=0, column=2, padx=4, pady=2)
        ttk.Button(frame, text="Toggle Brake", command=self.toggle_brake_failure).grid(row=1, column=2, padx=4, pady=2)
        ttk.Button(frame, text="Toggle Signal", command=self.toggle_signal_failure).grid(row=2, column=2, padx=4, pady=2)
        ttk.Button(frame, text="Toggle E‑Brake", command=self.toggle_emergency_brake).grid(row=3, column=2, padx=4, pady=2)

        frame.columnconfigure(1, weight=1)

    def create_control_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Controls", style="Header.TLabelframe")
        frame.grid(row=2, column=0, sticky="NSEW", padx=4, pady=4)
        ttk.Label(frame, text="Controlled by Train Controller (train_states.json)", style="Data.TLabel").pack(anchor="w", padx=8, pady=2)
        # Emergency brake toggle (writes to controller state)
        self.btn_emergency = ttk.Button(frame, text="Toggle Emergency Brake", command=self.toggle_emergency_brake)
        self.btn_emergency.pack(fill="x", padx=8, pady=6)

    def toggle_emergency_brake(self):
        self._toggle_flag("emergency_brake")

    def _toggle_flag(self, flag_name: str):
        state = self.get_train_state()
        current = bool(state.get(flag_name, False))
        state[flag_name] = not current
        safe_write_json(TRAIN_STATES_FILE, state)
        # Immediate UI refresh of that flag only
        key_map = {
            "engine_failure": "Engine Failure",
            "brake_failure": "Brake Failure",
            "signal_failure": "Signal Failure",
            "emergency_brake": "Emergency Brake"
        }
        ui_key = key_map.get(flag_name)
        if ui_key:
            self.fail_labels[ui_key].config(
                text="On" if state[flag_name] else "Off",
                style="Status.On.TLabel" if state[flag_name] else "Status.Off.TLabel"
            )

    def toggle_engine_failure(self):
        self._toggle_flag("engine_failure")

    def toggle_brake_failure(self):
        self._toggle_flag("brake_failure")

    def toggle_signal_failure(self):
        self._toggle_flag("signal_failure")

    def create_announcements_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Announcements", style="Header.TLabelframe")
        frame.grid(row=2, column=1, sticky="NSEW", padx=4, pady=4)
        self.announcement_box = tk.Text(frame, height=4, wrap="word", state='normal')
        self.announcement_box.pack(fill="both", expand=True, padx=6, pady=6)

    # Passenger logic (disembark only; CTC receives it)
    def compute_passengers_disembarking(self, station: str, velocity_mph: float, passengers_onboard: int) -> int:
        station = (station or "").strip()
        if not station or velocity_mph >= 0.5:
            return 0
        if self._last_disembark_station != station:
            crew = self.model.crew_count
            non_crew = max(0, int(passengers_onboard) - crew)
            max_out = min(30, int(non_crew * 0.4))
            count = random.randint(0, max_out) if max_out > 0 else 0
            self._last_disembark_station = station
            self._last_disembarking = count
            return count
        return int(self._last_disembarking)

    # Controller state IO
    def get_train_state(self):
        return safe_read_json(TRAIN_STATES_FILE)

    def update_train_state(self, updates: dict):
        state = self.get_train_state()
        state.update(updates)
        safe_write_json(TRAIN_STATES_FILE, state)

    # Train data IO
    def write_train_data(self, specs: dict, inputs: dict, outputs: dict):
        data = {"specs": specs, "inputs": inputs, "outputs": outputs}
        safe_write_json(TRAIN_SPECS_FILE, data)

    # Main loop (refactor into runner + scheduler)
    def update_loop(self):
        self._run_cycle(schedule=True)

    def _run_cycle(self, schedule: bool):
        # Load all sources
        td = ensure_train_data()
        ctrl = self.get_train_state()
        track_in = read_track_input()

        # Signal pickup failure -> freeze beacon-derived fields
        if ctrl.get("signal_failure", False):
            for k in ["speed limit", "side_door", "current station", "next station", "passengers_boarding"]:
                if k in self._last_beacon_inputs:
                    track_in[k] = self._last_beacon_inputs[k]
        else:
            for k in ["speed limit", "side_door", "current station", "next station", "passengers_boarding"]:
                if k in track_in:
                    self._last_beacon_inputs[k] = track_in[k]

        # Merge
        onboard_fallback = td["inputs"].get("passengers_onboard", 0)
        merged_inputs = merge_inputs(td["inputs"], track_in, ctrl, onboard_fallback)

        # Simulate (pass failure flags)
        outputs = self.model.update(
            commanded_speed=merged_inputs.get("commanded speed", ctrl.get("commanded_speed", 0.0)),
            commanded_authority=merged_inputs.get("commanded authority", ctrl.get("commanded_authority", 0.0)),
            speed_limit=merged_inputs.get("speed limit", ctrl.get("speed_limit", 0.0)),
            current_station=merged_inputs.get("current station", ctrl.get("next_stop", "")),
            next_station=merged_inputs.get("next station", ctrl.get("next_stop", "")),
            side_door=merged_inputs.get("side_door", ctrl.get("station_side", "Right")),
            power_command=ctrl.get("power_command", 0.0),
            emergency_brake=ctrl.get("emergency_brake", False),
            service_brake=ctrl.get("service_brake", False),
            engine_failure=ctrl.get("engine_failure", False),   # NEW
            brake_failure=ctrl.get("brake_failure", False),     # NEW
            set_temperature=ctrl.get("set_temperature", 70.0),
            left_door=ctrl.get("left_door", False),
            right_door=ctrl.get("right_door", False)
        )

        # Passengers -> CTC
        passengers_onboard = int(merged_inputs.get("passengers_onboard", 0))
        passengers_boarding = int(merged_inputs.get("passengers_boarding", 0))
        disembarking = self.compute_passengers_disembarking(
            outputs["station_name"], outputs["velocity_mph"], passengers_onboard
        )
        write_ctc_output(disembarking)

        # Write train_data.json (echo inputs + outputs)
        td_outputs = {
            **outputs,
            "door_side": merged_inputs.get("side_door", "Right"),
            "passengers_onboard": passengers_onboard,
            "passengers_boarding": passengers_boarding,
            "passengers_disembarking": disembarking
        }
        self.write_train_data(self.specs, merged_inputs, td_outputs)

        # Update controller state (for UI/telemetry)
        self.update_train_state({
            "train_velocity": outputs["velocity_mph"],
            "train_temperature": outputs["temperature_F"],
            "next_stop": merged_inputs.get("next station", ""),
            "station_side": merged_inputs.get("side_door", "Right")
        })

        # UI updates
        self.info_labels["Velocity (mph)"].config(text=f"{outputs['velocity_mph']:.2f}")
        self.info_labels["Acceleration (ft/s²)"].config(text=f"{outputs['acceleration_ftps2']:.2f}")
        self.info_labels["Position (yds)"].config(text=f"{outputs['position_yds']:.1f}")
        self.info_labels["Authority Remaining (yds)"].config(text=f"{outputs['authority_yds']:.1f}")
        self.info_labels["Train Temperature (°F)"].config(text=f"{outputs['temperature_F']:.1f}")
        self.info_labels["Set Temperature (°F)"].config(text=f"{ctrl.get('set_temperature', 70.0):.1f}")
        self.info_labels["Current Station"].config(text=f"{outputs['station_name'] or '—'}")
        self.info_labels["Next Station"].config(text=f"{outputs['next_station'] or '—'}")
        self.info_labels["Speed Limit (mph)"].config(text=f"{outputs['speed_limit']:.0f}")

        self.env_labels["Left Door"].config(
            text="Open" if outputs['left_door_open'] else "Closed",
            style="Status.On.TLabel" if outputs['left_door_open'] else "Status.Off.TLabel"
        )
        self.env_labels["Right Door"].config(
            text="Open" if outputs['right_door_open'] else "Closed",
            style="Status.On.TLabel" if outputs['right_door_open'] else "Status.Off.TLabel"
        )
        self.env_labels["Interior Lights"].config(
            text="On" if ctrl.get("interior_lights") else "Off",
            style="Status.On.TLabel" if ctrl.get("interior_lights") else "Status.Off.TLabel"
        )
        self.env_labels["Exterior Lights"].config(
            text="On" if ctrl.get("exterior_lights") else "Off",
            style="Status.On.TLabel" if ctrl.get("exterior_lights") else "Status.Off.TLabel"
        )

        # Failure panel statuses
        def set_flag(lbl_key, on):
            self.fail_labels[lbl_key].config(
                text="On" if on else "Off",
                style="Status.On.TLabel" if on else "Status.Off.TLabel"
            )
        set_flag("Engine Failure", bool(ctrl.get("engine_failure", False)))
        set_flag("Brake Failure", bool(ctrl.get("brake_failure", False)))
        set_flag("Signal Failure", bool(ctrl.get("signal_failure", False)))
        set_flag("Emergency Brake", bool(ctrl.get("emergency_brake", False)))

        self.announcement_box.config(state='normal')
        self.announcement_box.delete("1.0", "end")
        self.announcement_box.insert("end", f"Running\nDisembark: {disembarking}")
        self.announcement_box.config(state='disabled')

        if schedule:
            self.after(int(self.model.dt * 1000), self.update_loop)

    # Background watcher: triggers immediate cycle when any source changes
    def _watch_files(self):
        paths = {
            "track": os.path.abspath(TRACK_INPUT_FILE),
            "ctrl": os.path.abspath(TRAIN_STATES_FILE),
            "train_data": os.path.abspath(TRAIN_SPECS_FILE),
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
                    # Run one immediate cycle in GUI thread
                    self.after(1, lambda: self._run_cycle(schedule=False))
            except Exception:
                pass
            time.sleep(0.2)  # 5 Hz polling

    def on_close(self):
        self._stop_event.set()
        self.destroy()
# Entrypoint
if __name__ == "__main__":
    app = TrainModelUI()
    app.mainloop()

