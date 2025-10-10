import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

class TrainModelTestUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Train Model Test UI")
        self.geometry("1100x780")
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        # === Load JSON ===
        self.data = self.load_json()
        self.status = self.data.get("train_status", {})
        self.failures = self.data.get("failures", {})

        # === Main layout ===
        main_pane = ttk.PanedWindow(self, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=15, pady=15)

        # Left side: Inputs
        input_frame = ttk.LabelFrame(main_pane, text="Force Input - Track Model")
        main_pane.add(input_frame, weight=2)
        self.populate_inputs(input_frame)

        # Right side: Outputs
        output_frame = ttk.LabelFrame(main_pane, text="Outputs - Train Model")
        main_pane.add(output_frame, weight=1)
        self.populate_outputs(output_frame)

        # Bottom: Failures
        failure_frame = ttk.LabelFrame(self, text="Failure Status (Editable)")
        failure_frame.pack(fill="x", padx=15, pady=10)
        self.populate_failures(failure_frame)

        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Update Inputs", command=self.save_changes).grid(row=0, column=0, padx=10)
        ttk.Button(button_frame, text="Refresh Outputs", command=self.refresh_outputs_once).grid(row=0, column=1, padx=10)

    # ==========================================================
    def load_json(self):
        try:
            with open("train_data.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            messagebox.showerror("Error", "train_data.json not found.")
            return {}
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return {}

    # ==========================================================
    def populate_inputs(self, frame):
        """Inputs according to reference image"""
        self.entries = {}
        self.bool_vars = {}

        fields = [
            ("Commanded Speed (mph)", "commanded_speed"),
            ("Authority", "authority"),
            ("Beacon", "beacon"),
            ("Speed Limit (mph)", "speed_limit"),
            ("Number of Passengers Boarding", "passengers_boarding"),
            ("Train Positions", "train_positions"),
            ("Crew Count", "crew_count"),
            ("Mass (lb)", "mass_lb"),
            ("Length (ft)", "length_ft"),
            ("Width (ft)", "width_ft"),
            ("Height (ft)", "height_ft"),
            ("Right Door (Bool)", "right_door"),
            ("Left Door (Bool)", "left_door"),
            ("Lights (Bool)", "lights_on"),
            ("Temperature UP (°F)", "temp_up"),
            ("Temperature DOWN (°F)", "temp_down"),
            ("Announcement / Dispatch System (String)", "announcement"),
            ("Service Brake (Bool)", "service_brake"),
            ("Power Availability (W)", "power_availability"),
            ("Deceleration Limit (mph/s)", "decel_limit_mphps"),
            ("Emergency Brake (Bool)", "emergency_brake"),
            ("Train Temperature (°F)", "train_temperature"),
        ]

        for i, (label, key) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", padx=10, pady=3)
            if "Bool" in label:
                var = tk.BooleanVar(value=self.status.get(key, False))
                chk = ttk.Checkbutton(frame, variable=var)
                chk.grid(row=i, column=1, sticky="w", padx=5)
                self.bool_vars[key] = var
            else:
                entry = ttk.Entry(frame, width=25)
                entry.insert(0, str(self.status.get(key, "")))
                entry.grid(row=i, column=1, sticky="w", padx=5)
                self.entries[key] = entry

        frame.columnconfigure(1, weight=1)

    # ==========================================================
    def populate_outputs(self, frame):
        """Outputs refreshed manually"""
        self.output_labels = {}
        outputs = [
            ("Commanded Speed", "commanded_speed"),
            ("Authority", "authority"),
            ("Beacon", "beacon"),
            ("Train Velocity (mph)", "velocity"),
            ("Train Temperature (°F)", "train_temperature"),
            ("Speed Limit (mph)", "speed_limit"),
            ("Passengers Boarding", "passengers_boarding"),
            ("Passengers Disembarking", "passengers_disembarking"),
        ]
        for i, (label, key) in enumerate(outputs):
            ttk.Label(frame, text=f"{label}:").grid(row=i, column=0, sticky="w", padx=10, pady=3)
            lbl = ttk.Label(frame, text="N/A")
            lbl.grid(row=i, column=1, sticky="w", padx=10, pady=3)
            self.output_labels[label] = (lbl, key)

        frame.columnconfigure(1, weight=1)
        self.update_outputs()

    # ==========================================================
    def populate_failures(self, frame):
        """Failure checkboxes"""
        self.failure_vars = {}
        for i, (key, val) in enumerate(self.failures.items()):
            var = tk.BooleanVar(value=val)
            ttk.Checkbutton(frame, text=key.replace("_", " ").title(), variable=var).grid(
                row=i, column=0, sticky="w", padx=15, pady=3
            )
            self.failure_vars[key] = var

    # ==========================================================
    def save_changes(self):
        """Save all modified input and failure data"""
        try:
            for k, e in self.entries.items():
                val = e.get().strip()
                try:
                    if "." in val:
                        val = float(val)
                    else:
                        val = int(val)
                except Exception:
                    pass
                self.status[k] = val

            for k, v in self.bool_vars.items():
                self.status[k] = v.get()

            for k, v in self.failure_vars.items():
                self.failures[k] = v.get()

            self.data["train_status"] = self.status
            self.data["failures"] = self.failures
            with open("train_data.json", "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)

            messagebox.showinfo("Success", "Inputs updated successfully!")
            self.update_outputs()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    # ==========================================================
    def update_outputs(self):
        """Refresh outputs from self.status"""
        for label, (lbl, key) in self.output_labels.items():
            val = self.status.get(key, "N/A")
            lbl.config(text=str(val))

    # ==========================================================
    def refresh_outputs_once(self):
        """Manual refresh from JSON"""
        try:
            new_data = self.load_json()
            if new_data:
                self.status = new_data.get("train_status", {})
                self.failures = new_data.get("failures", {})
                self.update_outputs()
            messagebox.showinfo("Refreshed", "Outputs updated from train_data.json.")
        except Exception as e:
            messagebox.showerror("Error", f"Refresh failed: {e}")

# ==========================================================
if __name__ == "__main__":
    app = TrainModelTestUI()
    app.mainloop()
