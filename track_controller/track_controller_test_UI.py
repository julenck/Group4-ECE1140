# test_UI.py
# Wayside Controller Test UI (JSON Save Only)

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json

WindowWidth = 900
WindowHeight = 600


class TestUI(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.grid(sticky="NSEW")

        # Configure root grid scaling
        for i in range(2):
            master.grid_columnconfigure(i, weight=1, uniform="col")
        master.grid_rowconfigure(0, weight=1)

        # Input frame
        self.build_input_frame()

        # Output frame
        self.build_output_frame()

    def build_input_frame(self):
        input_frame = ttk.LabelFrame(self, text="Force Input")
        input_frame.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)

        # Input entries
        self.speed_var = tk.StringVar(value="22")
        self.authority_var = tk.StringVar(value="300")
        self.closures_var = tk.StringVar(value="None")
        self.route_var = tk.StringVar(value="Red")
        self.failure_var = tk.StringVar(value="None")
        self.train_positions_var = tk.StringVar(value="Block(s) A1")
        self.passengers_var = tk.StringVar(value="15")
        self.switch_var = tk.StringVar(value="Straight")

        row = 0
        ttk.Label(input_frame, text="Suggested Speed (mph)").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.speed_var).grid(row=row, column=1, pady=2)

        row += 1
        ttk.Label(input_frame, text="Authority (ft)").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.authority_var).grid(row=row, column=1, pady=2)

        row += 1
        ttk.Label(input_frame, text="Track Closures").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.closures_var).grid(row=row, column=1, pady=2)

        row += 1
        ttk.Label(input_frame, text="Route").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.route_var).grid(row=row, column=1, pady=2)

        row += 1
        ttk.Label(input_frame, text="Failure Alerts").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.failure_var).grid(row=row, column=1, pady=2)

        row += 1
        ttk.Label(input_frame, text="Train Positions").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.train_positions_var).grid(row=row, column=1, pady=2)

        row += 1
        ttk.Label(input_frame, text="Passengers Disembarking").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.passengers_var).grid(row=row, column=1, pady=2)

        row += 1
        ttk.Label(input_frame, text="Switch Position").grid(row=row, column=0, sticky="W")
        ttk.Combobox(input_frame, textvariable=self.switch_var, values=["Straight", "Diverging"], state="readonly").grid(
            row=row, column=1, pady=2
        )

        # Buttons
        row += 1
        ttk.Button(input_frame, text="Simulate", command=self.simulate).grid(row=row, column=0, pady=10)
        ttk.Button(input_frame, text="Stop Simulation", command=self.stop_simulation).grid(row=row, column=1, pady=10)

    def build_output_frame(self):
        output_frame = ttk.LabelFrame(self, text="Generated Output")
        output_frame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)

        self.output_vars = {}

        def make_output(label, row):
            ttk.Label(output_frame, text=label).grid(row=row, column=0, sticky="W")
            var = tk.StringVar()
            ttk.Label(output_frame, textvariable=var).grid(row=row, column=1, sticky="W")
            self.output_vars[label] = var

        make_output("Beacon", 0)
        make_output("Switch Positions", 1)
        make_output("Commanded Speed", 2)
        make_output("Authority", 3)
        make_output("Lights", 4)
        make_output("Gates", 5)
        make_output("State of Track", 6)
        make_output("Train Positions", 7)
        make_output("Passengers Disembarking", 8)

    def simulate(self):
        # Grab inputs
        speed = self.speed_var.get()
        authority = self.authority_var.get()
        passengers = self.passengers_var.get()
        switch_state = self.switch_var.get()

        # Simple logic for outputs
        self.output_vars["Beacon"].set("128B")
        self.output_vars["Switch Positions"].set(switch_state)
        try:
            cmd_speed = f"{int(speed) - 2} mph"
        except ValueError:
            cmd_speed = "Invalid"
        self.output_vars["Commanded Speed"].set(cmd_speed)
        self.output_vars["Authority"].set(authority)
        self.output_vars["Lights"].set("Green")
        self.output_vars["Gates"].set("Closed")
        self.output_vars["State of Track"].set("2 Trains Active")
        self.output_vars["Train Positions"].set(self.train_positions_var.get())
        self.output_vars["Passengers Disembarking"].set(passengers)

        # Save to JSON
        data = {
            "switches": ["SW1", "switch2", "sw3", "S5", "switch6"],
            "switch_states": [switch_state],  # can be extended if multiple
            "suggested_speed": int(speed) if speed.isdigit() else 0,
            "suggested_authority": int(authority) if authority.isdigit() else 0,
            "passengers_disembarking": int(passengers) if passengers.isdigit() else 0,
        }

        with open("WaysideInputs_test_UI.json", "w") as f:
            json.dump(data, f, indent=2)

    def stop_simulation(self):
        for var in self.output_vars.values():
            var.set("")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Wayside Controller Test UI")
    root.geometry(f"{WindowWidth}x{WindowHeight}")
    TestUI(root)
    root.mainloop()
