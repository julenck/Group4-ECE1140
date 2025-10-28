import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import json
import os
import math

# === File Paths ===
TRACK_TO_TRAIN_FILE = "../Track_Model/track_model_to_Train_Model.json"
TRAIN_DATA_FILE = "train_data.json"

# === Ensure Working Directory ===
os.chdir(os.path.dirname(os.path.abspath(__file__)))


# === TRAIN MODEL CORE (Imperial Units) ===
class TrainModel:
    def __init__(self, specs):
        """Initialize Train Model with static specifications"""
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

        # Passenger system
        self.passengers_boarding = 0
        self.passengers_disembarking = 0
        self.passengers_onboard = 0

        # Door and light system
        self.left_door_open = False
        self.right_door_open = False
        self.lights_on = True

        # Failures
        self.engine_failure = False
        self.brake_failure = False
        self.signal_failure = False
        self.emergency_brake = False

        # Route and timing
        self.current_station = "Downtown"
        self.next_station = "Midtown"
        self.station_positions_yds = {"Downtown": 0, "Midtown": 547, "Uptown": 1094}
        self.dt = 0.5

    def update(self, commanded_speed, commanded_authority, speed_limit, station_name, door_side):
        """Compute motion and operational updates from Track Model inputs"""
        # Convert commanded speed from mph to ft/s
        target_speed_ftps = commanded_speed * 1.46667

        if self.engine_failure:
            traction_force = 0
        else:
            traction_force = self.max_power_hp * 550 / max(self.velocity_mph + 0.1, 0.1)

        resistance = 5000 + 30 * self.velocity_mph + 0.5 * self.velocity_mph ** 2

        if self.emergency_brake:
            brake_force = abs(self.emergency_brake_ftps2) * self.mass_lbs
        elif self.brake_failure:
            brake_force = 0
        else:
            brake_force = abs(self.service_brake_ftps2) * self.mass_lbs if self.velocity_mph > 0 else 0

        net_force = traction_force - resistance - brake_force
        self.acceleration_ftps2 = max(
            min(net_force / self.mass_lbs, self.max_accel_ftps2), self.emergency_brake_ftps2
        )

        delta_v_ftps = self.acceleration_ftps2 * self.dt
        delta_v_mph = delta_v_ftps * 0.681818
        self.velocity_mph = max(self.velocity_mph + delta_v_mph, 0)
        delta_x_ft = (self.velocity_mph / 0.681818) * self.dt + 0.5 * self.acceleration_ftps2 * self.dt**2
        delta_x_yds = delta_x_ft / 3.0
        self.position_yds += delta_x_yds
        self.authority_yds = commanded_authority

        # Passenger logic
        self.passengers_disembarking = int(max(0, self.passengers_onboard * 0.05))
        self.passengers_onboard = max(
            0,
            min(self.capacity, self.passengers_onboard + self.passengers_boarding - self.passengers_disembarking),
        )

        # Door logic based on side_door info
        self.left_door_open = (door_side.lower() == "left")
        self.right_door_open = (door_side.lower() == "right")

        # Update station name from beacon
        self.current_station = station_name

        return {
            "velocity_mph": self.velocity_mph,
            "acceleration_ftps2": self.acceleration_ftps2,
            "position_yds": self.position_yds,
            "authority_yds": self.authority_yds,
            "speed_limit": speed_limit,
            "station_name": station_name,
            "door_side": door_side,
        }


