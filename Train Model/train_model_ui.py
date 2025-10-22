import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import json
import os
import math
import random  # for disembarking simulation

# Ensure working directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
JSON_FILE = "train_data.json"


# === TRAIN MODEL CORE ===
class TrainModel:
    def __init__(self, specs):
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

        # Dynamic states
        self.velocity = 0.0
        self.acceleration = 0.0
        self.position = 0.0
        self.temperature = 68.0
        self.authority = 300.0

        # Failures
        self.engine_failure = False
        self.brake_failure = False
        self.signal_failure = False

        # Emergency brake
        self.emergency_brake = False

        # Route data
        self.current_station = "Downtown"
        self.next_station = "Midtown"
        self.station_positions = {"Downtown": 0, "Midtown": 500, "Uptown": 1000}

        # Passenger data
        self.passengers_onboard = 0
        self.passengers_disembarking = 0

        self.dt = 0.5

    def generate_disembarking(self):
        """Generate a small random number of passengers disembarking when stopped."""
        if self.velocity < 0.1:  # only when train is stopped
            return random.randint(0, int(max(self.passengers_onboard * 0.1, 1)))
        return 0

    def update(self, power, authority, passengers_boarding):
        """Core update logic for train motion and basic environment."""
        # --- Physics ---
        if self.engine_failure:
            traction_force = 0
        else:
            traction_force = power / max(self.velocity, 0.1)

        resistance = 5000 + 30 * self.velocity + 0.5 * self.velocity**2

        if self.emergency_brake:
            brake_force = abs(self.max_emergency_brake) * self.mass
        elif self.brake_failure:
            brake_force = 0
        else:
            brake_force = abs(self.max_service_brake) * self.mass if self.velocity > 0 else 0

        net_force = traction_force - resistance - brake_force
        self.acceleration = max(min(net_force / self.mass, self.max_accel), self.max_emergency_brake)

        # Kinematics
        self.velocity += self.acceleration * self.dt
        self.velocity = max(self.velocity, 0)
        self.position += self.velocity * self.dt + 0.5 * self.acceleration * self.dt**2
        self.authority = max(authority - self.velocity * self.dt, 0)

        # Passenger logic
        self.passengers_disembarking = self.generate_disembarking()
        self.passengers_onboard = max(
            min(self.passengers_onboard + passengers_boarding - self.passengers_disembarking, self.capacity),
            0,
        )

        # Station + ETA update
        self.update_stations()

        return {
            "velocity_mps": self.velocity,
            "acceleration_mps2": self.acceleration,
            "position_m": self.position,
            "authority_m": self.authority,
            "current_station": self.current_station,
            "next_station": self.next_station,
            "eta_s": self.calculate_eta(),
            "passengers_boarding": passengers_boarding,
            "passengers_disembarking": self.passengers_disembarking,
            "passengers_onboard": self.passengers_onboard,
        }

    def update_stations(self):
        pos = self.position
        if pos < self.station_positions["Midtown"]:
            self.current_station = "Downtown"
            self.next_station = "Midtown"
        elif pos < self.station_positions["Uptown"]:
            self.current_station = "Midtown"
            self.next_station = "Uptown"
        else:
            self.current_station = "Uptown"
            self.next_station = "End of Line"

    def calculate_eta(self):
        next_pos = self.station_positions.get(self.next_station, None)
        if next_pos is None or self.velocity <= 0:
            return None
        distance = max(next_pos - self.position, 0)
        return distance / max(self.velocity, 0.1)


