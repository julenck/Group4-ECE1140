import tkinter as tk
import json, os, random
from tkinter import ttk
import math

# === File paths ===
TRAIN_STATES_FILE = "../train_controller/data/train_states.json"
TRAIN_SPECS_FILE = "train_data.json"
CTC_OUTPUT_FILE = "../CTC/train_model_to_ctc.json"  # NEW: send disembarking count to CTC

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# === Train Model Core ===
class TrainModel:
    def __init__(self, specs):
        """Initialize train model with static specifications"""
        self.crew_count = specs.get("crew_count", 2)
        self.length = specs["length_ft"]
        self.width = specs["width_ft"]
        self.height = specs["height_ft"]
        self.mass_lbs = specs["mass_lbs"]
        self.max_power_hp = specs["max_power_hp"]
        self.max_accel_ftps2 = specs.get("max_accel_ftps2", 1.5)
        self.service_brake_ftps2 = specs.get("service_brake_ftps2", -3.0)
        self.emergency_brake_ftps2 = specs.get("emergency_brake_ftps2", -8.0)
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
        """Gradually regulate train temperature toward set temperature"""
        temp_error = set_temperature - self.temperature_F
        max_rate = 0.025  # °F per update (≈3°F/min realistic)
        if abs(temp_error) > 0.25:
            temp_change = temp_error * 0.2
            temp_change = max(-max_rate, min(max_rate, temp_change))
            self.temperature_F += temp_change
        return round(self.temperature_F * 2) / 2

    def update(self, commanded_speed, commanded_authority, speed_limit,
               current_station, next_station, side_door, power_command=0,
               emergency_brake=False, service_brake=False, set_temperature=70.0,
               left_door=False, right_door=False):
        """Simulate motion and update state"""
        if emergency_brake:
            self.acceleration_ftps2 = self.emergency_brake_ftps2
        elif service_brake:
            self.acceleration_ftps2 = self.service_brake_ftps2
        else:
            power_watts = power_command
            if self.velocity_mph > 0.1:
                velocity_ftps = self.velocity_mph * 1.46667
                velocity_mps = velocity_ftps * 0.3048
                force_newtons = power_watts / velocity_mps
                force_lbs = force_newtons * 0.224809
                self.acceleration_ftps2 = (force_lbs / self.mass_lbs) * 32.174
            else:
                self.acceleration_ftps2 = self.max_accel_ftps2 if power_command > 0 else 0
            self.acceleration_ftps2 = max(min(self.acceleration_ftps2, self.max_accel_ftps2),
                                          self.service_brake_ftps2)

        delta_v_ftps = self.acceleration_ftps2 * self.dt
        delta_v_mph = delta_v_ftps * 0.681818
        self.velocity_mph = max(self.velocity_mph + delta_v_mph, 0)
        delta_x_ft = (self.velocity_mph / 0.681818) * self.dt
        self.position_yds += delta_x_ft / 3.0
        self.authority_yds = commanded_authority

        self.left_door_open = left_door
        self.right_door_open = right_door
        self.regulate_temperature(set_temperature)
        self.current_station = current_station
        self.next_station = next_station

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


