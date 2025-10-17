import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from math import sqrt

# Ensure correct working directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
JSON_FILE = "train_data.json"


class TrainModelTestUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Train Model Test UI - Full Input/Output Verification")
        self.geometry("700x850")

        # Load existing JSON
        self.data = self.load_json()
        self.inputs = self.data.get("inputs", {})
        self.specs = self.data.get("specs", {})

        # === Title ===
        ttk.Label(self, text="Train Model Input/Output Testing Interface",
                  font=("Arial", 14, "bold")).pack(pady=10)

        # === Input Frame ===
        input_frame = ttk.LabelFrame(self, text="Inputs (Editable)")
        input_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.entries = {}
        for key, label in [
            ("commanded_power", "Commanded Power (W)"),
            ("authority", "Authority (m)"),
            ("speed_limit", "Speed Limit (mph)"),
            ("commanded_speed", "Commanded Speed (mph)"),
            ("beacon_data", "Beacon Data (Block/Next Station)"),
            ("passengers_boarding", "Passengers Boarding"),
            ("crew_count", "Crew Count"),
            ("emergency_brake", "Emergency Brake (True/False)")
        ]:
            self.create_entry(input_frame, key, label)

        ttk.Button(self, text="Update & Run Simulation", command=self.run_simulation).pack(pady=10)

        # === Output Frame ===
        output_frame = ttk.LabelFrame(self, text="Outputs (Calculated)")
        output_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.output_labels = {}
        for key in [
            "velocity_mps", "acceleration_mps2", "position_m",
            "authority_m", "temperature_F", "eta_s", "current_station", "next_station"
        ]:
            lbl = ttk.Label(output_frame, text=f"{key}: --")
            lbl.pack(anchor="w", padx=10, pady=2)
            self.output_labels[key] = lbl

        ttk.Label(self, text="* Values are written to train_data.json automatically *",
                  foreground="gray").pack(pady=5)

    # === Entry builder ===
    def create_entry(self, parent, key, label):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", padx=10, pady=6)
        ttk.Label(frame, text=label, width=30, anchor="w").pack(side="left")
        entry = ttk.Entry(frame)
        entry.pack(side="right", fill="x", expand=True)
        entry.insert(0, str(self.inputs.get(key, "")))
        self.entries[key] = entry

    # === JSON Loader ===
    def load_json(self):
        if not os.path.exists(JSON_FILE):
            messagebox.showerror("Error", f"{JSON_FILE} not found. Please run train_model_ui.py first.")
            self.destroy()
            return {}
        with open(JSON_FILE, "r") as f:
            return json.load(f)

    # === Simulation Logic (Simplified physics model) ===
    def run_simulation(self):
        """Updates JSON and computes basic outputs."""
        try:
            # Update input values from entries
            for key, entry in self.entries.items():
                val = entry.get().strip()
                if val.lower() in ["true", "false"]:
                    self.inputs[key] = val.lower() == "true"
                else:
                    try:
                        self.inputs[key] = float(val)
                    except ValueError:
                        self.inputs[key] = val

            # Write updated inputs back to JSON
            self.data["inputs"] = self.inputs

            # Run physics-like computation
            outputs = self.compute_outputs()
            self.data["outputs"] = outputs

            # Save everything back
            with open(JSON_FILE, "w") as f:
                json.dump(self.data, f, indent=4)

            # Update UI labels
            for key, val in outputs.items():
                self.output_labels[key].config(text=f"{key}: {val}")

            messagebox.showinfo("Success", "Inputs updated and outputs calculated successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Simulation failed: {e}")

    # === Core physics logic (simplified same as TrainModel) ===
    def compute_outputs(self):
        power = float(self.inputs.get("commanded_power", 0))
        authority = float(self.inputs.get("authority", 0))
        emergency = self.inputs.get("emergency_brake", False)

        mass = float(self.specs.get("mass_kg", 40900))
        max_accel = float(self.specs.get("max_accel_mps2", 0.5))
        max_emergency_brake = float(self.specs.get("emergency_brake_mps2", -2.7))

        # Simple model physics
        velocity = sqrt(max(power / (mass * 2), 0))  # fake simplified
        acceleration = max_accel if not emergency else max_emergency_brake
        position = velocity * 5
        authority_left = max(authority - position, 0)

        temperature = 68.0
        current_station = "Downtown"
        next_station = "Midtown"
        eta = round(authority_left / max(velocity, 0.1), 1)

        return {
            "velocity_mps": round(velocity, 2),
            "acceleration_mps2": round(acceleration, 2),
            "position_m": round(position, 1),
            "authority_m": round(authority_left, 1),
            "temperature_F": temperature,
            "eta_s": eta,
            "current_station": current_station,
            "next_station": next_station
        }


if __name__ == "__main__":
    app = TrainModelTestUI()
    app.mainloop()
