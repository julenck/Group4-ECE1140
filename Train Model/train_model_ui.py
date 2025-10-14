import tkinter as tk
from tkinter import ttk
import json
import os

# ✅ Always switch to script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

JSON_FILE = "train_data.json"


# === TRAIN MODEL CORE ===
class TrainModel:
    def __init__(self, specs):
        # --- Specs from JSON ---
        self.length = specs["length_ft"]
        self.width = specs["width_ft"]
        self.height = specs["height_ft"]
        self.mass = specs["mass_kg"]
        self.max_power = specs["max_power_w"]
        self.max_accel = specs["max_accel_mps2"]
        self.max_service_brake = specs["service_brake_mps2"]
        self.max_emergency_brake = specs["emergency_brake_mps2"]
        self.capacity = specs["capacity"]
        self.crew_count = specs["crew_count"]

        # --- State ---
        self.velocity = 0.0
        self.acceleration = 0.0
        self.position = 0.0
        self.temperature = 68.0
        self.authority = 300.0

        # --- Status Flags ---
        self.engine_failure = False
        self.brake_failure = False
        self.signal_failure = False
        self.emergency_brake = False

        self.dt = 0.5

    def update(self, power, doors_open, lights_on, temp_setpoint, authority, emergency_brake):
        """Perform one simulation step."""
        # Force calculation
        if self.engine_failure:
            traction_force = 0
        else:
            traction_force = power / max(self.velocity, 0.1)

        resistance = 5000 + 30 * self.velocity + 0.5 * self.velocity**2

        if emergency_brake:
            brake_force = abs(self.max_emergency_brake) * self.mass
        elif self.brake_failure:
            brake_force = 0
        else:
            brake_force = abs(self.max_service_brake) * self.mass if self.velocity > 0 else 0

        net_force = traction_force - resistance - brake_force
        self.acceleration = net_force / self.mass
        self.acceleration = max(min(self.acceleration, self.max_accel), self.max_emergency_brake)

        # Update motion
        self.velocity += self.acceleration * self.dt
        self.velocity = max(self.velocity, 0)
        self.position += self.velocity * self.dt + 0.5 * self.acceleration * self.dt**2
        self.authority = max(authority - self.velocity * self.dt, 0)

        # Temperature
        if self.temperature < temp_setpoint:
            self.temperature += 0.1
        elif self.temperature > temp_setpoint:
            self.temperature -= 0.1

        return {
            "velocity_mps": self.velocity,
            "acceleration_mps2": self.acceleration,
            "position_m": self.position,
            "authority_m": self.authority,
            "temperature_F": self.temperature,
            "doors_open": doors_open,
            "lights_on": lights_on,
            "engine_failure": self.engine_failure,
            "brake_failure": self.brake_failure,
            "signal_failure": self.signal_failure
        }


# === MAIN TRAIN MODEL UI ===
class TrainModelUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Train Model Software Module")
        self.geometry("1200x850")

        self.json_path = JSON_FILE
        self.data = self.load_or_create_json()
        self.model = TrainModel(self.data["specs"])

        # Layout
        for i in range(3):
            self.grid_columnconfigure(i, weight=1)
        self.grid_rowconfigure(0, weight=3)
        self.grid_rowconfigure(1, weight=2)
        self.grid_rowconfigure(2, weight=0)

        self.create_info_panel()
        self.create_specs_panel()
        self.create_failure_panel()
        self.create_announcements_panel()
        self.update_loop()

    def load_or_create_json(self):
        """Create file if not found."""
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

    def write_json(self, outputs):
        self.data["outputs"] = outputs
        with open(self.json_path, "w") as f:
            json.dump(self.data, f, indent=4)

    def create_info_panel(self):
        info = ttk.LabelFrame(self, text="Train Information & Dynamics")
        info.grid(row=0, column=0, columnspan=2, sticky="NSEW", padx=10, pady=10)
        self.velocity_label = ttk.Label(info, text="Velocity: 0.00 m/s")
        self.velocity_label.grid(row=0, column=0, sticky="w", padx=10, pady=3)
        self.accel_label = ttk.Label(info, text="Acceleration: 0.00 m/s²")
        self.accel_label.grid(row=1, column=0, sticky="w", padx=10, pady=3)
        self.position_label = ttk.Label(info, text="Position: 0.0 m")
        self.position_label.grid(row=2, column=0, sticky="w", padx=10, pady=3)
        self.temp_label = ttk.Label(info, text="Cabin Temperature: 68.0 °F")
        self.temp_label.grid(row=3, column=0, sticky="w", padx=10, pady=3)
        self.authority_label = ttk.Label(info, text="Authority Remaining: 300 m")
        self.authority_label.grid(row=4, column=0, sticky="w", padx=10, pady=3)

    def create_specs_panel(self):
        specs = ttk.LabelFrame(self, text="Train Specifications")
        specs.grid(row=0, column=2, sticky="NSEW", padx=10, pady=10)
        for k, v in self.data["specs"].items():
            ttk.Label(specs, text=f"{k}: {v}").pack(anchor="w", padx=10, pady=2)

    def create_failure_panel(self):
        fail = ttk.LabelFrame(self, text="Failure Status")
        fail.grid(row=1, column=0, sticky="NSEW", padx=10, pady=10)
        self.engine_fail = tk.BooleanVar()
        self.brake_fail = tk.BooleanVar()
        self.signal_fail = tk.BooleanVar()
        ttk.Checkbutton(fail, text="Engine Failure", variable=self.engine_fail).pack(anchor="w")
        ttk.Checkbutton(fail, text="Brake Failure", variable=self.brake_fail).pack(anchor="w")
        ttk.Checkbutton(fail, text="Signal Pickup Failure", variable=self.signal_fail).pack(anchor="w")

    def create_announcements_panel(self):
        ann = ttk.LabelFrame(self, text="Announcements / Advertisements")
        ann.grid(row=1, column=1, columnspan=2, sticky="NSEW", padx=10, pady=10)
        self.announcement_box = tk.Text(ann, height=6)
        self.announcement_box.insert("end", "Train Model Running...\n")
        self.announcement_box.pack(fill="both", expand=True)

    def update_loop(self):
        inputs = self.data["inputs"]
        self.model.engine_failure = self.engine_fail.get()
        self.model.brake_failure = self.brake_fail.get()
        self.model.signal_failure = self.signal_fail.get()

        outputs = self.model.update(
            inputs["commanded_power"],
            inputs["doors_open"],
            inputs["lights_on"],
            inputs["temperature_F"],
            inputs["authority"],
            inputs["emergency_brake"]
        )
        self.write_json(outputs)

        # update labels
        self.velocity_label.config(text=f"Velocity: {outputs['velocity_mps']:.2f} m/s")
        self.accel_label.config(text=f"Acceleration: {outputs['acceleration_mps2']:.2f} m/s²")
        self.position_label.config(text=f"Position: {outputs['position_m']:.1f} m")
        self.temp_label.config(text=f"Cabin Temperature: {outputs['temperature_F']:.1f} °F")
        self.authority_label.config(text=f"Authority Remaining: {outputs['authority_m']:.1f} m")

        self.after(int(self.model.dt * 1000), self.update_loop)


if __name__ == "__main__":
    app = TrainModelUI()
    app.mainloop()
