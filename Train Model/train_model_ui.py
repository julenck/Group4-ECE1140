import os
import json
import random
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


# === File paths ===
TRAIN_STATES_FILE = "../train_controller/data/train_states.json"
TRACK_INPUT_FILE = "../Track_Model/track_model_to_Train_Model.json"
TRAIN_DATA_FILE = "train_data.json"

os.chdir(os.path.dirname(os.path.abspath(__file__)))  # ensures relative paths work


# === Train Model Core ===
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
        """Regulate train temperature toward set temperature.
        
        Simulates realistic HVAC system with gradual temperature changes.
        Temperature changes at about 3°F per minute (realistic for train HVAC).
        
        Args:
            set_temperature: Target temperature in °F
        """
        temp_error = set_temperature - self.temperature_F
        
        # Realistic HVAC rate: ~3°F per minute = 0.025°F per 0.5s update
        # This means it takes about 1 minute to change 3°F
        max_rate = 0.025  # °F per update cycle (realistic but noticeable)
        
        # Use proportional control for realistic approach
        # When far away: change at max rate
        # When close: change slower to avoid overshoot
        if abs(temp_error) > 0.25:  # Dead band to prevent oscillation
            # Proportional control with 0.2 gain for gradual changes
            temp_change = temp_error * 0.2
            # Limit to realistic HVAC heating/cooling rate
            temp_change = max(-max_rate, min(max_rate, temp_change))
            
            # Apply temperature change WITHOUT rounding yet
            self.temperature_F += temp_change
        
        # Always round to nearest 0.5 degrees for realistic display
        # (but only for display, maintain precision internally)
        return round(self.temperature_F * 2) / 2
    
    def update(self, commanded_speed, commanded_authority, speed_limit,
               current_station, next_station, side_door, power_command=0,
               emergency_brake=False, service_brake=False, set_temperature=70.0,
               left_door=False, right_door=False,
               engine_failure=False, brake_failure=False):
        # Emergency brake overrides everything
        if emergency_brake:
            self.acceleration_ftps2 = self.emergency_brake_ftps2
        else:
            if service_brake and not brake_failure:
                self.acceleration_ftps2 = self.service_brake_ftps2
            else:
                target_mph = min(commanded_speed, speed_limit if speed_limit > 0 else commanded_speed)
                target_ftps = target_mph / 0.681818
                current_ftps = self.velocity_mph / 0.681818
                diff = target_ftps - current_ftps
                accel_max = self.max_accel_ftps2
                raw_accel = max(-accel_max, min(accel_max, diff / self.dt))
                # Engine failure: no positive propulsion (allow coasting & braking)
                if engine_failure and raw_accel > 0:
                    raw_accel = 0.0
                self.acceleration_ftps2 = raw_accel
        delta_v_ftps = self.acceleration_ftps2 * self.dt
        delta_v_mph = delta_v_ftps * 0.681818
        self.velocity_mph = max(self.velocity_mph + delta_v_mph, 0.0)
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

