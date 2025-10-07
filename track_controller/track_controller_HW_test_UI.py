import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json

from track_controller_HW_UI import HWTrackControllerUI

WindowWidth = 900
WindowHeight = 600


class TestUI(tk.Frame):

    def __init__(self, master):

        super().__init__(master)
        self.master = master
        self.grid(sticky="NSEW")

        # Input frame
        self.build_input_frame()

        # Output frame
        self.build_output_frame()

    def build_input_frame(self):

        input_frame = ttk.LabelFrame(self, text="Force Input (HW)")
        input_frame.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)

        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_columnconfigure(1, weight=1)

        # Input entries
        self.speed_var = tk.StringVar(value="0")
        self.authority_var = tk.StringVar(value="0")
        self.destination_var = tk.StringVar(value="")
        self.block_occupancies_var = tk.StringVar(value="[]")

        # Add emergency toggle (can be used to force HW emergency state)
        self.emergency_var = tk.BooleanVar(value=False)

        row = 0
        ttk.Label(input_frame, text="Suggested Speed (mph)").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.speed_var).grid(row=row, column=1, pady=2)

        row += 1
        ttk.Label(input_frame, text="Authority (ft)").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.authority_var).grid(row=row, column=1, pady=2)

        row += 1
        ttk.Label(input_frame, text="Destination").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.destination_var).grid(row=row, column=1, pady=2)

        row += 1
        ttk.Label(input_frame, text="Block Occupancies (list)").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.block_occupancies_var).grid(row=row, column=1, pady=2)

        row += 1
        ttk.Checkbutton(input_frame, text="Emergency", variable=self.emergency_var).grid(row=row, column=0, pady=6)

        # Buttons
        ttk.Button(input_frame, text="Auto Simulate", command=self.simulate).grid(row=row, column=1, pady=10)
        self.check_pause = tk.BooleanVar(value=False)
        ttk.Checkbutton(input_frame, text="Pause", variable=self.check_pause, command=self.pause_function).grid(row=row, column=2, pady=10)

    def build_output_frame(self):

        output_frame = ttk.LabelFrame(self, text="Generated Output (HW)")
        output_frame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)

        output_frame.grid_columnconfigure(0, weight=1)
        output_frame.grid_columnconfigure(1, weight=1)

        #initialize output variables
        self.commanded_speed_var = tk.StringVar(value="N/A")
        self.commanded_authority_var = tk.StringVar(value="N/A")
        self.output_gate_states = tk.StringVar(value="N/A")
        self.output_light_states = tk.StringVar(value="N/A")
        self.output_emergency = tk.StringVar(value="N/A")

        labels = [
            ("Commanded Speed (mph):", self.commanded_speed_var),
            ("Commanded Authority (ft):", self.commanded_authority_var),
            ("Gate States:", self.output_gate_states),
            ("Light States:", self.output_light_states),
            ("Emergency:", self.output_emergency),
        ]

        for i, (text, var) in enumerate(labels):
            ttk.Label(output_frame, text=text).grid(row=i, column=0, sticky="W", padx=10, pady=5)
            ttk.Label(output_frame, textvariable=var).grid(row=i, column=1, sticky="W", padx=10, pady=5)
        
    def simulate(self):

        speed = int(self.speed_var.get()) if self.speed_var.get().isdigit() else 0
        authority = int(self.authority_var.get()) if self.authority_var.get().isdigit() else 0
        destination = int(self.destination_var.get()) if self.destination_var.get().isdigit() else 0
        try:
            block_occupancies = json.loads(self.block_occupancies_var.get())
        except:
            block_occupancies = []

        # Save inputs JSON (HW UI will read this)
        data = {
            "suggested_speed": speed,
            "suggested_authority": authority,
            "destination": destination,
            "block_occupancies": block_occupancies,
            "emergency": bool(self.emergency_var.get())
        }

        with open("WaysideInputs_testUI.json", "w") as f:
            json.dump(data, f, indent=2)

        self.update_outputs()
        if not self.check_pause.get():
            self.after(500, self.simulate)

    def update_outputs(self):
        # Read HW outputs JSON
        try:
            with open("WaysideOutputs_testUI.json", "r") as f:
                outputs = json.load(f)
        except Exception:
            outputs = {}

        # Update output labels
        self.commanded_speed_var.set(outputs.get("commanded_speed", "N/A"))
        self.commanded_authority_var.set(outputs.get("commanded_authority", "N/A"))

        gate_str = ", ".join(f"{k}:{v}" for k, v in outputs.get("crossings", {}).items())
        light_str = ", ".join(f"{k}:{v}" for k, v in outputs.get("lights", {}).items())

        self.output_gate_states.set(gate_str if gate_str else "N/A")
        self.output_light_states.set(light_str if light_str else "N/A")
        self.output_emergency.set("ACTIVE" if outputs.get("emergency") else "OFF")

    def pause_function(self):
        if self.check_pause.get():
            self.after(100, self.pause_function)