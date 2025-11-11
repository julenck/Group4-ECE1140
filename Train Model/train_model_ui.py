import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import json
import os
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
               left_door=False, right_door=False):
        """Simulate motion and update station/door status"""
        # Apply brakes first
        if emergency_brake:
            self.acceleration_ftps2 = self.emergency_brake_ftps2
        elif service_brake:
            self.acceleration_ftps2 = self.service_brake_ftps2
        else:
            # Use power command to calculate acceleration
            # Power command comes in Watts from train controller
            power_watts = power_command  # Already in watts, no conversion needed
            if self.velocity_mph > 0.1:  # Avoid division by zero
                velocity_ftps = self.velocity_mph * 1.46667  # mph to ft/s
                velocity_mps = velocity_ftps * 0.3048  # ft/s to m/s
                force_newtons = power_watts / velocity_mps  # F = P/v
                force_lbs = force_newtons * 0.224809  # N to lbs
                self.acceleration_ftps2 = (force_lbs / self.mass_lbs) * 32.174  # a = F/m
            else:
                # At rest, use max acceleration if power is applied
                self.acceleration_ftps2 = self.max_accel_ftps2 if power_command > 0 else 0
            
            # Limit acceleration to max
            self.acceleration_ftps2 = max(min(self.acceleration_ftps2, self.max_accel_ftps2), 
                                         self.service_brake_ftps2)

        # Integrate velocity and position
        delta_v_ftps = self.acceleration_ftps2 * self.dt
        delta_v_mph = delta_v_ftps * 0.681818
        self.velocity_mph = max(self.velocity_mph + delta_v_mph, 0)
        delta_x_ft = (self.velocity_mph / 0.681818) * self.dt
        self.position_yds += delta_x_ft / 3.0
        self.authority_yds = commanded_authority

        # Door logic - use actual door states from train controller
        self.left_door_open = left_door
        self.right_door_open = right_door

        # Regulate temperature toward set point
        self.regulate_temperature(set_temperature)

        # Update route info
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

    def compute_passengers_disembarking(self, station: str, velocity_mph: float, passengers_onboard: int) -> int:
        """
        Compute disembarking count only once when first stopped at a station.
        Does not modify passengers_onboard (CTC updates onboard after receiving this).
        """
        station = (station or "").strip()
        if not station or velocity_mph >= 0.5:
            return 0
        if self._last_disembark_station != station:
            crew = self.model.crew_count
            non_crew = max(0, passengers_onboard - crew)
            max_out = min(30, int(non_crew * 0.4))
            if max_out > 0:
                # lightweight randomness (0–max_out)
                count = int(os.urandom(1)[0] / 255 * max_out)
            else:
                count = 0
            self._last_disembark_station = station
            self._last_disembarking = count
            return count
        return self._last_disembarking

    def write_ctc_output(self, passengers_disembarking: int):
        """Send passengers_disembarking to CTC JSON file (no timestamp)."""
        out_dir = os.path.dirname(os.path.abspath(CTC_OUTPUT_FILE))
        if out_dir and not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception:
                pass
        payload = {"passengers_disembarking": int(passengers_disembarking)}
        tmp = CTC_OUTPUT_FILE + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(payload, f, indent=4)
            os.replace(tmp, CTC_OUTPUT_FILE)
        except PermissionError:
            try:
                with open(CTC_OUTPUT_FILE, "w") as f:
                    json.dump(payload, f, indent=4)
            except Exception as e:
                print("CTC write error:", e)
        except Exception as e:
            print("CTC write error:", e)

