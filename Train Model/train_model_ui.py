import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import json
import os

class TrainModelUI(tk.Tk):
    def __init__(self):
        super().__init__()

        # === Window setup ===
        self.title("Train Model - UI")
        self.geometry("1200x1000")
        os.chdir(os.path.dirname(os.path.abspath(__file__)))  

        # === Load JSON data (shared data file) ===
        self.data = self.load_json()
        self.status = self.data.get("train_status", {})
        self.specs = self.data.get("train_specs", {})
        self.failures = self.data.get("failures", {})

        # === Layout configuration (2-column grid) ===
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        # === LEFT SIDE: Info panels ===
        left_frame = ttk.Frame(self)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.populate_left(left_frame)

        # === RIGHT SIDE: Map, Failures, and Controls ===
        right_frame = ttk.LabelFrame(self, text="Map, Failures & Control")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.populate_right(right_frame)

        # === BOTTOM: Announcements ===
        announce_frame = ttk.LabelFrame(self, text="Announcements")
        announce_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        self.populate_announcement(announce_frame)

        # === Auto refresh ===
        self.after(2000, self.refresh_data)

    # ----------------------------------------------------------------------
    def load_json(self):
        """Load train data from the shared JSON file."""
        try:
            with open("train_data.json", "r") as f:
                return json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load train_data.json\n{e}")
            return {}

    # ----------------------------------------------------------------------
    def populate_left(self, frame):
        """Left section divided into station, movement, passengers, and specs."""
        self.labels = {}

        # ===== Station & Schedule (新增三项) =====
        station_frame = ttk.LabelFrame(frame, text="Station & Schedule")
        station_frame.pack(fill="x", padx=5, pady=5)

        station_info = [
            ("Current Station", self.status.get("current_station", "N/A")),
            ("Next Station", self.status.get("next_station", "N/A")),
            ("ETA (min)", self.status.get("eta_min", "N/A")),
        ]
        for i, (label, value) in enumerate(station_info):
            lbl = ttk.Label(station_frame, text=f"{label}: {value}")
            lbl.grid(row=i, column=0, sticky="w", padx=10, pady=3)
            self.labels[label] = lbl

        # =====  Train Movement Info =====
        movement_frame = ttk.LabelFrame(frame, text="Train Movement Information")
        movement_frame.pack(fill="x", padx=5, pady=5)

        movement_info = [
            ("Commanded Speed", self.status.get("commanded_speed", "N/A")),
            ("Authority", self.status.get("authority", "N/A")),
            ("Beacon", self.status.get("beacon", "N/A")),
            ("Speed Limit", self.status.get("speed_limit", "N/A")),
            ("Velocity", self.status.get("velocity", "N/A")),
            ("Acceleration", self.status.get("acceleration", "N/A")),
            ("Deceleration Limit", f"{self.specs.get('decel_limit_mphps', 'N/A')} mph/s"),
        ]
        for i, (label, value) in enumerate(movement_info):
            lbl = ttk.Label(movement_frame, text=f"{label}: {value}")
            lbl.grid(row=i, column=0, sticky="w", padx=10, pady=3)
            self.labels[label] = lbl

        # =====  Passenger Info =====
        passenger_frame = ttk.LabelFrame(frame, text="Passenger Information")
        passenger_frame.pack(fill="x", padx=5, pady=5)

        boarding = self.status.get("passengers_boarding", 0)
        disembarking = self.status.get("passengers_disembarking", 0)
        onboard = boarding - disembarking
        crew = self.status.get("crew_count", 2)

        passenger_info = [
            ("Passengers Boarding", boarding),
            ("Passengers Disembarking", disembarking),
            ("Passengers Onboard", onboard),
            ("Crew Count", crew)
        ]
        for i, (label, value) in enumerate(passenger_info):
            lbl = ttk.Label(passenger_frame, text=f"{label}: {value}")
            lbl.grid(row=i, column=0, sticky="w", padx=10, pady=3)
            self.labels[label] = lbl

        # =====  Train Specs =====
        specs_frame = ttk.LabelFrame(frame, text="Train Specifications")
        specs_frame.pack(fill="x", padx=5, pady=5)

        specs_info = [
            ("Inside Temperature", f"{self.status.get('temperature_inside', 'N/A')} °C"),
            ("Lights", "ON" if self.status.get("lights_on") else "OFF"),
            ("Doors", "Closed" if self.status.get("doors_closed") else "Open"),
            ("Length", f"{self.specs.get('length_ft', 'N/A')} ft"),
            ("Width", f"{self.specs.get('width_ft', 'N/A')} ft"),
            ("Height", f"{self.specs.get('height_ft', 'N/A')} ft"),
            ("Mass", f"{self.specs.get('mass_lb', 'N/A')} lb")
        ]
        for i, (label, value) in enumerate(specs_info):
            lbl = ttk.Label(specs_frame, text=f"{label}: {value}")
            lbl.grid(row=i, column=0, sticky="w", padx=10, pady=3)
            self.labels[label] = lbl

    # ----------------------------------------------------------------------
    def populate_right(self, frame):
        """Right section: map, failures, and emergency brake."""
        map_frame = ttk.LabelFrame(frame, text="Track Map")
        map_frame.pack(fill="both", expand=True, padx=10, pady=10)

        map_path = "map.png"
        if os.path.exists(map_path):
            img = Image.open(map_path)
            orig_w, orig_h = img.size
            max_w, max_h = 550, 400
            ratio = min(max_w / orig_w, max_h / orig_h)
            new_size = (int(orig_w * ratio), int(orig_h * ratio))
            img = img.resize(new_size, Image.LANCZOS)
            self.map_img = ImageTk.PhotoImage(img)
            ttk.Label(map_frame, image=self.map_img).pack(pady=5)
        else:
            ttk.Label(map_frame, text="Map image not found.").pack(pady=20)

        # === Failures ===
        fail_frame = ttk.LabelFrame(frame, text="Failure Status (Editable)")
        fail_frame.pack(fill="x", padx=10, pady=10)
        self.failure_vars = {}

        for key, val in self.failures.items():
            label = key.replace("_", " ").title()
            var = tk.BooleanVar(value=val)
            self.failure_vars[key] = var
            chk = ttk.Checkbutton(
                fail_frame,
                text=label,
                variable=var,
                command=lambda k=key, v=var: self.toggle_failure(k, v)
            )
            chk.pack(anchor="w")

        # === Emergency Brake ===
        eb_frame = ttk.LabelFrame(frame, text="Emergency Brake")
        eb_frame.pack(fill="x", padx=10, pady=10)
        self.eb_button = ttk.Button(eb_frame, text="ACTIVATE", command=self.activate_emergency)
        self.eb_button.pack(pady=10, ipadx=20, ipady=5)

    # ----------------------------------------------------------------------
    def populate_announcement(self, frame):
        """Bottom section for announcements."""
        self.announcement_box = tk.Text(frame, height=4, width=100)
        self.announcement_box.insert("end", self.status.get("announcement", "No announcements available."))
        self.announcement_box.pack(fill="both", expand=True, padx=10, pady=5)

    # ----------------------------------------------------------------------
    def toggle_failure(self, key, var):
        """Triggered when user toggles a failure checkbox."""
        self.failures[key] = var.get()
        self.save_json()
        print(f"[Updated] {key} -> {self.failures[key]}")

    # ----------------------------------------------------------------------
    def activate_emergency(self):
        """Activate emergency brake and save state."""
        messagebox.showwarning("Emergency Brake", "Emergency Brake Activated!")
        self.status["emergency_brake"] = True
        self.save_json()

    # ----------------------------------------------------------------------
    def refresh_data(self):
        """Reload JSON and update the displayed train information periodically."""
        new_data = self.load_json()
        new_status = new_data.get("train_status", {})
        new_failures = new_data.get("failures", {})

        # Special key mapping for labels that don't convert 1:1 to json keys
        label_key_map = {
            "ETA (min)": "eta_min"
        }

        # Update all dynamic labels
        for label, widget in self.labels.items():
            if label == "Passengers Onboard":
                boarding = new_status.get("passengers_boarding", 0)
                disembarking = new_status.get("passengers_disembarking", 0)
                val = boarding - disembarking
            elif label == "Inside Temperature":
                val = f"{new_status.get('temperature_inside', 'N/A')} °C"
            elif label == "Lights":
                val = "ON" if new_status.get("lights_on") else "OFF"
            elif label == "Doors":
                val = "Closed" if new_status.get("doors_closed") else "Open"
            else:
                # map label -> json key (handles spaces and the ETA special case)
                key = label_key_map.get(label, label.lower().replace(" ", "_"))
                val = new_status.get(key, self.specs.get(key, "N/A"))
            widget.config(text=f"{label}: {val}")

        # Update Failures checkboxes
        for k, v in new_failures.items():
            if k in self.failure_vars:
                self.failure_vars[k].set(v)

        self.after(2000, self.refresh_data)

    # ----------------------------------------------------------------------
    def save_json(self):
        """Save modified data to JSON."""
        try:
            self.data["train_status"] = self.status
            self.data["failures"] = self.failures
            with open("train_data.json", "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print("Error saving JSON:", e)

# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = TrainModelUI()
    app.mainloop()
