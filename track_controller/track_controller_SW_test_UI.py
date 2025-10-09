import tkinter as tk
from tkinter import ttk
import json

WindowWidth = 650
WindowHeight = 250

class TestUI(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.grid(sticky="NSEW")

        self.build_input_frame()
        self.build_output_frame()

    def build_input_frame(self):
        input_frame = ttk.LabelFrame(self, text="Force Input")
        input_frame.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)

        # --- Input Variables ---
        self.speed_var = tk.StringVar(value="0")
        self.authority_var = tk.StringVar(value="0")
        self.destination_var = tk.StringVar(value="")
        self.block_occupancies_var = tk.StringVar(value="[]")
        self.failure_signal_input_var = tk.StringVar(value="0")

        # --- Input Widgets ---
        row = 0
        ttk.Label(input_frame, text="Suggested Speed (mph)").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.speed_var).grid(row=row, column=1, pady=2)

        row += 1
        ttk.Label(input_frame, text="Suggested Authority (yds)").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.authority_var).grid(row=row, column=1, pady=2)

        row += 1
        ttk.Label(input_frame, text="Destination").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.destination_var).grid(row=row, column=1, pady=2)

        row += 1
        ttk.Label(input_frame, text="Block Occupancies (list)").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.block_occupancies_var).grid(row=row, column=1, pady=2)

        row += 1
        ttk.Label(input_frame, text="Failure Signal:").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.failure_signal_input_var).grid(row=row, column=1, pady=2)

        # Buttons
        row += 1
        ttk.Button(input_frame, text="Auto Simulate", command=self.simulate).grid(row=row, column=0, pady=10)

        self.check_pause = tk.BooleanVar(value=False)
        ttk.Checkbutton(input_frame, text="Pause", variable=self.check_pause, command=self.pause_function).grid(row=row, column=1, pady=10)

    def build_output_frame(self):
        output_frame = ttk.LabelFrame(self, text="Generated Output")
        output_frame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)

        # --- Output Variables ---
        self.commanded_speed_var = tk.StringVar(value="N/A")
        self.commanded_authority_var = tk.StringVar(value="N/A")
        self.output_switch_states = tk.StringVar(value="N/A")
        self.output_gate_states = tk.StringVar(value="N/A")
        self.output_light_states = tk.StringVar(value="N/A")
        self.failure_signal_var = tk.StringVar(value="N/A")

        # --- Output Widgets ---
        labels = [
            ("Commanded Speed (mph):", self.commanded_speed_var),
            ("Commanded Authority (yds):", self.commanded_authority_var),
            ("Switch States:", self.output_switch_states),
            ("Gate States:", self.output_gate_states),
            ("Light States:", self.output_light_states),
            ("Failure Signal:", self.failure_signal_var)
        ]

        for i, (text, var) in enumerate(labels):
            ttk.Label(output_frame, text=text).grid(row=i, column=0, sticky="W", padx=10, pady=5)
            ttk.Label(output_frame, textvariable=var).grid(row=i, column=1, sticky="W", padx=10, pady=5)

    def simulate(self):
        # Grab inputs
        speed = int(self.speed_var.get()) if self.speed_var.get().isdigit() else 0
        authority = int(self.authority_var.get()) if self.authority_var.get().isdigit() else 0
        destination = self.destination_var.get()
        fail_sig = int(self.failure_signal_input_var.get()) if self.failure_signal_input_var.get().isdigit() else 0
        try:
            block_occupancies = json.loads(self.block_occupancies_var.get())
        except:
            block_occupancies = []

        # Save inputs JSON
        data = {
            "suggested_speed": speed,
            "suggested_authority": authority,
            "destination": int(destination),
            "block_occupancies": block_occupancies,
            "failure_signal": fail_sig
        }

        with open("WaysideInputsTestUISW.json", "w") as f:
            json.dump(data, f, indent=2)

        self.update_outputs()
        if not self.check_pause.get():
            self.after(500, self.simulate)

    def update_outputs(self):
        # Read outputs JSON
        with open("WaysideOutputs_testUISW.json", "r") as f:
            outputs = json.load(f)

        # Update output labels
        self.commanded_speed_var.set(outputs.get("commanded_speed", "N/A"))
        self.commanded_authority_var.set(outputs.get("commanded_authority", "N/A"))

        self.output_switch_states.set(str(outputs.get("switches", {})))
        self.output_gate_states.set(str(outputs.get("crossings", {})))
        self.output_light_states.set(str(outputs.get("lights", {})))
        self.failure_signal_var.set(str(outputs.get("failure_signal", "0")))

    def pause_function(self):
        if self.check_pause.get():
            self.after(100, self.pause_function)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Test UI")
    root.geometry(f"{WindowWidth}x{WindowHeight}")
    app = TestUI(root)
    root.mainloop()
