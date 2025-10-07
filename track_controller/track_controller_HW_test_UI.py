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

        input_frame = ttk.LabelFrame(self, text="Force Input")
        input_frame.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)

        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_columnconfigure(1, weight=1)

        # Input entries
        self.speed_var = tk.StringVar(value="0")
        self.authority_var = tk.StringVar(value="0")
        self.closures_var = tk.StringVar(value="none")
        self.route_var = tk.StringVar(value="N/A")
        self.failure_var = tk.StringVar(value="none")
        self.train_positions_var = tk.StringVar(value="none")
        self.passengers_var = tk.StringVar(value="0")
        self.switch_name_var = tk.StringVar(value="SW1,SW2,SW3,SW4")
        self.switch_pos_var = tk.StringVar(value="S,S,D,S")  # S=Straight, D=Diverging

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
        ttk.Label(input_frame, text="Switch Names (comma-separated)").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.switch_name_var).grid(row=row, column=1, pady=2)

        row += 1
        ttk.Label(input_frame, text="Switch Positions (S/D, comma-separated)").grid(row=row, column=0, sticky="W")
        ttk.Entry(input_frame, textvariable=self.switch_pos_var).grid(row=row, column=1, pady=2
        )

        # Buttons
        row += 1
        #self.simulate_var = tk.BooleanVar(value=False)
        ttk.Button(input_frame, text="Auto Simulate", command=self.simulate).grid(row=row, column=0, pady=10)

        self.check_pause = tk.BooleanVar(value=False)
        ttk.Checkbutton(input_frame, text="Pause", variable=self.check_pause, command=self.pause_function).grid(row=row, column=1, pady=10)

        
    
    def build_output_frame(self):

        output_frame = ttk.LabelFrame(self, text="Generated Output")
        output_frame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)

        output_frame.grid_columnconfigure(0, weight=1)
        output_frame.grid_columnconfigure(1, weight=1)

        
        #initialize output variables
        self.output_switch_names = tk.StringVar(value="N/A")
        self.output_switch_positions = tk.StringVar(value="N/A")
        self.commanded_speed_var = tk.StringVar(value="N/A")
        self.commanded_authority_var = tk.StringVar(value="N/A")
        self.passengers_disembarking_var = tk.StringVar(value="N/A")

        # display commanded speed
        commanded_speed_label = ttk.Label(output_frame, text="Commanded Speed (mph): ")
        commanded_speed_label.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)
        commanded_speed_value = ttk.Label(output_frame, textvariable=self.commanded_speed_var)
        commanded_speed_value.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)

        # display commanded authority
        commanded_authority_label = ttk.Label(output_frame, text="Commanded Authority (ft): ")
        commanded_authority_label.grid(row=1, column=0, sticky="NSEW", padx=10, pady=10)
        commanded_authority_value = ttk.Label(output_frame, textvariable=self.commanded_authority_var)
        commanded_authority_value.grid(row=1, column=1, sticky="NSEW", padx=10, pady=10)

        # display passengers disembarking
        passengers_disembarking_label = ttk.Label(output_frame, text="Passengers Disembarking: ")
        passengers_disembarking_label.grid(row=4, column=0, sticky="NSEW", padx=10, pady=10)
        passengers_disembarking_value = ttk.Label(output_frame, textvariable=self.passengers_disembarking_var)
        passengers_disembarking_value.grid(row=4, column=1, sticky="NSEW", padx=10, pady=10)

        # display switch names
        switch_names_label = ttk.Label(output_frame, text="Switch Names: ")
        switch_names_label.grid(row=2, column=0, sticky="NSEW", padx=10, pady=10)
        switch_names_value = ttk.Label(output_frame, textvariable=self.output_switch_names)
        switch_names_value.grid(row=2, column=1, sticky="NSEW", padx=10, pady=10)

        # display switch positions
        switch_positions_label = ttk.Label(output_frame, text="Switch Positions: ")
        switch_positions_label.grid(row=3, column=0, sticky="NSEW", padx=10, pady=10)
        switch_positions_value = ttk.Label(output_frame, textvariable=self.output_switch_positions)
        switch_positions_value.grid(row=3, column=1, sticky="NSEW", padx=10, pady=10)

        

        

    def simulate(self):

        # Grab inputs
        speed = self.speed_var.get()
        authority = self.authority_var.get()
        passengers = self.passengers_var.get()
        switch_state = self.switch_pos_var.get()
        switch_names = self.switch_name_var.get()

        #separate switch names and states
        switch_names_list = switch_names.split(",")
        switch_state_split = switch_state.split(",")

        switch_state_list = []
        for i in range(len(switch_state_split)):

            if switch_state_split[i].upper() == "S":

                switch_state_list.append("Straight")

            elif switch_state_split[i].upper() == "D":

                switch_state_list.append("Diverging")

            else:

                switch_state_list.append("Straight")  # Default to Straight if invalid


        # Save to JSON
        data = {
            "switches": switch_names_list,
            "switch_states": switch_state_list,
            "suggested_speed": int(speed) if speed.isdigit() else 0,
            "suggested_authority": int(authority) if authority.isdigit() else 0,
            "passengers_disembarking": int(passengers) if passengers.isdigit() else 0,
        }

        with open("WaysideInputs_testUI.json", "w") as f:
            json.dump(data, f, indent=2)

        self.update_outputs()  # Update outputs after a delay

        if not self.check_pause.get():

            self.after(500, self.simulate)  # Repeat if simulate is still checked


    def update_outputs(self):
        #read in outputs
        with open("WaysideInputs_testUI.json", "r") as f:

            outputs = json.load(f)

        #configure output labels
        self.commanded_speed_var.set(outputs.get("commanded_speed", "N/A"))
        self.commanded_authority_var.set(outputs.get("commanded_authority", "N/A"))
        self.passengers_disembarking_var.set(outputs.get("passengers_disembarking", "N/A"))
        self.output_switch_names.set(",".join(outputs.get("switches", ["N/A"])))

        #make switch positions a comma-separated string
        position_str = ""

        for i in range(len(outputs.get("switch_states", []))):

            if outputs["switch_states"][i] == "Straight":

                position_str += "S"

            elif outputs["switch_states"][i] == "Diverging":

                position_str += "D"

            else:

                position_str += "N/A"

            if i < len(outputs["switch_states"])-1:

                position_str += ","

        self.output_switch_positions.set(position_str)

    def pause_function(self):

        if self.check_pause.get():
            
            self.after(100, self.pause_function)  # Check again after 100 ms