# === Train Model UI ===
class TrainModelUI(tk.Tk):
    def __init__(self):
        # Prepare paths and specs BEFORE tk init to avoid early callbacks needing specs
        self.train_states_path = TRAIN_STATES_FILE
        self.train_data_path = TRAIN_DATA_FILE
        self.track_input_path = TRACK_INPUT_FILE
        self.specs = self._load_or_default_specs()
        super().__init__()
        self.title("Train Model")
        self.geometry("800x600")
        self.model = TrainModel(self.specs)
        
        # Initialize train temperature from JSON file
        state = self.get_train_state()
        self.model.temperature_F = state.get("train_temperature", self.specs.get("default_temperature", 68.0))

        # UI elements
        self.last_disembark_station = None
        self.last_passengers_disembarking = 0
        self.info_labels = {}
        self.env_labels = {}
        
        self.build_basic_ui()
        self.build_failure_controls()
        # Start update loop
        self.update_loop()

    def _load_or_default_specs(self):
        """Return specs from train_data.json or defaults, then ensure train_data.json has them."""
        if os.path.exists(self.train_data_path):
            try:
                with open(self.train_data_path, "r") as f:
                    data = json.load(f)
                specs = data.get("specs", {})
                # Validate required keys
                missing = [k for k in DEFAULT_SPECS if k not in specs]
                if missing:
                    for k in missing:
                        specs[k] = DEFAULT_SPECS[k]
                    data["specs"] = specs
                    with open(self.train_data_path, "w") as f:
                        json.dump(data, f, indent=4)
                return specs
            except Exception:
                pass
        # Write fresh file if absent/corrupt
        base = {
            "specs": DEFAULT_SPECS,
            "inputs": {},
            "outputs": {}
        }
        try:
            with open(self.train_data_path, "w") as f:
                json.dump(base, f, indent=4)
        except Exception as e:
            print("Spec file init error:", e)
        return DEFAULT_SPECS

    def build_basic_ui(self):
        frame = ttk.LabelFrame(self, text="Info")
        frame.pack(fill="x", padx=10, pady=10)
        for k in ["Velocity (mph)", "Acceleration (ft/s²)", "Position (yds)",
                  "Authority Remaining (yds)", "Train Temperature (°F)",
                  "Set Temperature (°F)", "Current Station", "Next Station",
                  "Speed Limit (mph)", "Passengers Disembarking"]:
            lbl = ttk.Label(frame, text=f"{k}:")
            lbl.pack(anchor="w")
            self.info_labels[k] = lbl
        env = ttk.LabelFrame(self, text="Environment")
        env.pack(fill="x", padx=10, pady=10)
        for k in ["Left Door", "Right Door"]:
            lbl = ttk.Label(env, text=f"{k}:")
            lbl.pack(anchor="w")
            self.env_labels[k] = lbl

    def load_train_specs(self):
        if not os.path.exists(self.train_data_path):
            return {}
        with open(self.train_data_path, "r") as f:
            data = json.load(f)
        return data.get("specs", {})

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
        try:
            with open(self.track_input_path, "r") as f:
                data = json.load(f)
        except Exception:
            return {}
        block = data.get("block", {})
        beacon = data.get("beacon", {})
        return {
            "commanded speed": block.get("commanded speed", 0.0),
            "commanded authority": block.get("commanded authority", 0.0),
            "speed limit": beacon.get("speed limit", 0.0),
            "side_door": beacon.get("side_door", ""),
            "current station": beacon.get("current station", ""),
            "next station": beacon.get("next station", "")
        }

    def overwrite_train_data(self, inputs, outputs):
        state = self.get_train_state()
        # Failures & emergency brake included in inputs section
        inputs_full = {
            **inputs,
            "engine_failure": state.get("engine_failure", False),
            "signal_failure": state.get("signal_failure", False),
            "brake_failure": state.get("brake_failure", False),
            "emergency_brake": state.get("emergency_brake", False)
        }
        data = {"specs": self.specs, "inputs": inputs_full, "outputs": outputs}
        try:
            with open(self.train_data_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("train_data write error:", e)

    def compute_passengers_disembarking(self, current_station, velocity_mph):
        if not current_station:
            return 0
        stopped = velocity_mph < 0.5
        if stopped and current_station != self.last_disembark_station:
            max_out = min(30, int(self.model.capacity * 0.5))
            count = random.randint(0, max_out)
            self.last_disembark_station = current_station
            self.last_passengers_disembarking = count
            return count
        if stopped:
            return self.last_passengers_disembarking
        return 0

    def build_failure_controls(self):
        frm = ttk.LabelFrame(self, text="Failures / Safety")
        frm.pack(fill="x", padx=10, pady=5)
        self.var_engine = tk.BooleanVar(value=False)
        self.var_signal = tk.BooleanVar(value=False)
        self.var_brake = tk.BooleanVar(value=False)
        self.var_emergency = tk.BooleanVar(value=False)

        ttk.Checkbutton(frm, text="Engine Failure", variable=self.var_engine,
                        command=self._on_failure_toggle).pack(anchor="w")
        ttk.Checkbutton(frm, text="Signal Pickup Failure", variable=self.var_signal,
                        command=self._on_failure_toggle).pack(anchor="w")
        ttk.Checkbutton(frm, text="Brake Failure", variable=self.var_brake,
                        command=self._on_failure_toggle).pack(anchor="w")
        ttk.Checkbutton(frm, text="Emergency Brake", variable=self.var_emergency,
                        command=self._on_emergency_toggle).pack(anchor="w")

        self.fail_status_lbl = ttk.Label(frm, text="Status: OK")
        self.fail_status_lbl.pack(anchor="w")

    def _on_failure_toggle(self):
        self.engine_failure = self.var_engine.get()
        self.signal_failure = self.var_signal.get()
        self.brake_failure = self.var_brake.get()
        self._push_failures_to_state()
        status = []
        if self.engine_failure: status.append("Engine")
        if self.signal_failure: status.append("Signal")
        if self.brake_failure: status.append("Brake")
        self.fail_status_lbl.config(text=f"Status: {' / '.join(status) if status else 'OK'}")

    def _on_emergency_toggle(self):
        self.emergency_brake = self.var_emergency.get()
        self._push_failures_to_state()

    def _push_failures_to_state(self):
        self.update_train_state({
            "engine_failure": self.engine_failure,
            "signal_failure": self.signal_failure,
            "brake_failure": self.brake_failure,
            "emergency_brake": self.emergency_brake
        })

    def update_loop(self):
        track_inputs = self.load_track_inputs()
        state = self.get_train_state()

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
        passengers_out = self.compute_passengers_disembarking(current_station, outputs_sim["velocity_mph"])
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
            "passengers_disembarking": passengers_out,
            "door_side": side_door
        }
        self.overwrite_train_data(track_inputs, train_model_outputs)
        self.update_train_state({
            "train_velocity": outputs_sim["velocity_mph"],
            "train_temperature": self.model.temperature_F,
            "next_stop": next_station,
            "station_side": side_door
        })
        # UI labels
        self.info_labels["Velocity (mph)"].config(text=f"Velocity (mph): {outputs_sim['velocity_mph']:.2f}")
        self.info_labels["Acceleration (ft/s²)"].config(text=f"Acceleration (ft/s²): {outputs_sim['acceleration_ftps2']:.2f}")
        self.info_labels["Position (yds)"].config(text=f"Position (yds): {outputs_sim['position_yds']:.1f}")
        self.info_labels["Authority Remaining (yds)"].config(text=f"Authority Remaining (yds): {outputs_sim['authority_yds']:.1f}")
        self.info_labels["Train Temperature (°F)"].config(text=f"Train Temperature (°F): {self.model.temperature_F:.1f}")
        self.info_labels["Set Temperature (°F)"].config(text=f"Set Temperature (°F): {state.get('set_temperature', 70.0):.1f}")
        self.info_labels["Current Station"].config(text=f"Current Station: {current_station or '---'}")
        self.info_labels["Next Station"].config(text=f"Next Station: {next_station or '---'}")
        self.info_labels["Speed Limit (mph)"].config(text=f"Speed Limit (mph): {speed_limit}")
        self.info_labels["Passengers Disembarking"].config(text=f"Passengers Disembarking: {passengers_out}")

        self.env_labels["Left Door"].config(text=f"Left Door: {'Open' if outputs_sim['left_door_open'] else 'Closed'}")
        self.env_labels["Right Door"].config(text=f"Right Door: {'Open' if outputs_sim['right_door_open'] else 'Closed'}")

        # Add failure/emergency display
        self.fail_status_lbl.config(
            text=f"Status: {'EMERGENCY BRAKE' if state.get('emergency_brake') else 'OK'} | "
                 f"Eng:{int(state.get('engine_failure',0))} Sig:{int(state.get('signal_failure',0))} Brk:{int(state.get('brake_failure',0))}"
        )
        self.after(int(self.model.dt * 1000), self.update_loop)


if __name__ == "__main__":
    app = TrainModelUI()
    app.mainloop()

