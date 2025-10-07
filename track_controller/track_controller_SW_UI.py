# sw_track_controller_ui.py
# Author: Connor Kariotis
# ECE 1140 - Wayside Controller Software
# Description: UI for track controller maintenance and monitoring


"""Module for the Wayside Track Controller User Interface.

This module provides a Tkinter-based GUI for monitoring and maintaining
track switches, signals, gates, and train-related data. It allows users
to toggle maintenance mode, upload PLC files, and observe input/output
data in real time.
"""


#import tkinter and related libraries
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import json
import os
import plc_parser



# Constants for window size
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 700


class sw_track_controller_ui(tk.Tk):
	"""User interface for the Wayside Track Controller.

	Provides frames for maintenance, input/output data, PLC file upload,
	track map, and status updates. Periodically refreshes inputs and outputs
	from JSON files and PLC logic.
	"""

	def __init__(self, master=None):
		"""Initialize the main UI window and all widgets.

		Args:
			master: Optional parent widget. If None, creates a new Tk root.
		"""
		if master is None:
			super().__init__()  # initialize the tk.Tk class
		else:
			# If a master is provided, this is being used as a toplevel window
			super().__init__()
			self.master = master

		#set window title and size
		self.title("Track Controller Software Module")
		self.geometry(str(WINDOW_WIDTH) + "x" + str(WINDOW_HEIGHT))

		#initialize loaded inputs
		switch_options = []  # default empty list of switches

		#configure grid layout
		for i in range(3):
			self.grid_columnconfigure(i, weight=1, uniform="col")
		for i in range(2):
			self.grid_rowconfigure(i, weight=1, uniform="row")

		#------Start Maintenance Frame------#
		maintenance_frame = ttk.LabelFrame(self, text="Maintenance Mode:")
		maintenance_frame.grid(
			row=0, column=0, sticky="NSEW", padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120
		)

		#toggle maintenance mode button
		self.maintenance_mode = tk.BooleanVar(value=False)
		toggle_maintenance = ttk.Checkbutton(
			maintenance_frame,
			text="Toggle Maintenance",
			variable=self.maintenance_mode,
			command=self.toggle_maintenance_mode,
		)
		toggle_maintenance.pack(padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120)

		#switch selection dropdown
		ttk.Label(maintenance_frame, text="Select Switch").pack(
			padx=WINDOW_HEIGHT / 70, pady=(WINDOW_WIDTH / 30, 0)
		)
		self.selected_switch = tk.StringVar()
		self.switch_menu = ttk.Combobox(
			maintenance_frame, textvariable=self.selected_switch, values=switch_options, state="disabled"
		)
		self.switch_menu.pack(padx=0, pady=0)

		#Switch state dictionary
		self.switch_states_dictionary = {switch: "BASE" for switch in switch_options}

		#display current switch state
		self.switch_state_label = ttk.Label(
			maintenance_frame, text="Selected Switch State: N/A"
		)
		self.switch_state_label.pack(padx=WINDOW_HEIGHT / 70, pady=(0, WINDOW_WIDTH / 120))
		self.switch_menu.bind("<<ComboboxSelected>>", self.update_switch_state)

		#select State label
		self.select_state_label = ttk.Label(maintenance_frame, text="Select Desired State")
		self.select_state_label.pack(padx=WINDOW_HEIGHT / 70, pady=(WINDOW_WIDTH / 30, 0))

		#select State combobox
		self.select_state = tk.StringVar()
		self.select_state_menu = ttk.Combobox(
			maintenance_frame, textvariable=self.select_state, values=["BASE", "ALT"], state="disabled"
		)
		self.select_state_menu.pack(padx=0, pady=(WINDOW_WIDTH / 120, 0))

		#apply Change
		self.apply_change_button = ttk.Button(
			maintenance_frame, text="Apply Change", command=self.apply_switch_change, state="disabled"
		)
		self.apply_change_button.pack(padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120)
		#------End Maintenance Frame------#

		#------Start Input Frame------#
		input_frame = ttk.LabelFrame(self, text="Input Data:")
		input_frame.grid(
			row=0, column=1, sticky="NSEW", padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120
		)

		#label and display for suggested speed
		self.suggested_speed_label = ttk.Label(input_frame, text="Suggested Speed: N/A")
		self.suggested_speed_label.pack(padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120)

		#label and display for authority
		self.suggested_authority_label = ttk.Label(input_frame, text="Suggested Authority: N/A")
		self.suggested_authority_label.pack(padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120)

		#label and display for commanded destination
		self.destination_label = ttk.Label(input_frame, text="Destination: N/A")
		self.destination_label.pack(padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120)

		#label and display for block occupancies
		self.block_occupancies_label = ttk.Label(input_frame, text="Block Occupancies: N/A")
		self.block_occupancies_label.pack(padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120)
		#------End Input Frame------#

		#------Start Output Frame------#
		output_frame = ttk.LabelFrame(self, text="Output Data:")
		output_frame.grid(
			row=1, column=1, sticky="NSEW", padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120
		)

		#label and display for commanded speed
		self.commanded_speed_label = ttk.Label(output_frame, text="Commanded Speed: N/A")
		self.commanded_speed_label.pack(padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120)

		#label and display for commanded authority
		self.commanded_authority_label = ttk.Label(output_frame, text="Commanded Authority: N/A")
		self.commanded_authority_label.pack(padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120)

		#label and display for switch states
		self.switch_state_label_output = ttk.Label(output_frame, text="Switch States: N/A")
		self.switch_state_label_output.pack(padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120)

		#label and display for gate states
		self.gate_state_label = ttk.Label(output_frame, text="Gate States: N/A")
		self.gate_state_label.pack(padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120)

		#label and display for light states
		self.light_state_label = ttk.Label(output_frame, text="Light States: N/A")
		self.light_state_label.pack(padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120)
		#------End Output Frame------#

		#------ Start PLC Upload Frame------#
		upload_frame = ttk.LabelFrame(self, text="Upload PLC File - Maintenance Mode Necessary:")
		upload_frame.grid(
			row=1, column=0, sticky="NSEW", padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120
		)

		self.file_select_label = ttk.Label(upload_frame, text="Select PLC File:")
		self.file_select_label.pack(padx=WINDOW_HEIGHT / 70, pady=(WINDOW_WIDTH / 30, 0))

		self.file_path_var = tk.StringVar(value="test_plc.json")

		self.file_path_button = ttk.Button(
			upload_frame, text="Browse", command=self.browse_file, state="disabled"
		)
		self.file_path_button.pack(padx=WINDOW_HEIGHT / 70, pady=(0, WINDOW_WIDTH / 120))

		self.plc_file_label = ttk.Label(upload_frame, text="test_plc.json selected")
		self.plc_file_label.pack(padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120)
		#------End PLC Upload Frame------#

		#---Start Map Frame---#
		map_frame = ttk.LabelFrame(self, text="Track Map:")
		map_frame.grid(
			row=0, column=2, sticky="NSEW", padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120
		)
		
        #import map gif file and display it
		self.map_image = tk.PhotoImage(file="blue_line_map.gif")
		self.map_label = ttk.Label(map_frame, image=self.map_image)
		self.map_label.pack(expand=True, fill="both", padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120)

		#---End Map Frame---#

		#---Start Status Frame---#
		status_frame = ttk.LabelFrame(self, text="Status:")
		status_frame.grid(
			row=1, column=2, sticky="NSEW", padx=WINDOW_HEIGHT / 70, pady=WINDOW_WIDTH / 120
		)
		#---End Status Frame---#

		# Initialize file modification time tracking
		self.last_mod_time = 0

		self.load_inputs_outputs()  # load wayside inputs from JSON file


