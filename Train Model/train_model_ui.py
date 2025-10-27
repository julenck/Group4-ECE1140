import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import json
import os
import math

# Ensure working directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
JSON_FILE = "train_data.json"


# === TRAIN MODEL CORE (Imperial Units) ===
class TrainModel:
    def __init__(self, specs):
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
        self.authority_yds = 328.0  # default ~300m

        # Passenger system
        self.passengers_boarding = 0
        self.passengers_disembarking = 0
        self.passengers_onboard = 0

        # Door / Light system
        self.left_door_open = False
        self.right_door_open = False
        self.lights_on = False

        # Failures
        self.engine_failure = False
        self.brake_failure = False
        self.signal_failure = False
        self.emergency_brake = False

        # Route data
        self.current_station = "Downtown"
        self.next_station = "Midtown"
        self.station_positions_yds = {
            "Downtown": 0,
            "Midtown": 547,
            "Uptown": 1094
        }

        self.dt = 0.5  # seconds

    def update(self, power_hp, authority_yds, passengers_boarding):
        """Core update logic for train motion and environment (Imperial units)."""
        if self.engine_failure:
            traction_force = 0
        else:
            traction_force = power_hp * 550 / max(self.velocity_mph, 0.1)  # 1 hp = 550 ft·lbf/s

        resistance = 5000 + 30 * self.velocity_mph + 0.5 * self.velocity_mph**2

        if self.emergency_brake:
            brake_force = abs(self.emergency_brake_ftps2) * self.mass_lbs
        elif self.brake_failure:
            brake_force = 0
        else:
            brake_force = abs(self.service_brake_ftps2) * self.mass_lbs if self.velocity_mph > 0 else 0

        net_force = traction_force - resistance - brake_force
        self.acceleration_ftps2 = max(min(net_force / self.mass_lbs, self.max_accel_ftps2), self.emergency_brake_ftps2)

        # Kinematics (Imperial)
        delta_v_ftps = self.acceleration_ftps2 * self.dt
        delta_v_mph = delta_v_ftps * 0.681818  # 1 ft/s = 0.681818 mph
        self.velocity_mph = max(self.velocity_mph + delta_v_mph, 0)

        delta_x_ft = (self.velocity_mph / 0.681818) * self.dt + 0.5 * self.acceleration_ftps2 * self.dt**2
        delta_x_yds = delta_x_ft / 3.0
        self.position_yds += delta_x_yds
        self.authority_yds = max(authority_yds - delta_x_yds, 0)

        # Passenger updates
        self.passengers_disembarking = int(max(0, self.passengers_onboard * 0.05))
        self.passengers_onboard = max(
            0, min(self.capacity, self.passengers_onboard + passengers_boarding - self.passengers_disembarking)
        )

        self.update_stations()

        return {
            "velocity_mph": self.velocity_mph,
            "acceleration_ftps2": self.acceleration_ftps2,
            "position_yds": self.position_yds,
            "authority_yds": self.authority_yds,
            "current_station": self.current_station,
            "next_station": self.next_station,
            "eta_s": self.calculate_eta(),
            "passengers_boarding": passengers_boarding,
            "passengers_disembarking": self.passengers_disembarking,
            "passengers_onboard": self.passengers_onboard,
            "left_door_open": self.left_door_open,
            "right_door_open": self.right_door_open,
            "lights_on": self.lights_on,
            "temperature_F": self.temperature_F,
        }

    def update_stations(self):
        pos = self.position_yds
        if pos < self.station_positions_yds["Midtown"]:
            self.current_station = "Downtown"
            self.next_station = "Midtown"
        elif pos < self.station_positions_yds["Uptown"]:
            self.current_station = "Midtown"
            self.next_station = "Uptown"
        else:
            self.current_station = "Uptown"
            self.next_station = "End of Line"

    def calculate_eta(self):
        next_pos = self.station_positions_yds.get(self.next_station, None)
        if next_pos is None or self.velocity_mph <= 0:
            return None
        distance_yds = max(next_pos - self.position_yds, 0)
        velocity_yds_per_s = (self.velocity_mph * 1760) / 3600
        return distance_yds / max(velocity_yds_per_s, 0.1)


