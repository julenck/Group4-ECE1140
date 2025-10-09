import tkinter as tk
from tkinter import ttk, messagebox
import json
import os


class TrainModelTestUI(tk.Tk):
    def __init__(self):
        super().__init__()

        # === Window setup ===
        self.title("Train Model Test UI (Inputs + Outputs)")
        self.geometry("650x800")
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        # === Data storage ===
        self.inputs = {}
        self.outputs = {}

        # === Create UI sections ===
        self.create_input_section()
        self.create_output_section()

        # === Buttons ===
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Update Inputs", command=self.update_inputs).grid(row=0, column=0, padx=10)
        ttk.Button(btn_frame, text="Refresh Outputs", command=self.refresh_outputs).grid(row=0, column=1, padx=10)

    # ----------------------------------------------------------------------
    def create_input_section(self):
        """Input parameters area."""
        frame = ttk.LabelFrame(self, text="Force Input - Train Model")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        params = [
            ("Commanded Speed", "25 mph"),
            ("Authority", "23 Block#"),
            ("Beacon", "128 B"),
            ("Speed Limit", "30 mph"),
            ("Passengers Boarding", "80"),
            ("Crew Count", "2"),
            ("Lights (Bool)", "True"),
            ("Doors Closed (Bool)", "True"),
            ("Temperature (°C)", "22"),
            ("Announcement", "Train approaching Herron Ave"),
            ("Emergency Brake (Bool)", "False"),
            ("Train Engine Failure", "False"),
            ("Signal Pickup Failure", "False"),
            ("Brake Failure", "False")
        ]

        for i, (label, default) in enumerate(params):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=4)
            entry = ttk.Entry(frame)
            entry.insert(0, default)
            entry.grid(row=i, column=1, padx=5, pady=4)
            self.inputs[label] = entry

    # ----------------------------------------------------------------------
    def create_output_section(self):
        """Output monitoring area."""
        frame = ttk.LabelFrame(self, text="Train Model Outputs")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        outputs = [
            ("Train Velocity", ""),
            ("Inside Temperature", ""),
            ("Passengers Onboard", ""),
            ("Lights Status", ""),
            ("Door Status", ""),
            ("Failures Active", "")
        ]

        for i, (label, default) in enumerate(outputs):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=4)
            entry = ttk.Entry(frame, state="readonly")
            entry.grid(row=i, column=1, padx=5, pady=4, sticky="ew")
            self.outputs[label] = entry

    # ----------------------------------------------------------------------
    def update_inputs(self):
        """Collect all input values and write them into train_data.json."""
        values = {label: widget.get() for label, widget in self.inputs.items()}

        new_data = {
            "train_status": {
                "commanded_speed": values.get("Commanded Speed", "N/A"),
                "authority": values.get("Authority", "N/A"),
                "beacon": values.get("Beacon", "N/A"),
                "speed_limit": values.get("Speed Limit", "N/A"),
                "passengers_boarding": int(values.get("Passengers Boarding", 0)),
                "crew_count": int(values.get("Crew Count", 2)),
                "lights_on": values.get("Lights (Bool)", "False") == "True",
                "doors_closed": values.get("Doors Closed (Bool)", "False") == "True",
                "temperature_inside": int(values.get("Temperature (°C)", 22)),
                "announcement": values.get("Announcement", ""),
                "emergency_brake": values.get("Emergency Brake (Bool)", "False") == "True"
            },
            "failures": {
                "train_engine_failure": values.get("Train Engine Failure", "False") == "True",
                "signal_pickup_failure": values.get("Signal Pickup Failure", "False") == "True",
                "brake_failure": values.get("Brake Failure", "False") == "True"
            }
        }

        # Load existing JSON and update
        try:
            with open("train_data.json", "r") as f:
                data = json.load(f)
        except:
            data = {}

        data.update(new_data)

        # Save updated JSON
        with open("train_data.json", "w") as f:
            json.dump(data, f, indent=2)

        messagebox.showinfo("Inputs Updated", "Inputs have been written to train_data.json.\nThe main UI will refresh automatically.")

    # ----------------------------------------------------------------------
    def refresh_outputs(self):
        """Read and display the current output values from JSON."""
        try:
            with open("train_data.json", "r") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Unable to read JSON file.\n{e}")
            return

        status = data.get("train_status", {})
        failures = data.get("failures", {})

        # Derived/Calculated fields
        onboard = status.get("passengers_boarding", 0) - status.get("passengers_disembarking", 0)
        lights = "ON" if status.get("lights_on") else "OFF"
        doors = "Closed" if status.get("doors_closed") else "Open"
        active_failures = [k.replace("_", " ").title() for k, v in failures.items() if v]
        failures_text = ", ".join(active_failures) if active_failures else "None"

        # Update display fields
        outputs = {
            "Train Velocity": status.get("commanded_speed", "N/A"),
            "Inside Temperature": f"{status.get('temperature_inside', 'N/A')} °C",
            "Passengers Onboard": onboard,
            "Lights Status": lights,
            "Door Status": doors,
            "Failures Active": failures_text
        }

        for label, value in outputs.items():
            widget = self.outputs[label]
            widget.config(state="normal")
            widget.delete(0, tk.END)
            widget.insert(0, str(value))
            widget.config(state="readonly")

        messagebox.showinfo("Outputs Refreshed", "Output values have been refreshed from train_data.json.")


if __name__ == "__main__":
    app = TrainModelTestUI()
    app.mainloop()