#----Maintenance Mode Functions----#

	def toggle_maintenance_mode(self):
		"""Enable or disable all maintenance-related widgets.

		Toggles the state of switches, comboboxes, and PLC upload button
		based on the current maintenance mode status.
		"""
		widgets = [self.switch_menu, self.select_state_menu, self.apply_change_button, self.file_path_button]

		if self.maintenance_mode.get():
			state = "readonly"
		else:
			state = "disabled"

		for widget in widgets:
			widget.config(state=state)


	def apply_switch_change(self):
		"""Apply the selected switch change to the internal dictionary and label."""
		switch = self.selected_switch.get()

		#remove "switch" prefix to get block ID
		if switch.startswith("switch"):
			switch = int(switch[6:])
		new_state = self.select_state.get()

		if switch and new_state:
			self.switch_states_dictionary[switch] = new_state
			self.switch_state_label.config(text="Selected Switch State: " + new_state)


	def update_switch_state(self, event):
		"""Update the switch state label when a new switch is selected."""
		switch = self.selected_switch.get()

		#remove "switch" prefix to get block ID
		if switch.startswith("switch"):
			switch = int(switch[6:])

		if switch in self.switch_states_dictionary:
			current_state = self.switch_states_dictionary[switch]
			self.switch_state_label.config(text="Selected Switch State: " + current_state)
		else:
			self.switch_state_label.config(text="Selected Switch State: N/A")


