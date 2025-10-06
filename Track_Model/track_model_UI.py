import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import json
import os

class TrackBuilderUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Track Builder - Interface")
        self.geometry("1200x700")

        # Load JSON data
        ase_path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_path, "track_data.json")

        # Grid layout
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        # Left - Track Layout
        map_frame = ttk.LabelFrame(self, text="Track Layout Interactive Diagram")
        map_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.map_canvas = tk.Canvas(map_frame, bg="white")
        self.map_canvas.pack(fill="both", expand=True)

        # Load diagram image from folder
        if os.path.exists("Track.png"):
            img = Image.open("Track.png")
            img = img.resize((500, 500), Image.ANTIALIAS)
            self.map_img = ImageTk.PhotoImage(img)
            self.map_canvas.create_image(0, 0, anchor="nw", image=self.map_img)

        # Right - Block Details
        details_frame = ttk.LabelFrame(self, text=f"Currently Selected Block - {self.data['block']['name']}")
        details_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # Block Information
        info = ttk.LabelFrame(details_frame, text="Block Information")
        info.pack(fill="x", padx=5, pady=5)
        ttk.Label(info, text=f"Direction of Travel: {self.data['block']['direction']}").pack(anchor="w")
        ttk.Label(info, text=f"Traffic Light: {self.data['block']['traffic_light']}").pack(anchor="w")
        ttk.Label(info, text=f"Speed Limit: {self.data['block']['speed_limit']} mph").pack(anchor="w")
        ttk.Label(info, text=f"Switch: {self.data['block']['switch']}").pack(anchor="w")
        ttk.Label(info, text=f"Grade: {self.data['block']['grade']}%").pack(anchor="w")
        ttk.Label(info, text=f"Crossing: {self.data['block']['crossing']}").pack(anchor="w")
        ttk.Label(info, text=f"Station/Side: {self.data['block']['station_side']}").pack(anchor="w")
        ttk.Label(info, text=f"Branching: {self.data['block']['branching']}").pack(anchor="w")
        ttk.Label(info, text=f"Beacon: {self.data['block']['beacon']}").pack(anchor="w")
        ttk.Label(info, text=f"Elevation: {self.data['block']['elevation']} ft").pack(anchor="w")

        # Train Presence + Heating
        presence_frame = ttk.Frame(details_frame)
        presence_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(presence_frame, text=f"Train Presence On: {self.data['block']['name']}").pack(side="left")
        self.track_heating = tk.BooleanVar(value=self.data['block']['track_heating'])
        ttk.Checkbutton(presence_frame, text="Track Heating", variable=self.track_heating, state="disabled").pack(side="right")

        # Temperature (editable, with validation)
        temp_frame = ttk.Frame(details_frame)
        temp_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(temp_frame, text="Environment Temperature (°F):").pack(side="left")
        self.temp_var = tk.IntVar(value=self.data['environment']['temperature'])
        self.temp_spin = tk.Spinbox(temp_frame, from_=-20, to=120, textvariable=self.temp_var,
                                    command=self.validate_temperature)
        self.temp_spin.pack(side="left")

        # Upload Track Layout
        ttk.Button(details_frame, text="Upload Track Layout File").pack(pady=5)

        # Totals
        totals = ttk.LabelFrame(details_frame, text="Totals")
        totals.pack(fill="x", padx=5, pady=5)
        ttk.Label(totals, text=f"Total Blocks - Green Line: {self.data['totals']['green']}").pack(anchor="w")
        ttk.Label(totals, text=f"Total Blocks - Red Line: {self.data['totals']['red']}").pack(anchor="w")
        ttk.Label(totals, text=f"Total Blocks - Combined: {self.data['totals']['combined']}").pack(anchor="w")

        # Failure Status (editable)
        failures = ttk.LabelFrame(details_frame, text="Failure Status")
        failures.pack(fill="x", padx=5, pady=5)
        self.power_fail = tk.BooleanVar(value=self.data['failures']['power'])
        self.circuit_fail = tk.BooleanVar(value=self.data['failures']['circuit'])
        self.broken_track = tk.BooleanVar(value=self.data['failures']['broken_track'])
        ttk.Checkbutton(failures, text="Power Failure", variable=self.power_fail).pack(anchor="w")
        ttk.Checkbutton(failures, text="Circuit Failure", variable=self.circuit_fail).pack(anchor="w")
        ttk.Checkbutton(failures, text="Broken Track", variable=self.broken_track).pack(anchor="w")

        # Station Info
        station = ttk.LabelFrame(details_frame, text="Station Information")
        station.pack(fill="x", padx=5, pady=5)
        ttk.Label(station, text=f"Ticket Sales: {self.data['station']['ticket_sales']}").pack(anchor="w")
        ttk.Label(station, text=f"Boarding: {self.data['station']['boarding']}").pack(anchor="w")
        ttk.Label(station, text=f"Disembarking: {self.data['station']['disembarking']}").pack(anchor="w")
        ttk.Label(station, text=f"Train Occupancy: {self.data['station']['occupancy']}").pack(anchor="w")

    def validate_temperature(self):
        val = self.temp_var.get()
        if val < -20 or val > 120:
            messagebox.showerror("Invalid Temperature", "Temperature must be between -20°F and 120°F.")
            self.temp_var.set(self.data['environment']['temperature'])

    def load_json(self):
        # Example JSON file loader
        if os.path.exists("track_data.json"):
            with open("track_data.json", "r") as f:
                return json.load(f)
        else:
            return {}

if __name__ == "__main__":
    app = TrackBuilderUI()
    app.mainloop()