# === Train Model UI ===
class TrainModelUI(tk.Tk):
    def __init__(self, train_id=None):
        super().__init__()
        self.train_id = train_id
        title = f"Train {train_id} - Train Model" if train_id else "Train Model - Integrated with Train Controller"
        self.title(title)
        self.geometry("1000x600")
        self.minsize(900, 550)

        self.train_states_path = TRAIN_STATES_FILE
        self.specs_path = TRAIN_SPECS_FILE

        specs = self.load_train_specs()
        self.model = TrainModel(specs)
        state = self.get_train_state()
        self.model.temperature_F = state.get("train_temperature", 68.0)

        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except Exception:
            style.theme_use("clam")
        style.configure("Header.TLabelframe", font=("Segoe UI", 10, "bold"))
        style.configure("Data.TLabel", font=("Consolas", 10))
        style.configure("Status.On.TLabel", foreground="#0a7d12")
        style.configure("Status.Off.TLabel", foreground="#b00")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        left_frame = ttk.Frame(self)
        left_frame.grid(row=0, column=0, sticky="NSEW", padx=6, pady=6)
        right_frame = ttk.Frame(self)
        right_frame.grid(row=0, column=1, sticky="NSEW", padx=6, pady=6)

        left_frame.columnconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)

        # Left side panels
        self.create_info_panel(left_frame)
        self.create_specs_panel(left_frame)
        self.create_control_panel(left_frame)

        # Right side panels
        self.create_env_panel(right_frame)
        self.create_failure_panel(right_frame)
        self.create_announcements_panel(right_frame)

        self._last_disembark_station = None
        self._last_disembarking = 0
        self.update_loop()

    # === File IO ===
    def load_train_specs(self):
        if not os.path.exists(self.specs_path):
            default_specs = {
                "specs": {
                    "length_ft": 66.0, "width_ft": 10.0, "height_ft": 11.5,
                    "mass_lbs": 90100, "max_power_hp": 161,
                    "max_accel_ftps2": 1.64, "service_brake_ftps2": -3.94,
                    "emergency_brake_ftps2": -8.86, "capacity": 222, "crew_count": 2
                }
            }
            with open(self.specs_path, "w") as f:
                json.dump(default_specs, f, indent=4)
            return default_specs["specs"]
        with open(self.specs_path, "r") as f:
            data = json.load(f)
            return data.get("specs", {})

    def get_train_state(self):
        try:
            with open(self.train_states_path, "r") as f:
                all_states = json.load(f)
                if self.train_id is not None:
                    key = f"train_{self.train_id}"
                    return all_states.get(key, self._get_default_state())
                else:
                    return all_states
        except FileNotFoundError:
            default = self._get_default_state()
            with open(self.train_states_path, "w") as f:
                json.dump(default, f, indent=4)
            return default

    def _get_default_state(self):
        return {
            "commanded_speed": 0.0, "commanded_authority": 0.0, "speed_limit": 0.0,
            "train_velocity": 0.0, "next_stop": "", "station_side": "",
            "train_temperature": 70.0, "engine_failure": False, "signal_failure": False,
            "brake_failure": False, "manual_mode": False, "driver_velocity": 0.0,
            "service_brake": False, "right_door": False, "left_door": False,
            "interior_lights": False, "exterior_lights": False, "set_temperature": 70.0,
            "emergency_brake": False, "power_command": 0.0,
            "passengers_onboard": 0, "passengers_boarding": 0, "passengers_disembarking": 0
        }

    def update_train_state(self, updates):
        with open(self.train_states_path, "r") as f:
            all_states = json.load(f)
        if self.train_id is not None:
            key = f"train_{self.train_id}"
            if key not in all_states:
                all_states[key] = self._get_default_state()
            all_states[key].update(updates)
        else:
            all_states.update(updates)
        with open(self.train_states_path, "w") as f:
            json.dump(all_states, f, indent=4)

    # === UI Panels ===
    def create_info_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Dynamics", style="Header.TLabelframe")
        frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.info_labels = {}
        fields = [
            "Velocity (mph)", "Acceleration (ft/s²)", "Position (yds)",
            "Authority Remaining (yds)", "Train Temperature (°F)",
            "Set Temperature (°F)", "Current Station", "Next Station", "Speed Limit (mph)"
        ]
        for i, key in enumerate(fields):
            ttk.Label(frame, text=f"{key}:", style="Data.TLabel").grid(row=i, column=0, sticky="w", padx=10, pady=2)
            lbl = ttk.Label(frame, text="--", style="Data.TLabel")
            lbl.grid(row=i, column=1, sticky="w", padx=4, pady=2)
            self.info_labels[key] = lbl
        frame.columnconfigure(1, weight=1)

    def create_env_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Env / Doors / Lights", style="Header.TLabelframe")
        frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.env_labels = {}
        for i, key in enumerate(["Left Door", "Right Door", "Interior Lights", "Exterior Lights"]):
            ttk.Label(frame, text=f"{key}:", style="Data.TLabel").grid(row=i, column=0, sticky="w", padx=10, pady=2)
            lbl = ttk.Label(frame, text="--", style="Data.TLabel")
            lbl.grid(row=i, column=1, sticky="w", padx=4, pady=2)
            self.env_labels[key] = lbl

    def create_specs_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Specs")
        frame.pack(fill="both", expand=True, padx=4, pady=4)
        for k, v in self.load_train_specs().items():
            ttk.Label(frame, text=f"{k}: {v}", style="Data.TLabel").pack(anchor="w", padx=6, pady=1)

    def create_control_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Controls")
        frame.pack(fill="x", padx=4, pady=4)
        ttk.Button(frame, text="EMERGENCY BRAKE", command=self.toggle_emergency_brake).pack(fill="x", padx=6, pady=6)

    def toggle_emergency_brake(self):
        state = self.get_train_state()
        current = state.get("emergency_brake", False)
        self.update_train_state({"emergency_brake": not current})

    def create_failure_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Failures")
        frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.engine_failure_var = tk.BooleanVar(value=False)
        self.signal_failure_var = tk.BooleanVar(value=False)
        self.brake_failure_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Train Engine Failure", variable=self.engine_failure_var,
                        command=self.update_failures).pack(anchor="w", padx=10, pady=2)
        ttk.Checkbutton(frame, text="Signal Pickup Failure", variable=self.signal_failure_var,
                        command=self.update_failures).pack(anchor="w", padx=10, pady=2)
        ttk.Checkbutton(frame, text="Brake Failure", variable=self.brake_failure_var,
                        command=self.update_failures).pack(anchor="w", padx=10, pady=2)

    def update_failures(self):
        self.update_train_state({
            "engine_failure": self.engine_failure_var.get(),
            "signal_failure": self.signal_failure_var.get(),
            "brake_failure": self.brake_failure_var.get(),
        })

    def create_announcements_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Announcements")
        frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.announcement_box = tk.Text(frame, height=5, wrap="word", state='normal', font=("Consolas", 10))
        self.announcement_box.insert("end", "Train Model Running (Integrated Mode)...\n")
        self.announcement_box.pack(fill="both", expand=True, padx=5, pady=5)

    # === Simulation & Updates ===
    def compute_passengers_disembarking(self, station, velocity_mph, passengers_onboard):
        station = (station or "").strip()
        if not station or velocity_mph >= 0.5:
            return 0
        if self._last_disembark_station != station:
            crew = self.model.crew_count
            non_crew = max(0, passengers_onboard - crew)
            max_out = min(30, int(non_crew * 0.4))
            count = random.randint(0, max_out) if max_out > 0 else 0
            self._last_disembark_station = station
            self._last_disembarking = count
            return count
        return self._last_disembarking

    def write_ctc_output(self, passengers_disembarking):
        payload = {"passengers_disembarking": int(passengers_disembarking)}
        out_dir = os.path.dirname(os.path.abspath(CTC_OUTPUT_FILE))
        os.makedirs(out_dir, exist_ok=True)
        tmp = CTC_OUTPUT_FILE + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(payload, f, indent=4)
            os.replace(tmp, CTC_OUTPUT_FILE)
        except Exception:
            with open(CTC_OUTPUT_FILE, "w") as f:
                json.dump(payload, f, indent=4)

    def update_loop(self):
        state = self.get_train_state()
        outputs = self.model.update(
            commanded_speed=state.get("commanded_speed", 0),
            commanded_authority=state.get("commanded_authority", 0),
            speed_limit=state.get("speed_limit", 30),
            current_station=state.get("next_stop", "Unknown"),
            next_station=state.get("next_stop", "Unknown"),
            side_door=state.get("station_side", "Right"),
            power_command=state.get("power_command", 0),
            emergency_brake=state.get("emergency_brake", False),
            service_brake=state.get("service_brake", False),
            set_temperature=state.get("set_temperature", 70.0),
            left_door=state.get("left_door", False),
            right_door=state.get("right_door", False)
        )

        passengers_onboard = int(state.get("passengers_onboard", 0))
        disembarking = self.compute_passengers_disembarking(
            outputs["station_name"], outputs["velocity_mph"], passengers_onboard
        )
        self.write_ctc_output(disembarking)
        self.update_train_state({
            "train_velocity": outputs['velocity_mph'],
            "train_temperature": outputs['temperature_F'],
            "passengers_disembarking": disembarking
        })

        # UI update (clean version)
        self.info_labels["Velocity (mph)"].config(text=f"{outputs['velocity_mph']:.2f}")
        self.info_labels["Acceleration (ft/s²)"].config(text=f"{outputs['acceleration_ftps2']:.2f}")
        self.info_labels["Position (yds)"].config(text=f"{outputs['position_yds']:.1f}")
        self.info_labels["Authority Remaining (yds)"].config(text=f"{outputs['authority_yds']:.1f}")
        self.info_labels["Train Temperature (°F)"].config(text=f"{outputs['temperature_F']:.1f}")
        self.info_labels["Set Temperature (°F)"].config(text=f"{state.get('set_temperature', 70.0):.1f}")
        self.info_labels["Current Station"].config(text=f"{outputs['station_name']}")
        self.info_labels["Next Station"].config(text=f"{outputs['next_station']}")
        self.info_labels["Speed Limit (mph)"].config(text=f"{outputs['speed_limit']}")

        # FIXED: door/light status strings
        self.env_labels["Left Door"].config(
            text="Open" if outputs['left_door_open'] else "Closed",
            style="Status.On.TLabel" if outputs['left_door_open'] else "Status.Off.TLabel"
        )
        self.env_labels["Right Door"].config(
            text="Open" if outputs['right_door_open'] else "Closed",
            style="Status.On.TLabel" if outputs['right_door_open'] else "Status.Off.TLabel"
        )
        self.env_labels["Interior Lights"].config(
            text="On" if state.get("interior_lights") else "Off",
            style="Status.On.TLabel" if state.get("interior_lights") else "Status.Off.TLabel"
        )
        self.env_labels["Exterior Lights"].config(
            text="On" if state.get("exterior_lights") else "Off",
            style="Status.On.TLabel" if state.get("exterior_lights") else "Status.Off.TLabel"
        )

        # Optional: compact announcement refresh
        self.announcement_box.config(state='normal')
        self.announcement_box.delete("1.0", "end")
        self.announcement_box.insert("end", f"Running\nDisembark: {disembarking}")
        self.announcement_box.config(state='disabled')

        self.after(int(self.model.dt * 1000), self.update_loop)


if __name__ == "__main__":
    train_id = None
    if len(os.sys.argv) > 1:
        try:
            train_id = int(os.sys.argv[1])
        except ValueError:
            pass
    app = TrainModelUI(train_id)
    app.mainloop()

