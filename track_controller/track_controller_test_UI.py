# Wayside Controller Test UI
# Reformatted to match style of SWTrackControllerUI

import tkinter as tk
from tkinter import ttk, filedialog

WindowWidth = 1200
WindowHeight = 700

class WaysideControllerUI(tk.Tk):

    def __init__(self):
        super().__init__()

        # Window setup
        self.title("Wayside Controller Test UI")
        self.geometry(f"{WindowWidth}x{WindowHeight}")

        # Grid layout
        for i in range(2):
            self.grid_columnconfigure(i, weight=1, uniform="col")
        self.grid_rowconfigure(0, weight=1)

        # ---- Left Frame: Force Input ----
        inputFrame = ttk.LabelFrame(self, text="Force Input")
        inputFrame.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)

        # Input fields
        self.speed_entry = self.make_entry(inputFrame, "Suggested Speed", 0, "22mph")
        self.authority_entry = self.make_entry(inputFrame, "Authority", 1, "Block C1")
        self.track_closures_entry = self.make_entry(inputFrame, "Track Closures", 2, "None")
        self.route_entry = self.make_entry(inputFrame, "Route", 3, "Red")
        self.failure_entry = self.make_entry(inputFrame, "Failure Alerts", 4, "None")
        self.train_positions_entry = self.make_entry(inputFrame, "Train Positions", 5, "Block(s) A1")
        self.passengers_entry = self.make_entry(inputFrame, "Passengers Disembarking", 6, "15")

        ttk.Label(inputFrame, text="Schedule").grid(row=7, column=0, sticky="w", padx=5, pady=5)
        ttk.Button(inputFrame, text="File Upload", command=self.upload_schedule).grid(row=7, column=1, padx=5, pady=5)

        self.switch_entry = self.make_entry(inputFrame, "Switch Positions", 8, "0")

        # Buttons
        ttk.Button(inputFrame, text="Simulate", command=self.simulate).grid(row=9, column=0, pady=10)
        ttk.Button(inputFrame, text="Stop Simulation", command=self.stop_simulation).grid(row=9, column=1, pady=10)

        # ---- Right Frame: Generated Output ----
        outputFrame = ttk.LabelFrame(self, text="Generated Output")
        outputFrame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)

        self.beacon_value = self.make_output(outputFrame, "Beacon", 0)
        self.switch_output = self.make_output(outputFrame, "Switch Positions", 1)
        self.commanded_speed = self.make_output(outputFrame, "Commanded Speed", 2)
        self.authority_output = self.make_output(outputFrame, "Authority", 3)
        self.lights_output = self.make_output(outputFrame, "Lights", 4)
        self.gates_output = self.make_output(outputFrame, "Gates", 5)
        self.state_of_track = self.make_output(outputFrame, "State of Track", 6)
        self.train_positions_output = self.make_output(outputFrame, "Train Positions", 7)
        self.passengers_output = self.make_output(outputFrame, "Passengers Disembarking", 8)

    # --- Utility: make entry row ---
    def make_entry(self, parent, label, row, default=""):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=5)
        entry = ttk.Entry(parent)
        entry.insert(0, default)
        entry.grid(row=row, column=1, padx=5, pady=5)
        return entry

    # --- Utility: make output row ---
    def make_output(self, parent, label, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=5)
        var = tk.StringVar()
        ttk.Label(parent, textvariable=var).grid(row=row, column=1, sticky="w", padx=5, pady=5)
        return var

    # --- Functional logic ---
    def simulate(self):
        suggested_speed = self.speed_entry.get()
        authority = self.authority_entry.get()
        track_closures = self.track_closures_entry.get()
        route = self.route_entry.get()
        failure_alerts = self.failure_entry.get()
        train_positions = self.train_positions_entry.get()
        passengers = self.passengers_entry.get()
        switch_positions = self.switch_entry.get()

        # Example simple logic (expand later)
        self.beacon_value.set("128B")
        self.switch_output.set(switch_positions)
        self.commanded_speed.set(f"{int(suggested_speed.replace('mph','')) - 2}mph")
        self.authority_output.set(authority)
        self.lights_output.set("Green")
        self.gates_output.set("Closed")
        self.state_of_track.set("2 Trains Active")
        self.train_positions_output.set(train_positions)
        self.passengers_output.set(passengers)

    def stop_simulation(self):
        # Reset outputs
        for var in [
            self.beacon_value, self.switch_output, self.commanded_speed,
            self.authority_output, self.lights_output, self.gates_output,
            self.state_of_track, self.train_positions_output, self.passengers_output
        ]:
            var.set("")

    def upload_schedule(self):
        filedialog.askopenfilename(title="Select Schedule File")


if __name__ == "__main__":
    WaysideControllerUI().mainloop()