# === TRAIN MODEL MAIN UI (Imperial Units) ===
class TrainModelUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Train Model UI - Imperial Units")
        self.geometry("1450x900")

        self.json_path = JSON_FILE
        self.data = self.load_or_create_json()
        self.model = TrainModel(self.data["specs"])

        # Layout setup
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        self.left_frame = ttk.Frame(self)
        self.left_frame.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)

        self.right_frame = ttk.Frame(self)
        self.right_frame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)

        # Left panels
        self.create_info_panel(self.left_frame)
        self.create_env_panel(self.left_frame)
        self.create_specs_panel(self.left_frame)
        self.create_failure_panel(self.left_frame)
        self.create_control_panel(self.left_frame)
        self.create_announcements_panel(self.left_frame)

        # Right map
        self.create_static_map_panel(self.right_frame)

        self.update_loop()

    # ==== JSON Handling ====
    def load_or_create_json(self):
        if not os.path.exists(self.json_path):
            default_data = {
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
                    "crew_count": 2,
                },
                "inputs": {
                    "commanded_power_hp": 80.5,
                    "authority_yds": 328.0,
                    "beacon_data": "128B",
                    "commanded_speed_mph": 25.0,
                    "speed_limit_mph": 30.0,
                    "crew_count": 2,
                    "passengers_boarding": 80,
                    "emergency_brake": False,
                    "lights_on": True,
                    "left_door_open": False,
                    "right_door_open": False,
                    "temperature_F": 68,
                },
                "outputs": {},
            }
            with open(self.json_path, "w") as f:
                json.dump(default_data, f, indent=4)
            return default_data
        with open(self.json_path, "r") as f:
            return json.load(f)

    def write_json(self, outputs):
        """Write to main, controller, and track model JSONs."""
        self.data["outputs"] = outputs
        with open(self.json_path, "w") as f:
            json.dump(self.data, f, indent=4)

        # === Export to Train Controller ===
        controller_data = {
            "commanded_speed_mph": self.data["inputs"].get("commanded_speed_mph", 0),
            "commanded_authority_yds": self.data["inputs"].get("authority_yds", 0),
            "beacon_data": self.data["inputs"].get("beacon_data", ""),
            "failure_modes": {
                "engine_failure": self.model.engine_failure,
                "signal_pickup_failure": self.model.signal_failure,
                "brake_failure": self.model.brake_failure,
            },
            "train_velocity_mph": round(outputs.get("velocity_mph", 0), 2),
            "train_temperature_F": outputs.get("temperature_F", 68.0),
            "emergency_brake": self.model.emergency_brake,
        }
        with open("train_to_controller.json", "w") as f:
            json.dump(controller_data, f, indent=4)

        # === Export to Track Model ===
        track_data = {
            "number_of_passengers_disembarking": outputs.get("passengers_disembarking", 0)
        }
        with open("train_to_trackmodel.json", "w") as f:
            json.dump(track_data, f, indent=4)

    # ==== UI Panels ====
    def create_info_panel(self, parent):
        info = ttk.LabelFrame(parent, text="Train Information & Dynamics (Imperial Units)")
        info.pack(fill="x", pady=5)
        self.info_labels = {}
        for key in [
            "Velocity (mph)",
            "Acceleration (ft/s²)",
            "Position (yds)",
            "Authority Remaining (yds)",
            "Current Station",
            "ETA to Next Station",
            "Passengers Onboard",
        ]:
            lbl = ttk.Label(info, text=f"{key}: --")
            lbl.pack(anchor="w", padx=10, pady=2)
            self.info_labels[key] = lbl

    def create_env_panel(self, parent):
        env = ttk.LabelFrame(parent, text="Environmental Status (Read-only)")
        env.pack(fill="x", pady=5)
        self.env_labels = {}
        for key in ["Lights On", "Left Door", "Right Door", "Cabin Temperature (°F)"]:
            lbl = ttk.Label(env, text=f"{key}: --")
            lbl.pack(anchor="w", padx=10, pady=2)
            self.env_labels[key] = lbl

    def create_specs_panel(self, parent):
        specs = ttk.LabelFrame(parent, text="Train Specifications (Imperial Units)")
        specs.pack(fill="x", pady=5)
        for k, v in self.data["specs"].items():
            ttk.Label(specs, text=f"{k}: {v}").pack(anchor="w", padx=10, pady=1)

    def create_failure_panel(self, parent):
        fail = ttk.LabelFrame(parent, text="Failure Status")
        fail.pack(fill="x", pady=5)
        self.engine_fail = tk.BooleanVar()
        self.brake_fail = tk.BooleanVar()
        self.signal_fail = tk.BooleanVar()
        ttk.Checkbutton(fail, text="Engine Failure", variable=self.engine_fail).pack(anchor="w", padx=15, pady=2)
        ttk.Checkbutton(fail, text="Brake Failure", variable=self.brake_fail).pack(anchor="w", padx=15, pady=2)
        ttk.Checkbutton(fail, text="Signal Pickup Failure", variable=self.signal_fail).pack(anchor="w", padx=15, pady=2)

    def create_control_panel(self, parent):
        ctrl = ttk.LabelFrame(parent, text="Controls")
        ctrl.pack(fill="x", pady=10)
        self.emergency_button = ttk.Button(ctrl, text="EMERGENCY BRAKE", command=self.toggle_emergency)
        self.emergency_button.pack(fill="x", padx=20, pady=10)

    def toggle_emergency(self):
        self.model.emergency_brake = not self.model.emergency_brake
        if self.model.emergency_brake:
            self.emergency_button.config(text="EMERGENCY BRAKE ACTIVE", style="Danger.TButton")
        else:
            self.emergency_button.config(text="EMERGENCY BRAKE", style="TButton")

    def create_announcements_panel(self, parent):
        ann = ttk.LabelFrame(parent, text="Announcements / Advertisements")
        ann.pack(fill="both", expand=True, pady=5)
        self.announcement_box = tk.Text(ann, height=6, wrap="word")
        self.announcement_box.insert("end", "Train Model Running (Imperial Units)...\n")
        self.announcement_box.pack(fill="both", expand=True, padx=5, pady=5)

    def create_static_map_panel(self, parent):
        map_frame = ttk.LabelFrame(parent, text="Train Route Map")
        map_frame.pack(fill="both", expand=True, padx=10, pady=10)
        map_path = os.path.join(os.path.dirname(__file__), "map.png")
        img = Image.open(map_path).resize((850, 650))
        self.map_img = ImageTk.PhotoImage(img)
        lbl = ttk.Label(map_frame, image=self.map_img)
        lbl.pack(fill="both", expand=True)

    # ==== Update loop ====
    def update_loop(self):
        inputs = self.data["inputs"]
        self.model.engine_failure = self.engine_fail.get()
        self.model.brake_failure = self.brake_fail.get()
        self.model.signal_failure = self.signal_fail.get()

        self.model.lights_on = inputs.get("lights_on", False)
        self.model.left_door_open = inputs.get("left_door_open", False)
        self.model.right_door_open = inputs.get("right_door_open", False)
        self.model.temperature_F = inputs.get("temperature_F", 68.0)

        outputs = self.model.update(
            inputs["commanded_power_hp"],
            inputs["authority_yds"],
            inputs["passengers_boarding"],
        )
        self.write_json(outputs)

        # UI refresh
        self.info_labels["Velocity (mph)"].config(text=f"Velocity: {outputs['velocity_mph']:.2f} mph")
        self.info_labels["Acceleration (ft/s²)"].config(text=f"Acceleration: {outputs['acceleration_ftps2']:.2f} ft/s²")
        self.info_labels["Position (yds)"].config(text=f"Position: {outputs['position_yds']:.1f} yds")
        self.info_labels["Authority Remaining (yds)"].config(
            text=f"Authority Remaining: {outputs['authority_yds']:.1f} yds"
        )
        self.info_labels["Current Station"].config(
            text=f"Current Station: {outputs['current_station']} | Next: {outputs['next_station']}"
        )
        self.info_labels["Passengers Onboard"].config(
            text=f"Passengers Onboard: {outputs['passengers_onboard']}"
        )
        if outputs["eta_s"]:
            self.info_labels["ETA to Next Station"].config(
                text=f"ETA to Next Station: {outputs['eta_s']:.1f} s"
            )
        else:
            self.info_labels["ETA to Next Station"].config(text="ETA to Next Station: --")

        self.env_labels["Lights On"].config(text=f"Lights On: {'Yes' if self.model.lights_on else 'No'}")
        self.env_labels["Left Door"].config(text=f"Left Door: {'Open' if self.model.left_door_open else 'Closed'}")
        self.env_labels["Right Door"].config(text=f"Right Door: {'Open' if self.model.right_door_open else 'Closed'}")
        self.env_labels["Cabin Temperature (°F)"].config(text=f"Cabin Temperature: {self.model.temperature_F:.1f} °F")

        self.after(int(self.model.dt * 1000), self.update_loop)


if __name__ == "__main__":
    app = TrainModelUI()
    app.mainloop()
