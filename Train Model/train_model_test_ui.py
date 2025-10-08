import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys


class TrainModelTestUI(tk.Tk):
    def __init__(self):
        super().__init__()

        # === Window settings ===
        self.title("Train Model Test UI")
        self.geometry("1050x700")

        # === Main layout ===
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        # === LEFT: Input Frame ===
        input_frame = ttk.LabelFrame(self, text="Inputs - Train Model")
        input_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        input_frame.columnconfigure(1, weight=1)

        self.inputs = {}

        params = [
            ("Commanded Speed", "25 mph"),
            ("Authority", "23 Block#"),
            ("Beacon", "128 B"),
            ("Speed Limit", "30 mph"),
            ("Passengers Boarding", "80"),
            ("Train Position", "2 Block#"),
            ("Crew Count", "2"),
            ("Mass", "91 lb"),
            ("Length", "66 ft"),
            ("Width", "10 ft"),
            ("Height", "11.5 ft"),
            ("Right Door (Bool)", "False"),
            ("Left Door (Bool)", "False"),
            ("Lights (Bool)", "True"),
            ("Temperature (°F)", "67"),
            ("Announcement", "Arriving at Herron Ave"),
            ("Service Brake (Bool)", "False"),
            ("Emergency Brake (Bool)", "False"),
            ("Power Availability", "600 kW"),
            ("Deceleration Limit", "2.4 mph/s"),
            ("Engine Failure", "None"),
            ("Signal Pickup Failure", "None"),
            ("Brake Failure", "None"),
        ]

        for i, (label, default) in enumerate(params):
            ttk.Label(input_frame, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=3)
            entry = ttk.Entry(input_frame)
            entry.insert(0, default)
            entry.grid(row=i, column=1, sticky="ew", padx=5, pady=3)
            self.inputs[label] = entry

        # === RIGHT: Output Frame ===
        output_frame = ttk.LabelFrame(self, text="Outputs - Train Model")
        output_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        output_frame.columnconfigure(1, weight=1)

        self.outputs = {}

        outputs = [
            ("Commanded Speed", ""),
            ("Commanded Authority", ""),
            ("Beacon", ""),
            ("Failure Modes", ""),
            ("Train Velocity", ""),
            ("Train Temperature", ""),
            ("Speed Limit", ""),
            ("Passengers Boarding", ""),
            ("Passengers Disembarking", "")
        ]

        for i, (label, default) in enumerate(outputs):
            ttk.Label(output_frame, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=3)
            entry = ttk.Entry(output_frame, state="readonly")
            entry.grid(row=i, column=1, padx=5, pady=3, sticky="ew")
            self.outputs[label] = entry

        # === BOTTOM: Control Buttons ===
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=15)

        ttk.Button(btn_frame, text="Update Inputs", command=self.update_inputs).grid(row=0, column=0, padx=10)
        ttk.Button(btn_frame, text="Simulate Outputs", command=self.simulate_outputs).grid(row=0, column=1, padx=10)
        ttk.Button(btn_frame, text="Open Train Model UI", command=self.open_main_ui).grid(row=0, column=2, padx=10)

    # === Collect and show inputs ===
    def update_inputs(self):
        values = {label: widget.get() for label, widget in self.inputs.items()}
        msg = "\n".join([f"{k}: {v}" for k, v in values.items()])
        messagebox.showinfo("Updated Inputs", msg)

    # === Dummy output simulation ===
    def simulate_outputs(self):
        """Generate fake test outputs (for demonstration)."""
        test_values = {
            "Commanded Speed": "25 mph",
            "Commanded Authority": "23 Block#",
            "Beacon": "128 B",
            "Failure Modes": "None",
            "Train Velocity": "24 mph",
            "Train Temperature": "67 °F",
            "Speed Limit": "30 mph",
            "Passengers Boarding": "80",
            "Passengers Disembarking": "3"
        }
        for key, val in test_values.items():
            widget = self.outputs[key]
            widget.config(state="normal")
            widget.delete(0, tk.END)
            widget.insert(0, val)
            widget.config(state="readonly")

    # === Launch main UI ===
    def open_main_ui(self):
        try:
            subprocess.Popen([sys.executable, "train_model_ui.py"])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open Train Model UI.\n{e}")


if __name__ == "__main__":
    app = TrainModelTestUI()
    app.mainloop()
