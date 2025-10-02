#import tkinter and related libraries
import tkinter as tk
from tkinter import ttk, messagebox


class TrainModelTestUI(tk.Tk):
    def __init__(self):
        super().__init__()

        # Window settings
        self.title("Train Model Test UI")
        self.geometry("600x700")

        # Frame for inputs
        input_frame = ttk.LabelFrame(self, text="Force Input - Track Model")
        input_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Dictionary to hold input widgets
        self.inputs = {}

        # Define parameters: (Label, widget type, default value)
        params = [
            ("Commanded Speed", "entry", "25 mph"),
            ("Authority", "entry", "23 Block#"),
            ("Beacon", "entry", "128 B"),
            ("Speed Limit", "entry", "30 mph"),
            ("Number of Passengers Boarding", "entry", "80"),
            ("Train Positions", "entry", "2 Block#"),
            ("Crew Count", "entry", "2"),
            ("Mass", "entry", "91 lb"),
            ("Length", "entry", "66 ft"),
            ("Width", "entry", "10 ft"),
            ("Height", "entry", "11.5 ft"),
            ("Right Door (Bool)", "combo", "False"),
            ("Left Door (Bool)", "combo", "False"),
            ("Lights (Bool)", "combo", "False"),
            ("Temperature UP (int)", "entry", "3"),
            ("Temperature DOWN (int)", "entry", "0"),
            ("Announcement/Dispatching System (string)", "entry", "Arriving at Herron Ave"),
            ("Service Brake (Driver) (Bool)", "combo", "False"),
            ("Power Availability", "entry", "600 kW"),
            ("Deceleration Limit", "entry", "2.4 mph/s"),
            ("Emergency Brake (Bool)", "combo", "False"),
            ("Train Temperature (int)", "entry", "67"),
            ("Train Engine Failure", "combo", "None"),
            ("Signal Pickup Failure", "combo", "None"),
            ("Brake Failure", "combo", "None"),
        ]

        # Create grid layout for labels and inputs
        for i, (label, widget_type, default) in enumerate(params):
            ttk.Label(input_frame, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=3)

            if widget_type == "entry":
                entry = ttk.Entry(input_frame)
                entry.insert(0, default)
                entry.grid(row=i, column=1, padx=5, pady=3, sticky="ew")
                self.inputs[label] = entry
            elif widget_type == "combo":
                combo = ttk.Combobox(input_frame, values=["True", "False", "None"], state="readonly")
                combo.set(default)
                combo.grid(row=i, column=1, padx=5, pady=3, sticky="ew")
                self.inputs[label] = combo

        # Update button
        update_button = ttk.Button(self, text="Update Inputs", command=self.update_inputs)
        update_button.pack(pady=10)

    def update_inputs(self):
        """Collect all input values and show them in a message box."""
        values = {}
        for label, widget in self.inputs.items():
            if isinstance(widget, ttk.Entry):
                values[label] = widget.get()
            else:
                values[label] = widget.get()

        # Debug output (can be written to JSON later)
        messagebox.showinfo("Updated Inputs", "\n".join([f"{k}: {v}" for k, v in values.items()]))


if __name__ == "__main__":
    app = TrainModelTestUI()
    app.mainloop()
