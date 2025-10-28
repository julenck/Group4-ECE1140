import tkinter as tk
from tkinter import ttk
import json
import os


# === File Paths ===
TRACK_TO_TRAIN_FILE = "../Track_Model/track_model_to_Train_Model.json"  # Read from Track Model
TRAIN_DATA_FILE = "train_data.json"  # Train Model's own JSON data


# === Train Model Core ===
class TrainModel:
    def __init__(self, specs):
        """Initialize Train Model with specifications"""
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

        # Dynamic state
        self.velocity_mph = 0.0
        self.acceleration_ftps2 = 0.0
        self.position_yds = 0.0
        self.authority_yds = 0.0

        self.dt = 0.5

    def update(self, commanded_speed, commanded_authority, speed_limit, station_name, door_side):
        """Compute new physics outputs based on Track Model input"""
        traction_force = self.max_power_hp * 550 / max(self.velocity_mph + 0.1, 1)
        resistance = 5000 + 30 * self.velocity_mph + 0.5 * self.velocity_mph ** 2
        brake_force = abs(self.service_brake_ftps2) * self.mass_lbs

        net_force = traction_force - resistance - brake_force
        self.acceleration_ftps2 = max(min(net_force / self.mass_lbs, self.max_accel_ftps2), self.emergency_brake_ftps2)

        delta_v_ftps = self.acceleration_ftps2 * self.dt
        delta_v_mph = delta_v_ftps * 0.681818
        self.velocity_mph = max(self.velocity_mph + delta_v_mph, 0)

        delta_x_ft = (self.velocity_mph / 0.681818) * self.dt + 0.5 * self.acceleration_ftps2 * self.dt ** 2
        self.position_yds += delta_x_ft / 3.0
        self.authority_yds = commanded_authority

        return {
            "velocity_mph": round(self.velocity_mph, 2),
            "acceleration_ftps2": round(self.acceleration_ftps2, 2),
            "position_yds": round(self.position_yds, 2),
            "authority_yds": commanded_authority,
            "speed_limit": speed_limit,
            "station_name": station_name,
            "door_side": door_side
        }


# === Train Model UI ===
class TrainModelUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Train Model - Track Model Integrated")
        self.geometry("950x600")

        # Load or create train_data.json
        self.data = self.load_or_create_json()
        self.model = TrainModel(self.data["specs"])

        # UI Labels
        self.info_labels = {}
        frame = ttk.LabelFrame(self, text="Train Model Data (from Track Model)")
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        for key in [
            "Velocity (mph)", "Acceleration (ft/s²)", "Position (yds)",
            "Authority (yds)", "Speed Limit (mph)", "Station", "Door Side"
        ]:
            lbl = ttk.Label(frame, text=f"{key}: --", font=("Arial", 11))
            lbl.pack(anchor="w", padx=10, pady=4)
            self.info_labels[key] = lbl

        self.update_loop()

    # === JSON loading ===
    def load_or_create_json(self):
        """Create or load the base train_data.json"""
        if not os.path.exists(TRAIN_DATA_FILE):
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
            with open(TRAIN_DATA_FILE, "w") as f:
                json.dump(default_data, f, indent=4)
            return default_data
        with open(TRAIN_DATA_FILE, "r") as f:
            return json.load(f)

    # === Read data from Track Model ===
    def read_from_track_model(self):
        """Read information from track_model_to_Train_Model.json"""
        try:
            with open(TRACK_TO_TRAIN_FILE, "r") as f:
                data = json.load(f)

            block = data.get("block", {})
            beacon = data.get("beacon", {})

            # Keep the same naming as in the Track Model file
            return {
                "commanded speed": block.get("commanded speed", 0),
                "commanded authority": block.get("commanded authority", 0),
                "speed limit": beacon.get("speed limit", 30),
                "station name": beacon.get("station name", "Unknown"),
                "side_door": beacon.get("side_door", "Unknown")
            }

        except Exception as e:
            print(f"[Error reading track file]: {e}")
            return None

    # === Write back to train_data.json ===
    def write_to_train_data(self, inputs, outputs):
        """Synchronize inputs and outputs to train_data.json"""
        self.data["inputs"].update(inputs)
        self.data["outputs"].update(outputs)
        with open(TRAIN_DATA_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

    # === Update Loop ===
    def update_loop(self):
        """Periodically update UI and data from Track Model"""
        inputs = self.read_from_track_model()
        if inputs:
            outputs = self.model.update(
                commanded_speed=inputs["commanded speed"],
                commanded_authority=inputs["commanded authority"],
                speed_limit=inputs["speed limit"],
                station_name=inputs["station name"],
                door_side=inputs["side_door"]
            )

            # Write both inputs and outputs into train_data.json
            self.write_to_train_data(inputs, outputs)

            # Update the on-screen display
            self.info_labels["Velocity (mph)"].config(text=f"Velocity: {outputs['velocity_mph']} mph")
            self.info_labels["Acceleration (ft/s²)"].config(text=f"Acceleration: {outputs['acceleration_ftps2']} ft/s²")
            self.info_labels["Position (yds)"].config(text=f"Position: {outputs['position_yds']} yds")
            self.info_labels["Authority (yds)"].config(text=f"Authority: {outputs['authority_yds']} yds")
            self.info_labels["Speed Limit (mph)"].config(text=f"Speed Limit: {outputs['speed_limit']} mph")
            self.info_labels["Station"].config(text=f"Station: {outputs['station_name']}")
            self.info_labels["Door Side"].config(text=f"Door Side: {outputs['door_side']}")

        # Refresh every 0.5s
        self.after(int(self.model.dt * 1000), self.update_loop)


# === Run ===
if __name__ == "__main__":
    app = TrainModelUI()
    app.mainloop()
