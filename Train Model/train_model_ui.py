import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import json
import os
import math
from train_data_sync import sync_train_data  # import sync helper


# === File paths ===
TRACK_TO_TRAIN_FILE = "../Track_Model/track_model_to_Train_Model.json"
TRAIN_DATA_FILE = "train_data.json"

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

    def update(self, commanded_speed, commanded_authority, speed_limit,
               current_station, next_station, side_door):
        """Simulate motion and update station/door status"""
        # Convert commanded speed (mph → ft/s)
        target_speed_ftps = commanded_speed * 1.46667
        accel = (target_speed_ftps - (self.velocity_mph * 1.46667)) / 2.0
        self.acceleration_ftps2 = max(min(accel, self.max_accel_ftps2), self.service_brake_ftps2)

        # Integrate velocity and position
        delta_v_ftps = self.acceleration_ftps2 * self.dt
        delta_v_mph = delta_v_ftps * 0.681818
        self.velocity_mph = max(self.velocity_mph + delta_v_mph, 0)
        delta_x_ft = (self.velocity_mph / 0.681818) * self.dt
        self.position_yds += delta_x_ft / 3.0
        self.authority_yds = commanded_authority

        # Door logic
        self.left_door_open = side_door.lower() == "left"
        self.right_door_open = side_door.lower() == "right"

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
            "speed_limit": speed_limit
        }


# === Train Model UI ===
class TrainModelUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Train Model - Integrated with Train Controller")
        self.geometry("1450x900")

        self.json_path = TRAIN_DATA_FILE
        self.data = self.load_or_create_json()
        self.model = TrainModel(self.data["specs"])

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
        self.create_announcements_panel(left_frame)

        # Right panel (map)
        right_frame = ttk.Frame(self)
        right_frame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)
        self.create_static_map_panel(right_frame)

        # Start update loop
        self.update_loop()

    def load_or_create_json(self):
        """Load or initialize train_data.json if missing"""
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
                    "crew_count": 2
                },
                "inputs": {},
                "outputs": {}
            }
            with open(self.json_path, "w") as f:
                json.dump(default_data, f, indent=4)
        with open(self.json_path, "r") as f:
            return json.load(f)

    def write_json(self, inputs, outputs):
        """Write updated inputs and outputs back to train_data.json"""
        self.data["inputs"].update(inputs)
        self.data["outputs"].update(outputs)
        with open(self.json_path, "w") as f:
            json.dump(self.data, f, indent=4)

    def create_info_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Train Dynamics (Imperial Units)")
        frame.pack(fill="x", pady=5)
        self.info_labels = {}
        for key in [
            "Velocity (mph)",
            "Acceleration (ft/s²)",
            "Position (yds)",
            "Authority Remaining (yds)",
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
        for k, v in self.data["specs"].items():
            ttk.Label(frame, text=f"{k}: {v}").pack(anchor="w", padx=10, pady=1)

    def create_control_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Controls")
        frame.pack(fill="x", pady=10)
        self.emergency_button = ttk.Button(frame, text="EMERGENCY BRAKE")
        self.emergency_button.pack(fill="x", padx=20, pady=10)

    def create_announcements_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Announcements")
        frame.pack(fill="both", expand=True, pady=5)
        self.announcement_box = tk.Text(frame, height=6, wrap="word")
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
        """Periodic update: sync, compute, and refresh UI"""
        # 1. Sync input data from Train Controller
        sync_train_data()

        # 2. Reload updated train_data.json
        self.data = self.load_or_create_json()
        inputs = self.data.get("inputs", {})

        # 3. Run train model simulation if inputs exist
        if inputs:
            outputs = self.model.update(
                commanded_speed=inputs.get("commanded speed", 0),
                commanded_authority=inputs.get("commanded authority", 0),
                speed_limit=inputs.get("speed limit", 30),
                current_station=inputs.get("current station", "Unknown"),
                next_station=inputs.get("next station", "Unknown"),
                side_door=inputs.get("side_door", "Right")
            )

            self.write_json(inputs, outputs)

            # Update UI labels
            self.info_labels["Velocity (mph)"].config(text=f"Velocity: {outputs['velocity_mph']:.2f} mph")
            self.info_labels["Acceleration (ft/s²)"].config(text=f"Acceleration: {outputs['acceleration_ftps2']:.2f} ft/s²")
            self.info_labels["Position (yds)"].config(text=f"Position: {outputs['position_yds']:.1f} yds")
            self.info_labels["Authority Remaining (yds)"].config(text=f"Authority: {outputs['authority_yds']:.1f} yds")
            self.info_labels["Current Station"].config(text=f"Current Station: {outputs['station_name']}")
            self.info_labels["Next Station"].config(text=f"Next Station: {outputs['next_station']}")
            self.info_labels["Speed Limit (mph)"].config(text=f"Speed Limit: {outputs['speed_limit']} mph")

            self.env_labels["Left Door"].config(text=f"Left Door: {'Open' if outputs['left_door_open'] else 'Closed'}")
            self.env_labels["Right Door"].config(text=f"Right Door: {'Open' if outputs['right_door_open'] else 'Closed'}")


        # 4. Repeat periodically
        self.after(int(self.model.dt * 1000), self.update_loop)


if __name__ == "__main__":
    app = TrainModelUI()
    app.mainloop()