# === TRAIN MODEL MAIN UI ===
class TrainModelUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Train Model UI - Real-Time Simulation")
        self.geometry("1400x850")

        self.json_path = JSON_FILE
        self.data = self.load_or_create_json()
        self.model = TrainModel(self.data["specs"])

        # Layout: left (info & controls), right (map)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        self.left_frame = ttk.Frame(self)
        self.left_frame.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)

        self.right_frame = ttk.Frame(self)
        self.right_frame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)

        # Left-side panels
        self.create_info_panel(self.left_frame)
        self.create_passenger_panel(self.left_frame)  # now only onboard
        self.create_specs_panel(self.left_frame)
        self.create_failure_panel(self.left_frame)
        self.create_control_panel(self.left_frame)
        self.create_announcements_panel(self.left_frame)

        # Right-side map
        self.create_map_panel(self.right_frame)

        self.update_loop()

    # ==== JSON LOADERS ====
    def load_or_create_json(self):
        if not os.path.exists(self.json_path):
            raise FileNotFoundError("train_data.json not found.")
        with open(self.json_path, "r") as f:
            return json.load(f)

    def write_json(self, outputs):
        self.data["outputs"] = outputs
        with open(self.json_path, "w") as f:
            json.dump(self.data, f, indent=4)

    # ==== PANELS ====
    def create_info_panel(self, parent):
        info = ttk.LabelFrame(parent, text="Train Information & Dynamics")
        info.pack(fill="x", pady=5)
        self.info_labels = {}
        for key in [
            "Velocity", "Acceleration", "Position",
            "Authority Remaining", "Current Station", "ETA to Next Station"
        ]:
            label = ttk.Label(info, text=f"{key}: --")
            label.pack(anchor="w", padx=10, pady=2)
            self.info_labels[key] = label

    def create_passenger_panel(self, parent):
        """New panel: only onboard passengers displayed."""
        pax = ttk.LabelFrame(parent, text="Passenger Information")
        pax.pack(fill="x", pady=5)
        self.pax_label = ttk.Label(pax, text="Passengers Onboard: --")
        self.pax_label.pack(anchor="w", padx=10, pady=2)

    def create_specs_panel(self, parent):
        specs = ttk.LabelFrame(parent, text="Train Specifications")
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
        """Activate or deactivate emergency brake."""
        self.model.emergency_brake = not self.model.emergency_brake
        if self.model.emergency_brake:
            self.emergency_button.config(text="EMERGENCY BRAKE ACTIVE", style="Danger.TButton")
        else:
            self.emergency_button.config(text="EMERGENCY BRAKE", style="TButton")

    def create_announcements_panel(self, parent):
        ann = ttk.LabelFrame(parent, text="Announcements / Advertisements")
        ann.pack(fill="both", expand=True, pady=5)
        self.announcement_box = tk.Text(ann, height=6, wrap="word")
        self.announcement_box.insert("end", "Train Model Running...\n")
        self.announcement_box.pack(fill="both", expand=True, padx=5, pady=5)

    def create_map_panel(self, parent):
        map_frame = ttk.LabelFrame(parent, text="Train Position Map")
        map_frame.pack(fill="both", expand=True, padx=10, pady=10)
        map_path = os.path.join(os.path.dirname(__file__), "map.png")
        img = Image.open(map_path).resize((850, 650))
        self.map_img = ImageTk.PhotoImage(img)
        self.map_canvas = tk.Canvas(map_frame, width=850, height=650)
        self.map_canvas.pack(fill="both", expand=True)
        self.map_canvas.create_image(0, 0, anchor="nw", image=self.map_img)
        self.map_canvas.create_text(80, 620, text="Downtown", fill="black", font=("Arial", 10, "bold"))
        self.map_canvas.create_text(420, 620, text="Midtown", fill="black", font=("Arial", 10, "bold"))
        self.map_canvas.create_text(760, 620, text="Uptown", fill="black", font=("Arial", 10, "bold"))
        self.train_dot = self.map_canvas.create_oval(10, 300, 30, 320, fill="red")

    # ==== UPDATE LOOP ====
    def update_loop(self):
        inputs = self.data["inputs"]
        self.model.engine_failure = self.engine_fail.get()
        self.model.brake_failure = self.brake_fail.get()
        self.model.signal_failure = self.signal_fail.get()

        # Update including passenger input
        outputs = self.model.update(
            inputs["commanded_power"],
            inputs["authority"],
            inputs["passengers_boarding"]
        )
        self.write_json(outputs)

        # Info panel
        self.info_labels["Velocity"].config(text=f"Velocity: {outputs['velocity_mps']:.2f} m/s")
        self.info_labels["Acceleration"].config(text=f"Acceleration: {outputs['acceleration_mps2']:.2f} m/s²")
        self.info_labels["Position"].config(text=f"Position: {outputs['position_m']:.1f} m")
        self.info_labels["Authority Remaining"].config(text=f"Authority Remaining: {outputs['authority_m']:.1f} m")
        self.info_labels["Current Station"].config(
            text=f"Current Station: {outputs['current_station']} | Next: {outputs['next_station']}"
        )
        if outputs["eta_s"]:
            self.info_labels["ETA to Next Station"].config(text=f"ETA to Next Station: {outputs['eta_s']:.1f} s")
        else:
            self.info_labels["ETA to Next Station"].config(text="ETA to Next Station: --")

        # Passenger panel (only onboard visible)
        self.pax_label.config(text=f"Passengers Onboard: {outputs['passengers_onboard']}")

        # Move train on map
        canvas_width = 850
        track_length = 1000
        x_pos = min(max((outputs["position_m"] / track_length) * canvas_width, 10), 830)
        self.map_canvas.coords(self.train_dot, x_pos - 10, 300, x_pos + 10, 320)

        self.after(int(self.model.dt * 1000), self.update_loop)


if __name__ == "__main__":
    app = TrainModelUI()
    app.mainloop()