#----Input/Output Loading Function----#

	def load_inputs_outputs(self):
		"""Load input data from JSON file and update output labels accordingly.

		Reads WaysideInputsTestUISW.json and PLC file to refresh suggested speed,
		authority, destination, block occupancies, switch states, gate states, and light states.
		"""
		if os.path.exists("WaysideInputsTestUISW.json"):
			with open("WaysideInputsTestUISW.json", "r") as file:
				wayside_inputs = json.load(file)
		else:
			wayside_inputs = {}

		#Get suggested speed
		suggested_speed = wayside_inputs.get("suggested_speed", 0)
		self.suggested_speed_label.config(text="Suggested Speed: " + str(suggested_speed) + " mph")

		#Get suggested authority
		suggested_authority = wayside_inputs.get("suggested_authority", 0)
		self.suggested_authority_label.config(text="Suggested Authority: " + str(suggested_authority) + " yds")

		#Get destination
		destination = wayside_inputs.get("destination", 0)
		self.destination_label.config(text="Destination: " + str(destination))

		#Get block occupancies
		block_occupancies = wayside_inputs.get("block_occupancies", [])
		self.block_occupancies_label.config(text="Block Occupancies: " + str(block_occupancies))

		# Minimal safe initializations
		plc_rules = []
		commanded_speed = suggested_speed
		commanded_authority = suggested_authority

		#process plc file
		wayside_outputs = plc_parser.parse_plc_data(
			self.file_path_var.get(), block_occupancies, destination, suggested_speed, suggested_authority
		)
		switch_options = list("switch" + str(key) for key in wayside_outputs.get("switches", {}).keys())
		self.switch_menu.config(values=switch_options)

		#update switch states label
		if not self.maintenance_mode.get():  # only update switch states if not in maintenance mode
			self.switch_states_dictionary = wayside_outputs.get("switches", {})
			switch_states = wayside_outputs.get("switches", {})
			switch_states_str = ", ".join(f"\n\tSwitch {key}: {value}" for key, value in switch_states.items())
			self.switch_state_label_output.config(
				text="Switch States: " + switch_states_str if switch_states_str else "Switch States: N/A"
			)
		else:
			switch_states = self.switch_states_dictionary
			switch_states_str = ", ".join(f"\n\tSwitch {key}: {value}" for key, value in switch_states.items())
			self.switch_state_label_output.config(
				text="Switch States: " + switch_states_str if switch_states_str else "Switch States: N/A"
			)

			#override outputs with maintenance mode switch states
			if os.path.exists("WaysideOutputs_testUISW.json"):
				with open("WaysideOutputs_testUISW.json", "r") as file:
					wayside_outputs = json.load(file)
			else:
				wayside_outputs = {}

			wayside_outputs["switches"] = {}
			for switch, state in self.switch_states_dictionary.items():
				wayside_outputs["switches"][str(switch)] = state

			#write the overridden outputs back to the file
			with open("WaysideOutputs_testUISW.json", "w") as file:
				json.dump(wayside_outputs, file, indent=4)

		#update gate states label
		gate_states = wayside_outputs.get("crossings", {})
		gate_states_str = ", ".join(f"\n\tCrossing {key}: {value}" for key, value in gate_states.items())
		self.gate_state_label.config(
			text="Gate States: " + gate_states_str if gate_states_str else "Gate States: N/A"
		)

		#update light states label
		light_states = wayside_outputs.get("lights", {})
		light_states_str = ", ".join(f"\n\tLight {key}: {value}" for key, value in light_states.items())
		self.light_state_label.config(
			text="Light States: " + light_states_str if light_states_str else "Light States: N/A"
		)

		# Always write outputs when inputs change
		with open("WaysideOutputs_testUISW.json", "w") as file:
			json.dump(wayside_outputs, file, indent=4)

		#update output labels
		self.commanded_speed_label.config(
			text="Commanded Speed: " + str(wayside_outputs["commanded_speed"]) + " mph"
		)
		self.commanded_authority_label.config(
			text="Commanded Authority: " + str(wayside_outputs["commanded_authority"]) + " yds"
		)

		# Store the loaded inputs for next comparison
		self.wayside_inputs = wayside_inputs

		self.after(500, self.load_inputs_outputs)  # reload inputs every 500ms


	def browse_file(self):
		"""Open a file dialog to select a PLC JSON file."""
		file_path = filedialog.askopenfilename(
			filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
		)
		if file_path:
			self.file_path_var.set(file_path)
			self.plc_file_label.config(text=os.path.basename(file_path) + " selected")
		else:
			self.file_path_var.set("test_plc.json")
			self.plc_file_label.config(text="test_plc.json selected")


#-------------------------------------#


if __name__ == "__main__":
	app = sw_track_controller_ui()
	app.mainloop()
