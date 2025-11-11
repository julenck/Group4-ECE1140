import os
import json
import random
import tkinter as tk
from tkinter import ttk

# === File paths ===
TRAIN_STATES_FILE = "../train_controller/data/train_states.json"
TRACK_INPUT_FILE = "../Track_Model/track_model_to_Train_Model.json"
TRACK_OUTPUT_FILE = "../Track_Model/train_model_to_track_model.json"
TRAIN_DATA_FILE = "train_data.json"

# Ensure relative paths resolve from this folder
os.chdir(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_SPECS = {
    "length_ft": 66.0,
    "width_ft": 10.0,
    "height_ft": 11.5,
    "mass_lbs": 90100,
    "max_power_hp": 169,
    "max_accel_ftps2": 1.64,
    "service_brake_ftps2": -3.94,
    "emergency_brake_ftps2": -8.86,
    "capacity": 222,
    "crew_count": 2
}

class TrainModel:
    def __init__(self, specs):
        """Initialize train model with static specifications"""
        self.length = specs["length_ft"]
        self.width = specs["width_ft"]
        self.height = specs["height_ft"]
        self.mass_lbs = specs["mass_lbs"]
        self.max_power_hp = specs["max_power_hp"]
        self.max_accel_ftps2 = specs["max_accel_ftps2"]
        self.service_brake_ftps2 = specs["service_brake_ftps2"]
        self.emergency_brake_ftps2 = specs["emergency_brake_ftps2"]
        self.capacity = specs["capacity"]
        self.crew_count = specs["crew_count"]

        # Dynamic states
        self.velocity_mph = 0.0
        self.acceleration_ftps2 = 0.0
        self.position_yds = 0.0
        self.temperature_F = 68.0
        self.authority_yds = 0.0
        self.dt = 0.5  # update period (s)

        # Environment and route
        self.left_door_open = False
        self.right_door_open = False
        self.lights_on = True
        self.current_station = "Unknown"
        self.next_station = "Unknown"

    def regulate_temperature(self, set_temperature):
        """Regulate train temperature toward set temperature."""
        temp_error = set_temperature - self.temperature_F
        max_rate = 0.025  # °F per update cycle (about 3°F/min)
        if abs(temp_error) > 0.25:
            step = max_rate if temp_error > 0 else -max_rate
            self.temperature_F += step
        return round(self.temperature_F * 2) / 2

    def update(self, commanded_speed, commanded_authority, speed_limit,
               current_station, next_station, side_door, power_command=0,
               emergency_brake=False, service_brake=False, set_temperature=70.0,
               left_door=False, right_door=False,
               engine_failure=False, brake_failure=False):
        # Priority: Emergency brake overrides everything
        if emergency_brake:
            self.acceleration_ftps2 = self.emergency_brake_ftps2
        else:
            # Service brake unless failed
            if service_brake and not brake_failure:
                self.acceleration_ftps2 = self.service_brake_ftps2
            else:
                # Basic target speed tracking within limit
                target_mph = min(commanded_speed, speed_limit if speed_limit > 0 else commanded_speed)
                target_ftps = target_mph / 0.681818
                current_ftps = self.velocity_mph / 0.681818
                diff = target_ftps - current_ftps
                accel_max = self.max_accel_ftps2
                raw_accel = max(-accel_max, min(accel_max, diff / self.dt))
                # Engine failure = no positive propulsion (coast/brake only)
                if engine_failure and raw_accel > 0:
                    raw_accel = 0.0
                self.acceleration_ftps2 = raw_accel

        # Integrate motion
        delta_v_ftps = self.acceleration_ftps2 * self.dt
        delta_v_mph = delta_v_ftps * 0.681818
        self.velocity_mph = max(self.velocity_mph + delta_v_mph, 0.0)
        delta_x_ft = (self.velocity_mph / 0.681818) * self.dt
        self.position_yds += delta_x_ft / 3.0
        self.authority_yds = commanded_authority

        # Env and route
        self.left_door_open = left_door
        self.right_door_open = right_door
        self.regulate_temperature(set_temperature)
        self.current_station = current_station or self.current_station
        self.next_station = next_station or self.next_station

        return {
            "velocity_mph": self.velocity_mph,
            "acceleration_ftps2": self.acceleration_ftps2,
            "position_yds": self.position_yds,
            "authority_yds": self.authority_yds,
            "station_name": self.current_station,
            "next_station": self.next_station,
            "left_door_open": self.left_door_open,
            "right_door_open": self.right_door_open,
            "speed_limit": speed_limit,
            "temperature_F": self.temperature_F
        }

class TrainModelUI(tk.Tk):
    def __init__(self):
        # Paths/specs before tk init
        self.train_states_path = TRAIN_STATES_FILE
        self.train_data_path = TRAIN_DATA_FILE
        self.track_input_path = TRACK_INPUT_FILE
        self.track_output_path = TRACK_OUTPUT_FILE
        self.specs = self._load_or_default_specs()

        super().__init__()
        self.title("Train Model")
        self.geometry("960x720")
        self.minsize(900, 620)

        # Apply a nicer ttk theme and styles
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except Exception:
            style.theme_use("clam")

        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Section.TLabelframe", padding=12)
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 11, "bold"))
        style.configure("KPI.TFrame", padding=10, relief="ridge")
        style.configure("KPIName.TLabel", font=("Segoe UI", 9), foreground="#666")
        style.configure("KPIValue.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Key.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Val.TLabel", font=("Consolas", 11))

        # Core model
        self.model = TrainModel(self.specs)
        state = self.get_train_state()
        self.model.temperature_F = state.get("train_temperature", 68.0)

        # Failures/safety
        self.engine_failure = False
        self.signal_failure = False
        self.brake_failure = False
        self.emergency_brake = False
        self._last_beacon = {}

        # Passengers
        self.passengers_onboard = self.specs.get("crew_count", 0)  # start with crew
        self.boarding_last_cycle = 0
        self.last_disembark_station = None
        self.last_passengers_disembarking = 0
        self.last_station_processed = None  # NEW: track last station where adjustment applied

        # UI containers
        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=2)
        container.columnconfigure(1, weight=1)

        # Header
        ttk.Label(container, text="Train Model Monitor", style="Title.TLabel").grid(row=0, column=0, sticky="w")

        # KPI row
        kpi_row = ttk.Frame(container)
        kpi_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 12))
        for i in range(3):
            kpi_row.columnconfigure(i, weight=1)

        self._kpi_velocity = self._build_kpi(kpi_row, 0, "Velocity", "0.0 mph")
        self._kpi_accel = self._build_kpi(kpi_row, 1, "Acceleration", "0.00 ft/s²")
        self._kpi_temp = self._build_kpi(kpi_row, 2, "Temperature", "68.0 °F")

        # Left column: Train Info + Environment
        left_col = ttk.Frame(container)
        left_col.grid(row=2, column=0, sticky="nsew", padx=(0, 8))
        left_col.columnconfigure(0, weight=1)

        # Right column: Failures + Passengers
        right_col = ttk.Frame(container)
        right_col.grid(row=2, column=1, sticky="nsew", padx=(8, 0))
        right_col.columnconfigure(0, weight=1)

        # Build sections
        self.info_labels = {}
        self.env_labels = {}

        self._build_train_info(left_col)          # fills self.info_labels
        self._build_environment(left_col)         # fills self.env_labels
        self.build_failure_controls(parent=right_col)
        self.build_passenger_ui(parent=right_col)

        # Status bar
        self._build_status_bar(self)

        # Start loop
        self.after_id = None
        self.update_loop()

    def _load_or_default_specs(self):
        if os.path.exists(TRAIN_DATA_FILE):
            try:
                with open(TRAIN_DATA_FILE, "r") as f:
                    data = json.load(f)
                specs = data.get("specs", {})
                for k, v in DEFAULT_SPECS.items():
                    specs.setdefault(k, v)
                return specs
            except Exception:
                pass
        return DEFAULT_SPECS

    # Helper to build KPI card
    def _build_kpi(self, parent, col, name, initial_text):
        card = ttk.Frame(parent, style="KPI.TFrame")
        card.grid(row=0, column=col, sticky="nsew", padx=6)
        ttk.Label(card, text=name.upper(), style="KPIName.TLabel").pack(anchor="w")
        val = ttk.Label(card, text=initial_text, style="KPIValue.TLabel")
        val.pack(anchor="w")
        return val

    # Replaces old build_basic_ui with cleaner grid layout
    def _build_train_info(self, parent):
        frame = ttk.Labelframe(parent, text="Train Info", style="Section.TLabelframe")
        frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        items = [
            "Velocity (mph)", "Acceleration (ft/s²)", "Position (yds)",
            "Authority Remaining (yds)", "Train Temperature (°F)",
            "Set Temperature (°F)", "Current Station", "Next Station", "Speed Limit (mph)"
        ]
        for i, key in enumerate(items):
            ttk.Label(frame, text=key + ":", style="Key.TLabel").grid(row=i, column=0, sticky="w", padx=(4, 6), pady=2)
            lbl = ttk.Label(frame, text="—", style="Val.TLabel")
            lbl.grid(row=i, column=1, sticky="w", padx=(0, 4), pady=2)
            self.info_labels[key] = lbl

    def _build_environment(self, parent):
        env = ttk.Labelframe(parent, text="Environment", style="Section.TLabelframe")
        env.grid(row=1, column=0, sticky="nsew")
        ttk.Label(env, text="Left Door:", style="Key.TLabel").grid(row=0, column=0, sticky="w", padx=(4,6), pady=2)
        self.env_labels["Left Door"] = ttk.Label(env, text="Closed", style="Val.TLabel")
        self.env_labels["Left Door"].grid(row=0, column=1, sticky="w", padx=(0,4), pady=2)
        ttk.Label(env, text="Right Door:", style="Key.TLabel").grid(row=1, column=0, sticky="w", padx=(4,6), pady=2)
        self.env_labels["Right Door"] = ttk.Label(env, text="Closed", style="Val.TLabel")
        self.env_labels["Right Door"].grid(row=1, column=1, sticky="w", padx=(0,4), pady=2)

    # --- Updated to nicer layout; parent can be provided ---
    def build_failure_controls(self, parent=None):
        parent = parent or self
        frm = ttk.Labelframe(parent, text="Failures / Safety", style="Section.TLabelframe")
        frm.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        for c in range(2):
            frm.columnconfigure(c, weight=1)

        self.var_engine = tk.BooleanVar(value=False)
        self.var_signal = tk.BooleanVar(value=False)
        self.var_brake = tk.BooleanVar(value=False)
        self.var_emergency = tk.BooleanVar(value=False)

        ttk.Checkbutton(frm, text="Engine Failure", variable=self.var_engine,
                        command=self._on_failure_toggle).grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Checkbutton(frm, text="Signal Pickup Failure", variable=self.var_signal,
                        command=self._on_failure_toggle).grid(row=0, column=1, sticky="w", padx=4, pady=2)
        ttk.Checkbutton(frm, text="Brake Failure", variable=self.var_brake,
                        command=self._on_failure_toggle).grid(row=1, column=0, sticky="w", padx=4, pady=2)
        ttk.Checkbutton(frm, text="Emergency Brake", variable=self.var_emergency,
                        command=self._on_emergency_toggle).grid(row=1, column=1, sticky="w", padx=4, pady=2)

        # Status line
        self.fail_status_lbl = ttk.Label(frm, text="Status: OK")
        self.fail_status_lbl.grid(row=2, column=0, columnspan=2, sticky="w", padx=4, pady=(6, 2))

    def _on_failure_toggle(self):
        self.engine_failure = self.var_engine.get()
        self.signal_failure = self.var_signal.get()
        self.brake_failure = self.var_brake.get()
        self._push_failures_to_state()
        parts = []
        if self.engine_failure: parts.append("Engine")
        if self.signal_failure: parts.append("Signal")
        if self.brake_failure: parts.append("Brake")
        self.fail_status_lbl.config(text=f"Status: {' / '.join(parts) if parts else 'OK'}")

    def _on_emergency_toggle(self):
        self.emergency_brake = self.var_emergency.get()
        self._push_failures_to_state()
        base = self.fail_status_lbl.cget("text")
        if self.emergency_brake and "EMERGENCY BRAKE" not in base:
            self.fail_status_lbl.config(text=f"{base} | EMERGENCY BRAKE")
        if not self.emergency_brake:
            self._on_failure_toggle()

    def _push_failures_to_state(self):
        self.update_train_state({
            "engine_failure": self.engine_failure,
            "signal_failure": self.signal_failure,
            "brake_failure": self.brake_failure,
            "emergency_brake": self.emergency_brake
        })

    # --- Updated passengers section; parent can be provided ---
    def build_passenger_ui(self, parent=None):
        parent = parent or self
        frm = ttk.Labelframe(parent, text="Passengers", style="Section.TLabelframe")
        frm.grid(row=1, column=0, sticky="nsew")
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text="Onboard:", style="Key.TLabel").grid(row=0, column=0, sticky="w", padx=(4,6), pady=2)
        self.lbl_onboard = ttk.Label(frm, text=f"{self.passengers_onboard}", style="Val.TLabel")
        self.lbl_onboard.grid(row=0, column=1, sticky="w", padx=(0,4), pady=2)

        ttk.Label(frm, text="Boarding:", style="Key.TLabel").grid(row=1, column=0, sticky="w", padx=(4,6), pady=2)
        self.lbl_boarding = ttk.Label(frm, text="0", style="Val.TLabel")
        self.lbl_boarding.grid(row=1, column=1, sticky="w", padx=(0,4), pady=2)

        ttk.Label(frm, text="Disembarking:", style="Key.TLabel").grid(row=2, column=0, sticky="w", padx=(4,6), pady=2)
        self.lbl_disembark = ttk.Label(frm, text="0", style="Val.TLabel")
        self.lbl_disembark.grid(row=2, column=1, sticky="w", padx=(0,4), pady=2)

        cap_txt = f"Capacity: {self.specs.get('capacity', 0)} (Crew {self.specs.get('crew_count',0)})"
        ttk.Label(frm, text=cap_txt).grid(row=3, column=0, columnspan=2, sticky="w", padx=4, pady=(6,2))

    def _build_status_bar(self, root):
        bar = ttk.Frame(root)
        bar.pack(side="bottom", fill="x")
        self.status_var = tk.StringVar(value="Auto-sync: ON • Ready")
        ttk.Label(bar, textvariable=self.status_var).pack(side="left", padx=8, pady=4)

    # === Data IO helpers ===
    def get_train_state(self):
        try:
            with open(self.train_states_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def update_train_state(self, updates):
        state = self.get_train_state()
        state.update(updates)
        try:
            with open(self.train_states_path, "w") as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            print("train_states write error:", e)

    def load_track_inputs(self):
        """Read all inputs from Track Model and include passengers_onboard."""
        try:
            with open(self.track_input_path, "r") as f:
                data = json.load(f)
        except Exception:
            return {}
        block = data.get("block", {})
        beacon = data.get("beacon", {})
        if getattr(self, "signal_failure", False):
            if getattr(self, "_last_beacon", {}):
                beacon = self._last_beacon
        else:
            self._last_beacon = beacon
        return {
            "commanded speed": block.get("commanded speed", 0.0),
            "commanded authority": block.get("commanded authority", 0.0),
            "speed limit": beacon.get("speed limit", 0.0),
            "side_door": beacon.get("side_door", ""),
            "current station": beacon.get("current station", ""),
            "next station": beacon.get("next station", ""),
            "passengers_boarding": int(beacon.get("passengers_boarding", 0) or 0),
            "passengers_onboard": int(beacon.get("passengers_onboard", getattr(self, "passengers_onboard", 0)) or 0)
        }

    def adjust_passengers_at_station(self, station, velocity_mph, requested_boarding):
        """
        Apply passenger changes only once per arrival at a new station when stopped.
        Returns tuple: (disembarking_count, actual_boarding, onboard_after)
        """
        # Not stopped or no station -> no change
        if not station or velocity_mph >= 0.5:
            return (0, 0, self.passengers_onboard)

        # If already processed this station and still stopped, just reuse previous values
        if self.last_station_processed == station:
            return (self.last_passengers_disembarking, self.boarding_last_cycle, self.passengers_onboard)

        # New station arrival while stopped -> compute fresh changes
        non_crew = max(0, self.passengers_onboard - self.specs.get("crew_count", 0))
        max_disembark = min(30, int(non_crew * 0.4))
        disembark = random.randint(0, max_disembark) if max_disembark > 0 else 0
        onboard_after_disembark = max(self.specs.get("crew_count", 0),
                                      self.passengers_onboard - disembark)

        # Boarding realism: allow +-20% variation around requested_boarding, but not negative
        if requested_boarding < 0:
            requested_boarding = 0
        variation = int(requested_boarding * 0.2)
        actual_board = requested_boarding + random.randint(-variation, variation)
        actual_board = max(0, actual_board)

        # Cap by remaining capacity
        available = self.specs.get("capacity", 0) - onboard_after_disembark
        actual_board = min(actual_board, available)

        final_onboard = onboard_after_disembark + actual_board

        # Persist cycle values
        self.last_station_processed = station
        self.last_passengers_disembarking = disembark
        self.boarding_last_cycle = actual_board
        self.passengers_onboard = final_onboard

        return (disembark, actual_board, final_onboard)

    def overwrite_train_data(self, inputs, outputs):
        """Mirror Track Model passenger inputs into outputs; do not mutate onboard here."""
        state = self.get_train_state()
        inputs_full = {
            **inputs,
            "engine_failure": state.get("engine_failure", False),
            "signal_failure": state.get("signal_failure", False),
            "brake_failure": state.get("brake_failure", False),
            "emergency_brake": state.get("emergency_brake", False)
        }
        outputs_extended = {
            **outputs,
            # Echo passengers from Track Model into outputs
            "passengers_onboard": int(inputs_full.get("passengers_onboard", getattr(self, "passengers_onboard", 0)) or 0),
            "passengers_boarding": int(inputs_full.get("passengers_boarding", 0) or 0),
            "passengers_disembarking": int(getattr(self, "last_passengers_disembarking", 0) or 0)
        }
        data = {"specs": self.specs, "inputs": inputs_full, "outputs": outputs_extended}
        try:
            with open(self.train_data_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("train_data write error:", e)

    def write_track_output(self, passengers_disembarking: int):
        """Send passengers_disembarking back to the Track Model."""
        try:
            out = {"passengers_disembarking": int(passengers_disembarking)}
            # Ensure folder exists
            out_dir = os.path.dirname(os.path.abspath(self.track_output_path))
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            with open(self.track_output_path, "w") as f:
                json.dump(out, f, indent=4)
        except Exception as e:
            print("track output write error:", e)

    # === Main loop ===
    def update_loop(self):
        track_inputs = self.load_track_inputs()
        state = self.get_train_state()

        # Set from Track Model (source of truth)
        self.passengers_onboard = int(track_inputs.get("passengers_onboard", getattr(self, "passengers_onboard", 0)) or 0)
        self.boarding_last_cycle = int(track_inputs.get("passengers_boarding", 0) or 0)

        commanded_speed = track_inputs.get("commanded speed", state.get("commanded_speed", 0.0))
        commanded_authority = track_inputs.get("commanded authority", state.get("commanded_authority", 0.0))
        speed_limit = track_inputs.get("speed limit", state.get("speed_limit", commanded_speed))
        current_station = track_inputs.get("current station", "")
        next_station = track_inputs.get("next station", "")
        side_door = track_inputs.get("side_door", "Right")

        outputs_sim = self.model.update(
            commanded_speed=commanded_speed,
            commanded_authority=commanded_authority,
            speed_limit=speed_limit,
            current_station=current_station,
            next_station=next_station,
            side_door=side_door,
            power_command=state.get("power_command", 0.0),
            emergency_brake=state.get("emergency_brake", False),
            service_brake=state.get("service_brake", False),
            set_temperature=state.get("set_temperature", state.get("train_temperature", 68.0)),
            left_door=state.get("left_door", False),
            right_door=state.get("right_door", False),
            engine_failure=state.get("engine_failure", False),
            brake_failure=state.get("brake_failure", False)
        )

        # Compute disembarking only; do NOT change onboard here
        passengers_out = self.compute_passengers_disembarking(current_station, outputs_sim["velocity_mph"])
        self.last_passengers_disembarking = passengers_out

        train_model_outputs = {
            "velocity_mph": outputs_sim["velocity_mph"],
            "acceleration_ftps2": outputs_sim["acceleration_ftps2"],
            "position_yds": outputs_sim["position_yds"],
            "authority_yds": outputs_sim["authority_yds"],
            "station_name": outputs_sim["station_name"],
            "next_station": outputs_sim["next_station"],
            "left_door_open": outputs_sim["left_door_open"],
            "right_door_open": outputs_sim["right_door_open"],
            "speed_limit": outputs_sim["speed_limit"],
            "temperature_F": self.model.temperature_F,
            "door_side": side_door
        }

        # Write JSONs
        self.overwrite_train_data(track_inputs, train_model_outputs)
        self.write_track_output(passengers_out)

        # UI mirrors Track Model values
        self.lbl_onboard.config(text=f"{self.passengers_onboard}")
        self.lbl_boarding.config(text=f"{self.boarding_last_cycle}")
        self.lbl_disembark.config(text=f"{passengers_out}")

        # ...keep your other UI label updates...
        self.after(int(self.model.dt * 1000), self.update_loop)

    def compute_passengers_disembarking(self, current_station: str, velocity_mph: float) -> int:
        """Compute disembarking once when stopped at a new station.
        Does not change onboard; Track Model remains source of truth."""
        station = (current_station or "").strip()
        if not station:
            self.last_passengers_disembarking = 0
            return 0
        if velocity_mph >= 0.5:
            return 0
        if self.last_disembark_station != station:
            non_crew = max(0, int(self.passengers_onboard) - int(self.specs.get("crew_count", 0)))
            cap = min(30, int(non_crew * 0.4))
            count = random.randint(0, cap) if cap > 0 else 0
            self.last_disembark_station = station
            self.last_passengers_disembarking = count
            return count
        return int(self.last_passengers_disembarking)

if __name__ == "__main__":
    app = TrainModelUI()
    app.mainloop()