# === TRAIN MODEL UI (with Track Model integration) ===
class TrainModelUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Train Model - Integrated with Track Model")
        self.geometry("1450x900")

        self.json_path = TRAIN_DATA_FILE
        self.data = self.load_or_create_json()
        self.model = TrainModel(self.data["specs"])

        # === Layout configuration ===
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        # === LEFT SIDE: Panels ===
        left_frame = ttk.LabelFrame(self, text="Train Information & Environment")
        left_frame.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)

        self.create_info_panel(left_frame)
        self.create_env_panel(left_frame)
        self.create_specs_panel(left_frame)
        self.create_failure_panel(left_frame)
        self.create_control_panel(left_frame)
        self.create_announcements_panel(left_frame)

        # === RIGHT SIDE: Map ===
        right_frame = ttk.LabelFrame(self, text="Train Route Map")
        right_frame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)
        self.create_static_map_panel(right_frame)

        # Start update loop
        self.update_loop()

    # === JSON management ===
    def load_or_create_json(self):
        """Create or load train_data.json if not found"""
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
                "inputs": {},
                "outputs": {},
            }
            with open(self.json_path, "w") as f:
                json.dump(default_data, f, indent=4)
            return default_data
        with open(self.json_path, "r") as f:
            return json.load(f)

    def write_json(self, inputs, outputs):
        """Write both inputs and outputs back into train_data.json"""
        self.data["inputs"].update(inputs)
        self.data["outputs"].update(outputs)
        with open(self.json_path, "w") as f:
            json.dump(self.data, f, indent=4)

    # === NEW: Read from Track Model ===
    def read_from_track_model(self):
        """Read data from Track Model JSON file"""
        try:
            with open(TRACK_TO_TRAIN_FILE, "r") as f:
                data = json.load(f)

            block = data.get("block", {})
            beacon = data.get("beacon", {})

            return {
                "commanded speed": block.get("commanded speed", 0),
                "commanded authority": block.get("commanded authority", 0),
                "speed limit": beacon.get("speed limit", 30),
                "station name": beacon.get("station name", "Unknown"),
                "side_door": beacon.get("side_door", "Right"),
            }
        except Exception as e:
            print(f"Error reading track model file: {e}")
            return None

    # === UI Panels ===
    def create_info_panel(self, parent):
        info = ttk.LabelFrame(parent, text="Train Dynamics (Imperial Units)")
        info.pack(fill="x", pady=5)
        self.info_labels = {}
        for key in [
            "Velocity (mph)",
            "Acceleration (ft/s²)",
            "Position (yds)",
            "Authority Remaining (yds)",
            "Current Station",
            "Speed Limit (mph)",
        ]:
            lbl = ttk.Label(info, text=f"{key}: --")
            lbl.pack(anchor="w", padx=10, pady=2)
            self.info_labels[key] = lbl

    def create_env_panel(self, parent):
        env = ttk.LabelFrame(parent, text="Environment Status (Read-only)")
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
            self.emergency_button.config(text="EMERGENCY BRAKE ACTIVE")
        else:
            self.emergency_button.config(text="EMERGENCY BRAKE")

    def create_announcements_panel(self, parent):
        ann = ttk.LabelFrame(parent, text="Announcements / Advertisements")
        ann.pack(fill="both", expand=True, pady=5)
        self.announcement_box = tk.Text(ann, height=6, wrap="word")
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

    # === Periodic Update ===
    def update_loop(self):
        """Periodic data read and UI refresh"""
        inputs = self.read_from_track_model()
        if inputs:
            outputs = self.model.update(
                commanded_speed=inputs["commanded speed"],
                commanded_authority=inputs["commanded authority"],
                speed_limit=inputs["speed limit"],
                station_name=inputs["station name"],
                door_side=inputs["side_door"],
            )
            self.write_json(inputs, outputs)

            # Update UI values
            self.info_labels["Velocity (mph)"].config(text=f"Velocity: {outputs['velocity_mph']:.2f} mph")
            self.info_labels["Acceleration (ft/s²)"].config(text=f"Acceleration: {outputs['acceleration_ftps2']:.2f} ft/s²")
            self.info_labels["Position (yds)"].config(text=f"Position: {outputs['position_yds']:.1f} yds")
            self.info_labels["Authority Remaining (yds)"].config(text=f"Authority: {outputs['authority_yds']:.1f} yds")
            self.info_labels["Current Station"].config(text=f"Station: {outputs['station_name']}")
            self.info_labels["Speed Limit (mph)"].config(text=f"Speed Limit: {outputs['speed_limit']} mph")

        # Loop again
        self.after(int(self.model.dt * 1000), self.update_loop)


# === MAIN ===
if __name__ == "__main__":
    app = TrainModelUI()
    app.mainloop()
