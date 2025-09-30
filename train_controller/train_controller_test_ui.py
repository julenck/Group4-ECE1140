# Train Controller Test UI
# Reformatted to match style of train_controller_sw_ui

from email.policy import default
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os


# variables for window size
window_width = 1200
window_height = 700

class train_controller_test_ui(tk.Tk):

    def __init__(self):
        super().__init__()#initialize the tk.Tk class

        # Window Setup
        self.title("Train Controller Test UI")
        self.geometry(f"{window_width}x{window_height}")
        
        # Grid layout
        for i in range(2):
            self.grid_columnconfigure(i, weight=1, uniform="col")
        self.grid_rowconfigure(0, weight=1)

         # ---- Left Frame: Force Input ----
        inputFrame = ttk.LabelFrame(self, text="Force Input")
        inputFrame.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)

        # Input fields
        # The last column should be variables which are values that change the json file
        self.commanded_speed_entry = self.make_entry_text(inputFrame, "Commanded Speed (mph)", 0, "25") 
        self.set_speed_entry = self.make_entry_text(inputFrame, "Set Speed (mph)", 1, "23")
        self.speed_limit_entry = self.make_entry_text(inputFrame, "Speed Limit (mph)", 2, "30")
        self.commanded_authority_entry = self.make_entry_text(inputFrame, "Commanded Authority (yds)", 3, "123")
        self.train_velocity_entry = self.make_entry_text(inputFrame, "Train Velocity (mph)", 4, "30")
        self.next_stop_beacon_entry = self.make_entry_text(inputFrame, "Next Stop", 5, "Herron Ave")
        self.station_side_beacon_entry = self.make_entry_dropdown(inputFrame, "Station Side (left/right)", 6, ["left", "right"])
        self.service_brake_entry = self.make_entry_text(inputFrame, "Service Brake (%)", 7, "30%")
        self.emergency_brake_entry = self.make_entry_dropdown(inputFrame, "Emergency Brake (on/off)", 8, ["on", "off"], "off")
        self.train_engine_failure_entry = self.make_entry_dropdown(inputFrame, "Train Engine Failure", 9, ["True", "False"], "False")
        self.signal_pickup_failure_entry = self.make_entry_dropdown(inputFrame, "Signal Pickup Failure", 10, ["True", "False"], "False")
        self.brake_failure_entry = self.make_entry_dropdown(inputFrame, "Brake Failure", 11, ["True", "False"], "False")



        # Buttons
        ttk.Button(inputFrame, text="Simulate").grid(row=12, column=0, pady=10)


    def make_entry_text(self, parent, label, row, default=""):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=5)
        entry = ttk.Entry(parent)
        entry.insert(0, default)
        entry.grid(row=row, column=1, padx=5, pady=5)
        return entry
    
    def make_entry_dropdown(self, parent, label, row, values, default=None):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=5)
        combo = ttk.Combobox(parent, values=values, state="readonly")
        if default is not None:
            combo.set(default)
        combo.grid(row=row, column=1, padx=5, pady=5)
        return combo

    # --- Utility: make output row ---
    def make_output(self, parent, label, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=5)
        var = tk.StringVar()
        ttk.Label(parent, textvariable=var).grid(row=row, column=1, sticky="w", padx=5, pady=5)
        return var
    
    


if __name__ == "__main__":
    train_controller_test_ui().mainloop()