# === Train Model UI ===
class TrainModelUI(tk.Tk):
    def __init__(self, train_id=None):
        super().__init__()
        self.train_id = train_id  # None means root level (legacy), otherwise use train_X
        title = f"Train {train_id} - Train Model" if train_id else "Train Model - Integrated with Train Controller"
        self.title(title)
        self.geometry("1450x900")

        self.train_states_path = TRAIN_STATES_FILE
        self.specs_path = TRAIN_SPECS_FILE
        
        # Load static specs
        specs = self.load_train_specs()
        self.model = TrainModel(specs)
        
        # Initialize train temperature from JSON file
        state = self.get_train_state()
        self.model.temperature_F = state.get("train_temperature", 68.0)

        # Layout configuration
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Left panel
        left_frame = ttk.Frame(self)
        left_frame.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)
        self.create_info_panel(left_frame)
        self.create_env_panel(left_frame)
        self.create_specs_panel(left_frame)
        self.create_control_panel(left_frame)
        self.create_failure_panel(left_frame)   # <-- NEW PANEL ADDED HERE
        self.create_announcements_panel(left_frame)

        # Right panel (map)
        right_frame = ttk.Frame(self)
        right_frame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)
        self.create_static_map_panel(right_frame)

        # Start update loop
        self.update_loop()

    def load_train_specs(self):
        """Load static train specifications from train_data.json"""
        if not os.path.exists(self.specs_path):
            default_specs = {
                "specs": {
                    "length_ft": 66.0,
                    "width_ft": 10.0,
                    "height_ft": 11.5,
                    "mass_lbs": 90100,
                    "max_power_hp": 161,
                    "max_accel_ftps2": 1.64,
                    "service_brake_ftps2": -3.94,
                    "emergency_brake_ftps2": -8.86,
                    "capacity": 222,
                    "crew_count": 2
                }
            }
            with open(self.specs_path, "w") as f:
                json.dump(default_specs, f, indent=4)
            return default_specs["specs"]
        
        with open(self.specs_path, "r") as f:
            data = json.load(f)
            return data.get("specs", {})

    def get_train_state(self):
        """Read train state from train_states.json"""
        try:
            with open(self.train_states_path, "r") as f:
                all_states = json.load(f)
                
                # If train_id is specified, read from train_X section
                if self.train_id is not None:
                    train_key = f"train_{self.train_id}"
                    if train_key in all_states:
                        return all_states[train_key]
                    else:
                        # Initialize this train's section if it doesn't exist
                        return self._get_default_state()
                else:
                    # Legacy mode: read from root level
                    return all_states
        except FileNotFoundError:
            # Initialize with default state if file doesn't exist
            default_state = self._get_default_state()
            with open(self.train_states_path, "w") as f:
                json.dump(default_state, f, indent=4)
            return default_state
    
    def _get_default_state(self):
        """Get default train state"""
        return {
            "train_id": self.train_id if self.train_id else 0,
            "commanded_speed": 0.0,
            "commanded_authority": 0.0,
            "speed_limit": 0.0,
            "train_velocity": 0.0,
            "next_stop": "",
            "station_side": "",
            "train_temperature": 70.0,
            "engine_failure": False,
            "signal_failure": False,
            "brake_failure": False,
            "manual_mode": False,
            "driver_velocity": 0.0,
            "service_brake": False,
            "right_door": False,
            "left_door": False,
            "interior_lights": False,
            "exterior_lights": False,
            "set_temperature": 70.0,
            "temperature_up": False,
            "temperature_down": False,
            "announcement": "",
            "announce_pressed": False,
            "emergency_brake": False,
            "kp": 0.0,
            "ki": 0.0,
            "engineering_panel_locked": False,
            "power_command": 0.0,
            "passengers_onboard": 0,              # NEW
            "passengers_boarding": 0,             # NEW (from CTC or external source)
            "passengers_disembarking": 0          # NEW (computed here, sent to CTC)
        }

    def update_train_state(self, updates):
        """Write train outputs back to train_states.json"""
        with open(self.train_states_path, "r") as f:
            all_states = json.load(f)
        
        if self.train_id is not None:
            # Update specific train's section at ROOT level only
            train_key = f"train_{self.train_id}"
            if train_key not in all_states:
                all_states[train_key] = self._get_default_state()
            
            # Get current state and update with new values
            current_train_state = all_states[train_key]
            
            # Only update with actual data, skip nested train_X keys
            for key, value in updates.items():
                if not (key.startswith('train_') and isinstance(value, dict)):
                    current_train_state[key] = value
            
            all_states[train_key] = current_train_state
        else:
            # Legacy mode: update root level
            all_states.update(updates)
        
        with open(self.train_states_path, "w") as f:
            json.dump(all_states, f, indent=4)

    def create_info_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Train Dynamics (Imperial Units)")
        frame.pack(fill="x", pady=5)
        self.info_labels = {}
        for key in [
            "Velocity (mph)",
            "Acceleration (ft/s²)",
            "Position (yds)",
            "Authority Remaining (yds)",
            "Train Temperature (°F)",
            "Set Temperature (°F)",
            "Current Station",
            "Next Station",
            "Speed Limit (mph)"
        ]:
            lbl = ttk.Label(frame, text=f"{key}: --")
            lbl.pack(anchor="w", padx=10, pady=2)
            self.info_labels[key] = lbl

    def create_env_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Environment Status")
        frame.pack(fill="x", pady=5)
        self.env_labels = {}
        for key in ["Left Door", "Right Door"]:
            lbl = ttk.Label(frame, text=f"{key}: --")
            lbl.pack(anchor="w", padx=10, pady=2)
            self.env_labels[key] = lbl

    def create_specs_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Train Specifications")
        frame.pack(fill="x", pady=5)
        specs = self.load_train_specs()
        for k, v in specs.items():
            ttk.Label(frame, text=f"{k}: {v}").pack(anchor="w", padx=10, pady=1)

    def create_control_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Controls")
        frame.pack(fill="x", pady=10)
        self.emergency_button = ttk.Button(frame, text="EMERGENCY BRAKE", 
                                           command=self.toggle_emergency_brake)
        self.emergency_button.pack(fill="x", padx=20, pady=10)
    
    def toggle_emergency_brake(self):
        """Toggle emergency brake state"""
        state = self.get_train_state()
        current_state = state.get("emergency_brake", False)
        self.update_train_state({"emergency_brake": not current_state})

    def create_failure_panel(self, parent):
        """Panel for setting failure modes."""
        frame = ttk.LabelFrame(parent, text="Failure Modes")
        frame.pack(fill="x", pady=5)

        # Boolean variables for each failure mode
        self.engine_failure_var = tk.BooleanVar(value=False)
        self.signal_failure_var = tk.BooleanVar(value=False)
        self.brake_failure_var = tk.BooleanVar(value=False)

        # Checkbuttons for each failure mode
        ttk.Checkbutton(frame, text="Train Engine Failure",
                        variable=self.engine_failure_var,
                        command=self.update_failures).pack(anchor="w", padx=10, pady=2)
        ttk.Checkbutton(frame, text="Signal Pickup Failure",
                        variable=self.signal_failure_var,
                        command=self.update_failures).pack(anchor="w", padx=10, pady=2)
        ttk.Checkbutton(frame, text="Brake Failure",
                        variable=self.brake_failure_var,
                        command=self.update_failures).pack(anchor="w", padx=10, pady=2)

    def update_failures(self):
        """Write failure mode states directly to train_states.json"""
        self.update_train_state({
            "engine_failure": self.engine_failure_var.get(),
            "signal_failure": self.signal_failure_var.get(),
            "brake_failure": self.brake_failure_var.get(),
        })

    def create_announcements_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Announcements")
        frame.pack(fill="both", expand=True, pady=5)
        self.announcement_box = tk.Text(frame, height=6, wrap="word", state='normal')
        self.announcement_box.insert("end", "Train Model Running (Integrated Mode)...\n")
        self.announcement_box.pack(fill="both", expand=True, padx=5, pady=5)

    def create_static_map_panel(self, parent):
        map_path = os.path.join(os.path.dirname(__file__), "map.png")
        if os.path.exists(map_path):
            img = Image.open(map_path).resize((850, 650))
            self.map_img = ImageTk.PhotoImage(img)
            lbl = ttk.Label(parent, image=self.map_img)
            lbl.pack(fill="both", expand=True)
        else:
            ttk.Label(parent, text="Map not found").pack()

    def update_loop(self):
        """Periodic update: read state, simulate, write outputs."""
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

        # UI updates
        self.info_labels["Velocity (mph)"].config(text=f"Velocity: {outputs['velocity_mph']:.2f} mph")
        self.info_labels["Acceleration (ft/s²)"].config(text=f"Acceleration: {outputs['acceleration_ftps2']:.2f} ft/s²")
        self.info_labels["Position (yds)"].config(text=f"Position: {outputs['position_yds']:.1f} yds")
        self.info_labels["Authority Remaining (yds)"].config(text=f"Authority: {outputs['authority_yds']:.1f} yds")
        self.info_labels["Train Temperature (°F)"].config(text=f"Train Temperature: {outputs['temperature_F']:.1f}°F")
        self.info_labels["Set Temperature (°F)"].config(text=f"Set Temperature: {state.get('set_temperature', 70.0):.1f}°F")
        self.info_labels["Current Station"].config(text=f"Current Station: {outputs['station_name']}")
        self.info_labels["Next Station"].config(text=f"Next Station: {outputs['next_station']}")
        self.info_labels["Speed Limit (mph)"].config(text=f"Speed Limit: {outputs['speed_limit']} mph")
        self.env_labels["Left Door"].config(text=f"Left Door: {'Open' if outputs['left_door_open'] else 'Closed'}")
        self.env_labels["Right Door"].config(text=f"Right Door: {'Open' if outputs['right_door_open'] else 'Closed'}")

        self.announcement_box.config(state='normal')
        self.announcement_box.delete("1.0", "end")
        self.announcement_box.insert("end", f"Train Model Running...\nDisembarking this stop: {disembarking}")
        self.announcement_box.config(state='disabled')

        self.after(int(self.model.dt * 1000), self.update_loop)

if __name__ == "__main__":
    app = TrainModelUI()
    app.mainloop()
