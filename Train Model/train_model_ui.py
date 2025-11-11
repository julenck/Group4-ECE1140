import os
import json
import random
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

# === File paths ===
TRAIN_STATES_FILE = "../train_controller/data/train_states.json"
TRACK_INPUT_FILE = "../Track_Model/track_model_to_Train_Model.json"
TRACK_OUTPUT_FILE = "../Track_Model/train_model_to_track_model.json"
TRAIN_DATA_FILE = "train_data.json"

# Ensure relative paths resolve from this folder
os.chdir(os.path.dirname(os.path.abspath(__file__)))

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
        # Paths/specs before tk init
        self.train_states_path = TRAIN_STATES_FILE
        self.train_data_path = TRAIN_DATA_FILE
        self.track_input_path = TRACK_INPUT_FILE
        self.track_output_path = TRACK_OUTPUT_FILE
        self.specs = self._load_or_default_specs()

        super().__init__()
        self.title("Train Model")
        self.geometry("900x650")

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

        # UI
        self.info_labels = {}
        self.env_labels = {}
        self.build_basic_ui()
        self.build_failure_controls()
        self.build_passenger_ui()

        # Start loop
        self.update_loop()

    def _load_or_default_specs(self):
        """Return specs from train_data.json or defaults; ensure file contains 'specs'."""
        if os.path.exists(self.train_data_path):
            try:
                with open(self.train_data_path, "r") as f:
                    data = json.load(f)
                specs = data.get("specs", {})
                # Fill missing keys
                for k, v in DEFAULT_SPECS.items():
                    specs.setdefault(k, v)
                data["specs"] = specs
                # Ensure structure exists
                data.setdefault("inputs", {})
                data.setdefault("outputs", {})
                with open(self.train_data_path, "w") as f:
                    json.dump(data, f, indent=4)
                return specs
            except Exception:
                pass
        # Create fresh file
        data = {"specs": DEFAULT_SPECS, "inputs": {}, "outputs": {}}
        try:
            with open(self.train_data_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("Spec file init error:", e)
        return DEFAULT_SPECS

    def build_basic_ui(self):
        frame = ttk.LabelFrame(self, text="Train Info")
        frame.pack(fill="x", padx=10, pady=10)
        for k in ["Velocity (mph)", "Acceleration (ft/s²)", "Position (yds)",
                  "Authority Remaining (yds)", "Train Temperature (°F)",
                  "Set Temperature (°F)", "Current Station", "Next Station",
                  "Speed Limit (mph)"]:
            lbl = ttk.Label(frame, text=f"{k}:")
            lbl.pack(anchor="w")
            self.info_labels[k] = lbl

        env = ttk.LabelFrame(self, text="Environment")
        env.pack(fill="x", padx=10, pady=10)
        for k in ["Left Door", "Right Door"]:
            lbl = ttk.Label(env, text=f"{k}:")
            lbl.pack(anchor="w")
            self.env_labels[k] = lbl

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

    def build_passenger_ui(self):
        frm = ttk.LabelFrame(self, text="Passengers")
        frm.pack(fill="x", padx=10, pady=5)
        self.lbl_onboard = ttk.Label(frm, text=f"Onboard: {self.passengers_onboard}")
        self.lbl_onboard.pack(anchor="w")
        self.lbl_boarding = ttk.Label(frm, text="Boarding: 0")
        self.lbl_boarding.pack(anchor="w")
        self.lbl_disembark = ttk.Label(frm, text="Disembarking: 0")
        self.lbl_disembark.pack(anchor="w")
        self.lbl_capacity = ttk.Label(
            frm,
            text=f"Capacity: {self.specs.get('capacity', 0)} (Crew {self.specs.get('crew_count',0)})"
        )
        self.lbl_capacity.pack(anchor="w")

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
        """Load track inputs; if signal failure, freeze beacon values."""
        try:
            with open(self.track_input_path, "r") as f:
                data = json.load(f)
        except Exception:
            return {}
        block = data.get("block", {})
        beacon = data.get("beacon", {})
        if self.signal_failure:
            if self._last_beacon:
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
            "passengers_boarding": beacon.get("passengers_boarding", 0)
        }

    def compute_passengers_disembarking(self, current_station, velocity_mph):
        if not current_station:
            return 0
        stopped = velocity_mph < 0.5
        if stopped and current_station != self.last_disembark_station:
            # Up to 40% of non-crew, cap 30 each stop
            non_crew = max(0, self.passengers_onboard - self.specs.get("crew_count", 0))
            max_out = min(30, int(non_crew * 0.4))
            count = random.randint(0, max_out) if max_out > 0 else 0
            self.last_disembark_station = current_station
            self.last_passengers_disembarking = count
            return count
        if stopped:
            return self.last_passengers_disembarking
        return 0

    def write_track_output(self, passengers_disembarking):
        out = {"passengers_disembarking": passengers_disembarking}
        try:
            with open(self.track_output_path, "w") as f:
                json.dump(out, f, indent=4)
        except Exception as e:
            print("track output write error:", e)

    def overwrite_train_data(self, inputs, outputs):
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
            "passengers_onboard": self.passengers_onboard,
            "passengers_boarding": self.boarding_last_cycle,
            "passengers_disembarking": self.last_passengers_disembarking
        }
        data = {"specs": self.specs, "inputs": inputs_full, "outputs": outputs_extended}
        try:
            with open(self.train_data_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("train_data write error:", e)

    # === Main loop ===
    def update_loop(self):
        track_inputs = self.load_track_inputs()
        state = self.get_train_state()

        # Inputs
        commanded_speed = track_inputs.get("commanded speed", state.get("commanded_speed", 0.0))
        commanded_authority = track_inputs.get("commanded authority", state.get("commanded_authority", 0.0))
        speed_limit = track_inputs.get("speed limit", state.get("speed_limit", commanded_speed))
        current_station = track_inputs.get("current station", "")
        next_station = track_inputs.get("next station", "")
        side_door = track_inputs.get("side_door", "Right")
        passengers_boarding = track_inputs.get("passengers_boarding", 0)

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

        # Passenger logic
        passengers_out = self.compute_passengers_disembarking(current_station, outputs_sim["velocity_mph"])
        stopped = outputs_sim["velocity_mph"] < 0.5
        at_station = bool(current_station)

        if stopped and at_station:
            # Apply disembark first
            self.passengers_onboard = max(
                self.specs.get("crew_count", 0),
                self.passengers_onboard - passengers_out
            )
            # Then boarding up to available capacity
            available = max(0, self.specs.get("capacity", 0) - self.passengers_onboard)
            actual_boarding = min(available, max(0, passengers_boarding))
            self.passengers_onboard += actual_boarding
            self.boarding_last_cycle = actual_boarding
        else:
            self.boarding_last_cycle = 0

        # Outputs for train_data.json
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
        self.last_passengers_disembarking = passengers_out

        # Write JSONs
        self.overwrite_train_data(track_inputs, train_model_outputs)
        self.write_track_output(passengers_out)
        # Push some fields to controller state for visibility
        self.update_train_state({
            "train_velocity": outputs_sim["velocity_mph"],
            "train_temperature": self.model.temperature_F,
            "next_stop": next_station,
            "station_side": side_door
        })

        # UI updates
        self.info_labels["Velocity (mph)"].config(text=f"Velocity (mph): {outputs_sim['velocity_mph']:.2f}")
        self.info_labels["Acceleration (ft/s²)"].config(text=f"Acceleration (ft/s²): {outputs_sim['acceleration_ftps2']:.2f}")
        self.info_labels["Position (yds)"].config(text=f"Position (yds): {outputs_sim['position_yds']:.1f}")
        self.info_labels["Authority Remaining (yds)"].config(text=f"Authority Remaining (yds): {outputs_sim['authority_yds']:.1f}")
        self.info_labels["Train Temperature (°F)"].config(text=f"Train Temperature (°F): {self.model.temperature_F:.1f}")
        self.info_labels["Set Temperature (°F)"].config(text=f"Set Temperature (°F): {state.get('set_temperature', 70.0):.1f}")
        self.info_labels["Current Station"].config(text=f"Current Station: {current_station or '---'}")
        self.info_labels["Next Station"].config(text=f"Next Station: {next_station or '---'}")
        self.info_labels["Speed Limit (mph)"].config(text=f"Speed Limit (mph): {speed_limit}")
        self.env_labels["Left Door"].config(text=f"Left Door: {'Open' if outputs_sim['left_door_open'] else 'Closed'}")
        self.env_labels["Right Door"].config(text=f"Right Door: {'Open' if outputs_sim['right_door_open'] else 'Closed'}")
        self.lbl_onboard.config(text=f"Onboard: {self.passengers_onboard}")
        self.lbl_boarding.config(text=f"Boarding: {self.boarding_last_cycle}")
        self.lbl_disembark.config(text=f"Disembarking: {passengers_out}")

        self.after(max(1, int(self.model.dt * 1000)), self.update_loop)

if __name__ == "__main__":
    app = TrainModelUI()
    app.mainloop()

