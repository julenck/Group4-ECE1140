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
        self.geometry("1200x800")
        os.chdir(os.path.dirname(os.path.abspath(__file__)))  # Ensure working directory is correct

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

        # === LEFT SIDE: Train info and environment ===
        left_frame = ttk.LabelFrame(self, text="Train Information & Environment")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.populate_left(left_frame)

        # === RIGHT SIDE: Map display, failure control, and emergency brake ===
        right_frame = ttk.LabelFrame(self, text="Map, Failures & Control")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.populate_right(right_frame)

        # === BOTTOM: Announcements display ===
        announce_frame = ttk.LabelFrame(self, text="Announcements")
        announce_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        self.populate_announcement(announce_frame)

        # === Automatically refresh UI every 2 seconds ===
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
        """Left section: displays train status, passengers, and specs."""
        self.labels = {}

        # Calculate passengers onboard (boarding - disembarking)
        onboard = self.status.get("passengers_boarding", 0) - self.status.get("passengers_disembarking", 0)
        crew = self.status.get("crew_count", 2)

        # List of key parameters to display
        info = [
            ("Current Station", self.status.get("current_station", "N/A")),
            ("Next Station", self.status.get("next_station", "N/A")),
            ("ETA (min)", self.status.get("eta_min", "N/A")),
            ("Commanded Speed", self.status.get("commanded_speed", "N/A")),
            ("Authority", self.status.get("authority", "N/A")),
            ("Beacon", self.status.get("beacon", "N/A")),
            ("Speed Limit", self.status.get("speed_limit", "N/A")),
            ("Passengers Onboard", onboard),
            ("Crew Count", crew),
            ("Inside Temperature", f"{self.status.get('temperature_inside', 'N/A')} °C"),
            ("Lights", "ON" if self.status.get("lights_on") else "OFF"),
            ("Doors", "Closed" if self.status.get("doors_closed") else "Open"),
            ("Length", f"{self.specs.get('length_ft', 'N/A')} ft"),
            ("Width", f"{self.specs.get('width_ft', 'N/A')} ft"),
            ("Height", f"{self.specs.get('height_ft', 'N/A')} ft"),
            ("Mass", f"{self.specs.get('mass_lb', 'N/A')} lb")
        ]

        # Dynamically create label widgets
        for i, (label, value) in enumerate(info):
            lbl = ttk.Label(frame, text=f"{label}: {value}")
            lbl.grid(row=i, column=0, sticky="w", padx=10, pady=3)
            self.labels[label] = lbl

    # ----------------------------------------------------------------------
    def populate_right(self, frame):
        """Right section: track map, interactive failure toggles, and emergency brake button."""
        # === Display map image ===
        map_frame = ttk.LabelFrame(frame, text="Track Map")
        map_frame.pack(fill="both", expand=True, padx=10, pady=10)
        map_path = "map.png"
        if os.path.exists(map_path):
           img = Image.open(map_path)

        # Get original dimensions
           orig_width, orig_height = img.size

        # Define max width and height for display
           max_width, max_height = 550, 400

        # Compute aspect ratio scaling
           ratio = min(max_width / orig_width, max_height / orig_height)
           new_size = (int(orig_width * ratio), int(orig_height * ratio))

        # Resize with preserved ratio
           img = img.resize(new_size, Image.LANCZOS)

           self.map_img = ImageTk.PhotoImage(img)
           map_label = ttk.Label(map_frame, image=self.map_img)
           map_label.pack(pady=5)
        else:
           ttk.Label(map_frame, text="Map image not found.").pack(pady=20)

        # === Interactive failure controls ===
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

        # === Emergency brake control ===
        eb_frame = ttk.LabelFrame(frame, text="Emergency Brake")
        eb_frame.pack(fill="x", padx=10, pady=10)
        self.eb_button = ttk.Button(eb_frame, text="ACTIVATE", command=self.activate_emergency)
        self.eb_button.pack(pady=10, ipadx=20, ipady=5)

    # ----------------------------------------------------------------------
    def populate_announcement(self, frame):
        """Bottom section: text box for public announcements."""
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
        """Activate the emergency brake and save state."""
        messagebox.showwarning("Emergency Brake", "Emergency Brake Activated!")
        self.status["emergency_brake"] = True
        self.save_json()

    # ----------------------------------------------------------------------
    def refresh_data(self):
        """Reload JSON and update the displayed train information periodically."""
        new_data = self.load_json()
        new_status = new_data.get("train_status", {})
        new_failures = new_data.get("failures", {})

        # Update label values dynamically
        for label, widget in self.labels.items():
            if label in ["Commanded Speed", "Speed Limit", "Authority", "Beacon"]:
                widget.config(text=f"{label}: {new_status.get(label.lower().replace(' ', '_'), 'N/A')}")
            elif label == "Inside Temperature":
                widget.config(text=f"Inside Temperature: {new_status.get('temperature_inside', 'N/A')} °C")
            elif label == "Lights":
                widget.config(text=f"Lights: {'ON' if new_status.get('lights_on') else 'OFF'}")
            elif label == "Doors":
                widget.config(text=f"Doors: {'Closed' if new_status.get('doors_closed') else 'Open'}")

        # Update Failure checkboxes
        for k, v in new_failures.items():
            if k in self.failure_vars:
                self.failure_vars[k].set(v)

        # Re-run this method every 2 seconds
        self.after(2000, self.refresh_data)

    # ----------------------------------------------------------------------
    def save_json(self):
        """Save all modified data (e.g., failures or emergency brake) to JSON."""
        try:
            self.data["train_status"] = self.status
            self.data["failures"] = self.failures
            with open("train_data.json", "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print("Error saving JSON:", e)


if __name__ == "__main__":
    app = TrainModelUI()
    app.mainloop()
