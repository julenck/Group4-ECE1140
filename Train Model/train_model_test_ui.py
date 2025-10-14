import tkinter as tk
from tkinter import ttk
import json, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

JSON_FILE = "train_data.json"

class TrainModelTestUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Train Model Test UI")
        self.geometry("650x700")
        self.json_path = JSON_FILE
        self.data = self.load_or_create_json()

        # Inputs section
        inputs_frame = ttk.LabelFrame(self, text="Train Inputs")
        inputs_frame.pack(fill="both", expand=False, padx=10, pady=10)

        self.power = tk.DoubleVar(value=self.data["inputs"]["commanded_power"])
        ttk.Label(inputs_frame, text="Commanded Power (W):").pack(anchor="w")
        ttk.Scale(inputs_frame, from_=0, to=120000, orient="horizontal", variable=self.power).pack(fill="x")

        self.authority = tk.DoubleVar(value=self.data["inputs"]["authority"])
        ttk.Label(inputs_frame, text="Authority (m):").pack(anchor="w")
        ttk.Entry(inputs_frame, textvariable=self.authority).pack(fill="x")

        self.doors = tk.BooleanVar(value=self.data["inputs"]["doors_open"])
        ttk.Checkbutton(inputs_frame, text="Doors Open", variable=self.doors).pack(anchor="w")
        self.lights = tk.BooleanVar(value=self.data["inputs"]["lights_on"])
        ttk.Checkbutton(inputs_frame, text="Cabin Lights ON", variable=self.lights).pack(anchor="w")

        self.temp = tk.DoubleVar(value=self.data["inputs"]["temperature_F"])
        ttk.Label(inputs_frame, text="Cabin Temperature (°F):").pack(anchor="w")
        ttk.Entry(inputs_frame, textvariable=self.temp).pack(fill="x")

        self.emergency = tk.BooleanVar(value=self.data["inputs"]["emergency_brake"])
        ttk.Checkbutton(inputs_frame, text="Emergency Brake", variable=self.emergency).pack(anchor="w")

        ttk.Button(self, text="Send Inputs", command=self.update_json).pack(pady=10)

        # Specs section
        specs_frame = ttk.LabelFrame(self, text="Train Specifications")
        specs_frame.pack(fill="both", expand=True, padx=10, pady=10)
        for k, v in self.data["specs"].items():
            ttk.Label(specs_frame, text=f"{k}: {v}").pack(anchor="w", padx=10)

    def load_or_create_json(self):
        if not os.path.exists(self.json_path):
            print("⚙️ Creating default train_data.json...")
            default_data = {
                "specs": {
                    "length_ft": 66.0,
                    "width_ft": 10.0,
                    "height_ft": 11.5,
                    "mass_kg": 40900,
                    "max_power_w": 120000,
                    "max_accel_mps2": 0.5,
                    "service_brake_mps2": -1.2,
                    "emergency_brake_mps2": -2.7,
                    "capacity": 222,
                    "crew_count": 2
                },
                "inputs": {
                    "commanded_power": 60000,
                    "authority": 300,
                    "doors_open": False,
                    "lights_on": True,
                    "temperature_F": 68,
                    "emergency_brake": False
                },
                "outputs": {}
            }
            with open(self.json_path, "w") as f:
                json.dump(default_data, f, indent=4)
            return default_data
        with open(self.json_path, "r") as f:
            return json.load(f)

    def update_json(self):
        with open(self.json_path, "r") as f:
            data = json.load(f)
        data["inputs"] = {
            "commanded_power": self.power.get(),
            "authority": self.authority.get(),
            "doors_open": self.doors.get(),
            "lights_on": self.lights.get(),
            "temperature_F": self.temp.get(),
            "emergency_brake": self.emergency.get()
        }
        with open(self.json_path, "w") as f:
            json.dump(data, f, indent=4)
        self.title("✔ Inputs Updated")

if __name__ == "__main__":
    app = TrainModelTestUI()
    app.mainloop()
