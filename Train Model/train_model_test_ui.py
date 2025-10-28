import tkinter as tk
from tkinter import ttk
import json
import os

# === File paths ===
TRACK_TO_TRAIN_FILE = "../Track_Model/track_model_to_Train_Model.json"
TRAIN_DATA_FILE = "train_data.json"

os.chdir(os.path.dirname(os.path.abspath(__file__)))


# === Train Model Core (simplified, no specs) ===
class TrainModel:
    def __init__(self):
        """Simplified Train Model for test UI"""
        self.velocity_mph = 0.0
        self.acceleration_ftps2 = 0.0
        self.position_yds = 0.0
        self.authority_yds = 0.0
        self.current_station = "Unknown"
        self.next_station = "Unknown"
        self.left_door_open = False
        self.right_door_open = False
        self.speed_limit = 0
        self.dt = 0.5

    def update(self, commanded_speed, commanded_authority, speed_limit, current_station, next_station, side_door):
        """Basic physics + state update from Track Model data"""
        target_speed_ftps = commanded_speed * 1.46667
        accel = (target_speed_ftps - (self.velocity_mph * 1.46667)) / 2.0
        self.acceleration_ftps2 = max(min(accel, 1.64), -3.94)

        delta_v_ftps = self.acceleration_ftps2 * self.dt
        delta_v_mph = delta_v_ftps * 0.681818
        self.velocity_mph = max(self.velocity_mph + delta_v_mph, 0)
        delta_x_ft = (self.velocity_mph / 0.681818) * self.dt
        delta_x_yds = delta_x_ft / 3.0
        self.position_yds += delta_x_yds
        self.authority_yds = commanded_authority

        self.left_door_open = side_door.lower() == "left"
        self.right_door_open = side_door.lower() == "right"
        self.current_station = current_station
        self.next_station = next_station
        self.speed_limit = speed_limit

        return {
            "velocity_mph": self.velocity_mph,
            "acceleration_ftps2": self.acceleration_ftps2,
            "position_yds": self.position_yds,
            "authority_yds": self.authority_yds,
            "current_station": self.current_station,
            "next_station": self.next_station,
            "left_door_open": self.left_door_open,
            "right_door_open": self.right_door_open,
            "speed_limit": self.speed_limit
        }


# === Test UI ===
class TrainModelTestUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Train Model Test UI - Integrated with Track Model")
        self.geometry("750x500")

        self.model = TrainModel()
        self.data = {}
        self.create_ui()

        self.update_loop()

    def create_ui(self):
        """UI layout setup"""
        frame = ttk.LabelFrame(self, text="Train Model Data (from Track Model)")
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        self.labels = {}
        for key in [
            "Velocity (mph)",
            "Acceleration (ft/s²)",
            "Position (yds)",
            "Authority (yds)",
            "Current Station",
            "Next Station",
            "Speed Limit (mph)",
            "Left Door",
            "Right Door"
        ]:
            lbl = ttk.Label(frame, text=f"{key}: --")
            lbl.pack(anchor="w", padx=10, pady=3)
            self.labels[key] = lbl

    def read_from_track_model(self):
        """Read data from Track Model JSON"""
        try:
            with open(TRACK_TO_TRAIN_FILE, "r") as f:
                data = json.load(f)
            block = data.get("block", {})
            beacon = data.get("beacon", {})
            return {
                "commanded speed": block.get("commanded speed", 0),
                "commanded authority": block.get("commanded authority", 0),
                "speed limit": beacon.get("speed limit", 30),
                "side_door": beacon.get("side_door", "Right"),
                "current station": beacon.get("current station", "Unknown"),
                "next station": beacon.get("next station", "Unknown")
            }
        except Exception as e:
            print(f"[Error] Cannot read Track Model JSON: {e}")
            return None

    def update_loop(self):
        """Periodic update"""
        inputs = self.read_from_track_model()
        if inputs:
            outputs = self.model.update(
                commanded_speed=inputs["commanded speed"],
                commanded_authority=inputs["commanded authority"],
                speed_limit=inputs["speed limit"],
                current_station=inputs["current station"],
                next_station=inputs["next station"],
                side_door=inputs["side_door"]
            )

            # Refresh UI
            self.labels["Velocity (mph)"].config(text=f"Velocity: {outputs['velocity_mph']:.2f} mph")
            self.labels["Acceleration (ft/s²)"].config(text=f"Acceleration: {outputs['acceleration_ftps2']:.2f} ft/s²")
            self.labels["Position (yds)"].config(text=f"Position: {outputs['position_yds']:.1f} yds")
            self.labels["Authority (yds)"].config(text=f"Authority: {outputs['authority_yds']:.1f} yds")
            self.labels["Current Station"].config(text=f"Current Station: {outputs['current_station']}")
            self.labels["Next Station"].config(text=f"Next Station: {outputs['next_station']}")
            self.labels["Speed Limit (mph)"].config(text=f"Speed Limit: {outputs['speed_limit']} mph")
            self.labels["Left Door"].config(
                text=f"Left Door: {'Open' if outputs['left_door_open'] else 'Closed'}"
            )
            self.labels["Right Door"].config(
                text=f"Right Door: {'Open' if outputs['right_door_open'] else 'Closed'}"
            )

        self.after(int(self.model.dt * 1000), self.update_loop)


if __name__ == "__main__":
    app = TrainModelTestUI()
    app.mainloop()
