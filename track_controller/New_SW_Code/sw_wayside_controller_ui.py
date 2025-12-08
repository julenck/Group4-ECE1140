


#Author: Connor Kariotis
#ECE 1140 - Wayside Controller Software
#Discription: UI for track controller maintenance and monitoring

"""Module for the Wayside Track Controller User Interface.

This module provides a Tkinter-based GUI for monitoring and maintaining
track switches, signals, gates, and train-related data. It allows users
to toggle maintenance mode, upload PLC files, and observe input/output
data in real time.
"""

#import tkinter and related libraries
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import json
import os
from datetime import datetime, timezone
from PIL import Image, ImageTk
# from .Green_Line_PLC_XandLup import process_states_green_xlup
# from .Green_Line_PLC_XandLdown import process_states_green_xldown
from track_controller.New_SW_Code import sw_wayside_controller
from track_controller.New_SW_Code import sw_vital_check

class sw_wayside_controller_ui:
    def __init__(self, controller):
        self.root = tk.Tk()
        self.controller = controller
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    

    # Attributes
        self.toggle_maintenance_mode: tk.BooleanVar = tk.BooleanVar(value=False)
        self.maintenance_enabled: bool = False  # Manual tracking
        self.selected_block: int = -1
        self.selected_block_data: dict = {}
        self.maintenance_frame: ttk.Frame = None
        self.input_frame: ttk.Frame = None
        self.all_blocks_frame: ttk.Frame = None
        self.map_frame: ttk.Frame = None
        self.selected_block_frame: ttk.Frame = None
        self.scrollable_frame: ttk.Frame = None
        self.blocks_with_switches: list = [13,28,57,63,77,85]
        self.blocks_with_lights: list = [0,3,7,29,58,62,76,86,100,101,150,151]
        self.blocks_with_gates: list = [19,108]

        self.block_labels: dict = {}


        #epty options for now
        self.switch_options: list = []
        self.state_options: list = ["Straight", "Diverge"]
        self.selected_switch: tk.StringVar = tk.StringVar()


        # Configure grid layout
        self.root.columnconfigure(0, weight=1)  # Left column
        self.root.columnconfigure(1, weight=1)  # Middle column
        self.root.columnconfigure(2, weight=1)  # Right column
        self.root.rowconfigure(0, weight=1)  # Top row
        self.root.rowconfigure(1, weight=1)  # Bottom row

        # Add frames for each section
        # Define styles for the frames
        style = ttk.Style(self.root)
        style.configure("Maintenance.TFrame", background="lightgray")
        style.configure("Input.TFrame", background="white")
        style.configure("AllBlocks.TFrame", background="white")
        style.configure("Map.TFrame", background="white")
        style.configure("SelectedBlock.TFrame", background="white")

        # Create frames with ttk and apply styles
        self.maintenance_frame = ttk.Frame(self.root, style="Maintenance.TFrame")
        self.maintenance_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")

        self.input_frame = ttk.Frame(self.root, style="Input.TFrame")
        self.input_frame.grid(row=0, column=1, sticky="nsew")

        self.all_blocks_frame = ttk.Frame(self.root, style="AllBlocks.TFrame")
        self.all_blocks_frame.grid(row=1, column=1, sticky="nsew")

        self.map_frame = ttk.Frame(self.root, style="Map.TFrame")
        self.map_frame.grid(row=0, column=2, sticky="nsew")
        

        self.selected_block_frame = ttk.Frame(self.root, style="SelectedBlock.TFrame")
        self.selected_block_frame.grid(row=1, column=2, sticky="nsew")

        self.start_plc: str = controller.get_start_plc()
        self.selected_file_str = tk.StringVar(value="N/A")
        self.selected_file_str.set(self.start_plc)

        self.train_data_labels: dict = {}

        self.build_maintenance_frame()
        self.update_switch_options()  # Initialize switch options based on start PLC
        self.build_input_frame()
        self.build_all_blocks_frame()
        self.build_map_frame()
        self.build_selected_block_frame()

        self.update_block_labels()
        self.update_train_data_labels()
    
    def title(self, title_text):
        """Set window title"""
        self.root.title(title_text)
    
    def geometry(self, geometry_string):
        """Set window geometry"""
        self.root.geometry(geometry_string)
    
    def mainloop(self):
        """Start the Tkinter main loop"""
        self.root.mainloop()

    def on_close(self):
         # Stop the PLC loop and all background timers
        if hasattr(self, "controller") and self.controller is not None:
            self.controller.stop()

        # Destroy the UI window cleanly
        self.root.destroy()

        # End Tkinter's mainloop completely if no other windows remain
        if hasattr(self, 'root') and hasattr(self.root, 'winfo_exists'):
            try:
                self.root.quit()
            except:
                pass

    

# Methods
    def set_light_state(self, block_id: int, state: int):
        self.controller.override_light(block_id, state)

    def set_gate_state(self, block_id: int, state: int):
        self.controller.override_gate(block_id, state)

    def set_switch_state(self, block_id: int, state: int):
        self.controller.override_switch(block_id, state)

    def set_plc(self):
        #ask for a python file
        filename = filedialog.askopenfilename(
            title="Select PLC File",
            filetypes=[("Python Files", "*.py"), ("All Files", "*.*")]
        )
        file = self.controller.load_plc(filename)

        self.update_selected_file(file)

    def send_inputs(self, data: dict):
        #self.controller.load_inputs()
        pass

    def send_outputs(self, data: dict):
        pass

    def update_selected_file(self, filename: str):
        self.selected_file_str.set(filename)
        self.selected_file_label.config(text=f"currently selected file: {os.path.basename(self.selected_file_str.get())}")
        self.update_switch_options()  # Update available switches
        self.build_all_blocks_frame()

    def select_block(self, block_id: int):
        #self.selected_block = block_id
        #self.selected_block_data = self.controller.get_block_data(block_id)
        pass

    def show_block_data(self, data: dict):
        pass

    def build_maintenance_frame(self):

        # Define styles for the maintenance frame widgets
        style = ttk.Style(self.root)
        style.configure("Maintenance.TLabel", font=("Arial", 18, "bold"), background="lightgray")
        style.configure("Maintenance.TCheckbutton", font=("Arial", 12, "bold"), background="lightgray")
        style.configure("display.TLabel", font=("Arial", 12), background="lightgray")

        # Title label
        title_label = ttk.Label(self.maintenance_frame, text="Maintenance", style="Maintenance.TLabel")
        title_label.pack(pady=10)

        # Toggle maintenance mode
        toggle_maintenance = ttk.Checkbutton(
            self.maintenance_frame,
            text="Toggle Maintenance",
            style="Maintenance.TCheckbutton",
            command=self.toggle_maintenance,
        )
        toggle_maintenance.pack(pady=10)

        #switch selection
        switch_label = ttk.Label(self.maintenance_frame, text="Select Switch:", style="Maintenance.TLabel")
        switch_label.pack(pady=5)
        self.switch_menu = ttk.Combobox(
            self.maintenance_frame,
            textvariable=self.selected_switch,
            values=self.switch_options,
            state="disabled",
        )
        self.switch_menu.pack(pady=5)
        self.switch_menu.bind("<<ComboboxSelected>>", lambda e: self.root.after(50, self.on_switch_selected))
        #show current state
        self.current_switch_state_label = ttk.Label(self.maintenance_frame, text="Current Switch State: N/A", style="display.TLabel")
        self.current_switch_state_label.pack(pady=(5,10))

        #switch state selection
        state_label = ttk.Label(self.maintenance_frame, text="Set Switch State:", style="Maintenance.TLabel")
        state_label.pack(pady=5)
        self.state_menu = ttk.Combobox(
            self.maintenance_frame,
            values=[],  # Will be populated when switch is selected
            state="disabled",
        )
        self.state_menu.pack(pady=5)
        
        # Apply button for manual switch control
        self.apply_switch_button = ttk.Button(
            self.maintenance_frame,
            text="Apply Switch Position",
            command=self.apply_manual_switch,
            state="disabled",
            style="Maintenance.TButton"
        )
        self.apply_switch_button.pack(pady=(5,40))

        #upload plc file

        plc_label = ttk.Label(self.maintenance_frame, text="Upload PLC File:", style="Maintenance.TLabel")
        plc_label.pack(pady=5)

        self.upload_button = ttk.Button(
            self.maintenance_frame,
            text="browse",
            command=self.set_plc,
            state="disabled",
            style="Maintenance.TButton"
        )
        self.upload_button.pack(pady=10)

        

        self.selected_file_label = ttk.Label(self.maintenance_frame, text=f"currently selected file: {self.selected_file_str.get()}", style="display.TLabel", wraplength=200)
        self.selected_file_label.pack(pady=5)

        # MURPHY Section - Block Failure Testing
        ttk.Separator(self.maintenance_frame, orient='horizontal').pack(fill='x', pady=10)
        
        murphy_title = ttk.Label(self.maintenance_frame, text="MURPHY", style="Maintenance.TLabel")
        murphy_title.pack(pady=5)
        
        # Block number entry
        block_entry_label = ttk.Label(self.maintenance_frame, text="Enter Block:", style="display.TLabel", font=("Arial", 9))
        block_entry_label.pack(pady=2)
        
        self.murphy_block_var = tk.StringVar()
        self.murphy_block_entry = ttk.Entry(self.maintenance_frame, textvariable=self.murphy_block_var, width=8)
        self.murphy_block_entry.pack(pady=2)
        self.murphy_block_entry.bind('<Return>', lambda e: self.load_murphy_block())
        
        load_block_btn = ttk.Button(self.maintenance_frame, text="Load", command=self.load_murphy_block, style="Maintenance.TButton")
        load_block_btn.pack(pady=2)
        
        # Failure state display frame
        self.murphy_display_frame = ttk.Frame(self.maintenance_frame, style="Maintenance.TFrame")
        self.murphy_display_frame.pack(pady=5, fill='x', padx=5)
        
        self.murphy_labels = {}  # Store label references
        self.murphy_buttons = {}  # Store button references
        self.current_murphy_block = None  # Track which block is loaded

    def load_murphy_block(self):
        """Load failure states for the specified block"""
        print(f"DEBUG: load_murphy_block called")
        # Get value directly from entry widget
        block_str = self.murphy_block_entry.get()
        print(f"DEBUG: block_str from entry = '{block_str}'")
        try:
            block_num = int(block_str)
            print(f"DEBUG: Parsed block_num = {block_num}")
        except ValueError as e:
            print(f"DEBUG: ValueError parsing block number: {e}")
            return  # Invalid input, do nothing
        
        # Check if block is in visible blocks for current controller
        print(f"DEBUG: Current PLC file = '{self.selected_file_str.get()}'")
        if self.selected_file_str.get() == "Green_Line_PLC_XandLup.py":
            # Blocks 1-73 and 144-151
            visible_blocks = list(range(1, 74)) + list(range(144, 152)) + [0]
            print(f"DEBUG: Using XandLup visible blocks")
        elif self.selected_file_str.get() == "Green_Line_PLC_XandLdown.py":
            # Blocks 70-146
            visible_blocks = list(range(70, 147))
            print(f"DEBUG: Using XandLdown visible blocks")
        else:
            print(f"DEBUG: No valid PLC loaded, returning")
            return  # No PLC loaded
        
        print(f"DEBUG: Checking if {block_num} in visible_blocks")
        if block_num not in visible_blocks:
            print(f"DEBUG: Block {block_num} not in visible range, doing nothing")
            return  # Block not in visible range, do nothing
        
        print(f"DEBUG: Block {block_num} is valid, setting current_murphy_block")
        self.current_murphy_block = block_num
        print(f"DEBUG: Calling build_murphy_display()")
        self.build_murphy_display()
    
    def build_murphy_display(self):
        """Build the failure state display for the current block"""
        print(f"DEBUG: build_murphy_display called")
        # Clear existing widgets
        for widget in self.murphy_display_frame.winfo_children():
            widget.destroy()
        
        if self.current_murphy_block is None:
            print("DEBUG: current_murphy_block is None, returning")
            return
        
        block_num = self.current_murphy_block
        print(f"DEBUG: Building display for block {block_num}")
        
        # Display block info
        block_label = ttk.Label(self.murphy_display_frame, 
                                text=f"Block {block_num}:", 
                                font=("Arial", 9, "bold"),
                                background="lightgray",
                                anchor="center")
        block_label.grid(row=0, column=0, columnspan=3, pady=3, sticky="ew")
        
        # Configure column weights for centering
        self.murphy_display_frame.columnconfigure(0, weight=1)
        self.murphy_display_frame.columnconfigure(1, weight=1)
        self.murphy_display_frame.columnconfigure(2, weight=1)
        
        # Get current failure states
        failure_types = ["Broken Track", "Power Failure", "Circuit Failure"]
        
        for i, failure_type in enumerate(failure_types):
            # Label for failure type
            type_label = ttk.Label(self.murphy_display_frame, 
                                   text=failure_type, 
                                   font=("Arial", 8),
                                   background="lightgray",
                                   anchor="center")
            type_label.grid(row=1, column=i, padx=3, pady=2, sticky="ew")
            
            # Current state label
            fault_idx = block_num * 3 + i
            current_state = self.controller.input_faults[fault_idx]
            state_text = "ON" if current_state == 1 else "OFF"
            state_color = "red" if current_state == 1 else "green"
            
            print(f"DEBUG: Failure {i} ({failure_type}): fault_idx={fault_idx}, state={current_state}")
            
            state_label = ttk.Label(self.murphy_display_frame, 
                                    text=state_text, 
                                    font=("Arial", 8, "bold"),
                                    foreground=state_color,
                                    background="lightgray",
                                    anchor="center")
            state_label.grid(row=2, column=i, padx=3, pady=2, sticky="ew")
            self.murphy_labels[i] = state_label
            
            # Toggle button
            toggle_btn = ttk.Button(self.murphy_display_frame, 
                                    text="Toggle", 
                                    command=lambda idx=i: self.toggle_murphy_failure(idx),
                                    style="Maintenance.TButton")
            toggle_btn.grid(row=3, column=i, padx=3, pady=2, sticky="ew")
            self.murphy_buttons[i] = toggle_btn
        
        print(f"DEBUG: Display built successfully")
    
    def toggle_murphy_failure(self, failure_idx):
        """Toggle a specific failure type for the current block"""
        print(f"DEBUG: toggle_murphy_failure called with failure_idx={failure_idx}")
        if self.current_murphy_block is None:
            print("DEBUG: current_murphy_block is None, returning")
            return
        
        fault_idx = self.current_murphy_block * 3 + failure_idx
        print(f"DEBUG: Toggling fault_idx={fault_idx} for block {self.current_murphy_block}")
        
        # Toggle the failure state
        current_state = self.controller.input_faults[fault_idx]
        new_state = 0 if current_state == 1 else 1
        self.controller.input_faults[fault_idx] = new_state
        
        print(f"DEBUG: Changed state from {current_state} to {new_state}")
        
        # Update the display
        state_text = "ON" if new_state == 1 else "OFF"
        state_color = "red" if new_state == 1 else "green"
        self.murphy_labels[failure_idx].config(text=state_text, foreground=state_color)
        print(f"DEBUG: Updated label to {state_text} with color {state_color}")

    def update_switch_options(self):
        state_text = "ACTIVE" if new_state == 1 else "OFF"
        state_color = "red" if new_state == 1 else "green"
        self.murphy_labels[failure_idx].config(text=state_text, foreground=state_color)

    def update_switch_options(self):
        """Update available switches based on loaded PLC file"""
        if self.selected_file_str.get() == "Green_Line_PLC_XandLup.py":
            # Switches 0-3 correspond to blocks 13, 28, 57, 63
            self.switch_options = ["Switch 1 (Block 13)", "Switch 2 (Block 28)", 
                                   "Switch 3 (Block 57)", "Switch 4 (Block 63)"]
        elif self.selected_file_str.get() == "Green_Line_PLC_XandLdown.py":
            # Switches 4-5 correspond to blocks 77, 85
            self.switch_options = ["Switch 5 (Block 77)", "Switch 6 (Block 85)"]
        else:
            self.switch_options = []
        
        self.switch_menu.config(values=self.switch_options)
        self.selected_switch.set("")  # Clear selection
        if self.current_switch_state_label:
            self.current_switch_state_label.config(text="Current Switch State: N/A")

    def on_switch_selected(self, event=None):
        """Update current state display when a switch is selected"""
        # Get value directly from the combobox widget instead of StringVar
        selection = self.switch_menu.get()
        print(f"DEBUG: on_switch_selected called, selection = '{selection}'")
        if not selection or selection == "":
            print("DEBUG: No selection, returning")
            return
        
        # Parse switch index from selection
        switch_idx = self.get_switch_index_from_selection(selection)
        print(f"DEBUG: Switch index = {switch_idx}")
        if switch_idx is not None:
            current_state = self.controller.switch_states[switch_idx]
            print(f"DEBUG: Current state = {current_state}")
            
            # Get the specific block connections for this switch
            state_options = self.get_switch_state_options(switch_idx)
            print(f"DEBUG: State options = {state_options}")
            print(f"DEBUG: Setting state_menu values to {state_options}")
            self.state_menu['values'] = state_options
            print(f"DEBUG: state_menu values set, checking: {self.state_menu['values']}")
            
            # Show current state
            state_str = state_options[current_state] if current_state < len(state_options) else "Unknown"
            self.current_switch_state_label.config(text=f"Current Switch State: {state_str}")
            print(f"DEBUG: Updated label to: {state_str}")
        else:
            print("DEBUG: switch_idx is None")

    def get_switch_state_options(self, switch_idx):
        """Get the specific block connection options for a switch"""
        # Define the connections for each switch
        # Format: [state_0_connection (lower block), state_1_connection (higher/diverge block)]
        # State 0 = connected to lower numbered block
        # State 1 = connected to higher numbered or diverging block
        switch_connections = {
            0: ["13-1", "13-12"],       # Switch 1 (Block 13): 0=to block 1, 1=to block 12
            1: ["28-27", "28-29"],      # Switch 2 (Block 28): 0=to block 27, 1=to block 29
            2: ["57-58", "57-Yard"],    # Switch 3 (Block 57): 0=to block 58, 1=to Yard
            3: ["Yard-63", "62-63"],    # Switch 4 (Block 63): 0=to Yard, 1=to block 62
            4: ["77-76", "77-101"],     # Switch 5 (Block 77): 0=to block 76, 1=to block 101
            5: ["85-84", "85-86"]       # Switch 6 (Block 85): 0=to block 84, 1=to block 86
        }
        return switch_connections.get(switch_idx, ["State 0", "State 1"])

    def get_switch_index_from_selection(self, selection):
        """Extract switch index from combo box selection string"""
        if "Switch 1" in selection:
            return 0
        elif "Switch 2" in selection:
            return 1
        elif "Switch 3" in selection:
            return 2
        elif "Switch 4" in selection:
            return 3
        elif "Switch 5" in selection:
            return 4
        elif "Switch 6" in selection:
            return 5
        return None

    def apply_manual_switch(self):
        """Apply manual switch position override"""
        print("DEBUG: apply_manual_switch called")
        # Get values directly from the combobox widgets instead of StringVars
        selection = self.switch_menu.get()
        desired_state = self.state_menu.get()
        print(f"DEBUG: selection = '{selection}', desired_state = '{desired_state}'")
        
        if not selection or not desired_state:
            print("DEBUG: Missing selection or desired state, returning")
            return
        
        switch_idx = self.get_switch_index_from_selection(selection)
        print(f"DEBUG: switch_idx = {switch_idx}")
        if switch_idx is None:
            print("DEBUG: switch_idx is None, returning")
            return
        
        # Get the state options for this switch and find the index
        state_options = self.get_switch_state_options(switch_idx)
        print(f"DEBUG: state_options = {state_options}")
        try:
            state_value = state_options.index(desired_state)
            print(f"DEBUG: state_value = {state_value}")
        except ValueError as e:
            print(f"DEBUG: ValueError - invalid state selected: {e}")
            return  # Invalid state selected
        
        # Apply the manual override
        print(f"DEBUG: Setting switch_states[{switch_idx}] = {state_value}")
        print(f"DEBUG: Before - controller.switch_states[{switch_idx}] = {self.controller.switch_states[switch_idx]}")
        self.controller.manual_switch_overrides[switch_idx] = state_value
        self.controller.switch_states[switch_idx] = state_value
        print(f"DEBUG: After - controller.switch_states[{switch_idx}] = {self.controller.switch_states[switch_idx]}")
        print(f"DEBUG: manual_switch_overrides = {self.controller.manual_switch_overrides}")
        
        # Verify the switch change using vital checks
        verification_passed = self.controller.vital.verify_switch_change(
            switch_idx, 
            state_value, 
            self.controller.switch_states
        )
        
        if not verification_passed:
            # Vital check failed - toggle power failure for this block
            # Map switch index to block ID
            blocks_with_switches = [13, 28, 57, 63, 77, 85]
            if switch_idx < len(blocks_with_switches):
                block_id = blocks_with_switches[switch_idx]
                # Toggle power failure (index = block_id * 3 + 1)
                power_failure_idx = block_id * 3 + 1
                self.controller.input_faults[power_failure_idx] = 1
                print(f"[VITAL CHECK FAILED] Switch {switch_idx} at block {block_id} - Power failure activated")
        else:
            print(f"[VITAL CHECK PASSED] Switch {switch_idx} verified successfully")
        
        # Update display
        self.current_switch_state_label.config(text=f"Current Switch State: {desired_state}")
        print(f"DEBUG: Updated label to: {desired_state}")
        
        # Clear the state selection
        self.state_menu.set("")

    def build_input_frame(self):
        # Clear frame first
        for widget in self.input_frame.winfo_children():
            widget.destroy()
            
        # Define a style for the input frame widgets
        style = ttk.Style(self.root)
        style.configure("Input.TLabel", font=("Arial", 16, "bold"), background="white")
        style.configure("TrainData.TLabel", font=("Arial", 10), background="white")

        # Title label
        title_label = ttk.Label(self.input_frame, text="Active Train Data", style="Input.TLabel")
        title_label.pack(pady=10)
        
        # Create scrollable container for train data
        container = ttk.Frame(self.input_frame)
        container.pack(fill="both", expand=True, padx=10, pady=5)
        
        canvas = tk.Canvas(container, bg="white", height=250)
        scroller = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        train_data_frame = ttk.Frame(canvas)
        
        train_data_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=train_data_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroller.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scroller.pack(side="right", fill="y")
        
        # Get active train data from controller
        train_data = self.controller.get_active_trains()
        
        if not train_data:
            no_train_label = ttk.Label(train_data_frame, text="No active trains in this section", style="TrainData.TLabel")
            no_train_label.pack(pady=20)
        else:
            # Create headers
            headers_frame = ttk.Frame(train_data_frame)
            headers_frame.pack(fill="x", padx=5, pady=5)
            
            ttk.Label(headers_frame, text="Train", style="TrainData.TLabel", width=10).grid(row=0, column=0, padx=5, sticky="w")
            ttk.Label(headers_frame, text="Position", style="TrainData.TLabel", width=10).grid(row=0, column=1, padx=5, sticky="w")
            ttk.Label(headers_frame, text="Speed (m/s)", style="TrainData.TLabel", width=12).grid(row=0, column=2, padx=5, sticky="w")
            ttk.Label(headers_frame, text="Authority (m)", style="TrainData.TLabel", width=12).grid(row=0, column=3, padx=5, sticky="w")
            
            # Add separator
            ttk.Separator(train_data_frame, orient='horizontal').pack(fill='x', pady=2)
            
            # Display each train's data
            row = 1
            self.train_data_labels = {}
            for train_id, data in train_data.items():
                train_frame = ttk.Frame(train_data_frame)
                train_frame.pack(fill="x", padx=5, pady=2)
                
                train_label = ttk.Label(train_frame, text=train_id, style="TrainData.TLabel", width=10)
                train_label.grid(row=0, column=0, padx=5, sticky="w")
                
                pos_label = ttk.Label(train_frame, text=str(data.get('pos', 'N/A')), style="TrainData.TLabel", width=10)
                pos_label.grid(row=0, column=1, padx=5, sticky="w")
                
                speed_label = ttk.Label(train_frame, text=f"{data.get('cmd speed', 0):.2f}", style="TrainData.TLabel", width=12)
                speed_label.grid(row=0, column=2, padx=5, sticky="w")
                
                auth_label = ttk.Label(train_frame, text=f"{data.get('cmd auth', 0):.2f}", style="TrainData.TLabel", width=12)
                auth_label.grid(row=0, column=3, padx=5, sticky="w")
                
                # Store labels for updating
                self.train_data_labels[train_id] = {
                    "pos": pos_label,
                    "speed": speed_label,
                    "auth": auth_label
                }
                row += 1

        # #sub frame for train data
        # self.train_data_frame = ttk.Frame(self.input_frame)
        # self.train_data_frame.pack(fill="both", expand=True, padx=10, pady=10)
        # #read in cmd train data from controller
        # train_data = self.controller.get_active_trains()
        # if train_data == {}:
        #     no_train_label = ttk.Label(self.train_data_frame, text="No active trains", style="smaller.TLabel")
        #     no_train_label.pack(pady=10)
        # else:
        #     i=0
        #     for train in train_data:
        #     #if on first wayside
        #         if self.selected_file_str.get() == "Green_Line_PLC_XandLup.py":
        #             if train_data[train]["pos"] <= 73 or train_data[train]["pos"] >= 144:
        #                 train_label = ttk.Label(self.train_data_frame, text=f"Train {train}:", style="smaller.TLabel")
        #                 train_label.grid(row=int(train[-1])-1, column=0, padx=5, pady=5, sticky="w")
        #                 speed_label = ttk.Label(self.train_data_frame, text=f"  Commanded Speed: {train_data[train]['cmd speed']} m/s", style="smaller.TLabel")
        #                 speed_label.grid(row=int(train[-1])-1, column=1, padx=5, pady=5, sticky="w")
        #                 auth_label = ttk.Label(self.train_data_frame, text=f"  Commanded Authority: {train_data[train]['cmd auth']} m", style="smaller.TLabel" )
        #                 auth_label.grid(row=int(train[-1])-1, column=2, padx=5, pady=5, sticky="w")
        #                 pos_label = ttk.Label(self.train_data_frame, text=f"  Position: {train_data[train]['pos']}", style="smaller.TLabel")
        #                 pos_label.grid(row=int(train[-1])-1, column=3, padx=5, pady=5, sticky="w")

        #         self.train_data_labels[i] = {
        #                             "train": train_label,
        #                             "speed": speed_label,
        #                             "auth": auth_label,
        #                             "pos": pos_label
        #                         }
        #         i+=1      
        #self.update_train_data_labels()
            

        

    def build_all_blocks_frame(self):
        #clear frame first
        for widget in self.all_blocks_frame.winfo_children():
            widget.destroy()
        # Clear block_labels dict since we're rebuilding all labels
        self.block_labels = {}
        # Define a style for the all blocks frame widgets
        style = ttk.Style(self.root)
        style.configure("AllBlocks.TLabel", font=("Arial", 16, "bold"), background="white")
        style.configure("smaller.TLabel", font=("Arial", 12), background="white")

        # Title label
        title_label = ttk.Label(self.all_blocks_frame, text="All Blocks Status", style="AllBlocks.TLabel")
        title_label.pack(pady=10)

        #create grid to display all blocks
        container = ttk.Frame(self.all_blocks_frame)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, bg="white")
        scroller = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        #make scrollable frame self so it can be accessed later
        self.scrollable_frame = ttk.Frame(canvas, style = "smaller.TLabel")
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroller.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scroller.pack(side="right", fill="y")


        def on_scroll(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        # Bind only to this canvas, not all widgets
        canvas.bind("<MouseWheel>", on_scroll)

        #message for start because no plc file loaded
        if self.selected_file_str.get() == "N/A":
            no_file_label = ttk.Label(self.scrollable_frame, text="No PLC file loaded", style="smaller.TLabel")
            no_file_label.grid(row=0, column=0, padx=10, pady=10)

        else:

            #grid headers:
            ttk.Label(self.scrollable_frame, text="Block", style="smaller.TLabel").grid(row=0, column=1, padx=5, pady=5)
            ttk.Label(self.scrollable_frame, text="Occupied", style="smaller.TLabel").grid(row=0, column=2, padx=5, pady=5)
            ttk.Label(self.scrollable_frame, text="Switch", style="smaller.TLabel").grid(row=0, column=3, padx=5, pady=5)
            ttk.Label(self.scrollable_frame, text="Light", style="smaller.TLabel").grid(row=0, column=4, padx=5, pady=5)
            ttk.Label(self.scrollable_frame, text="Gate", style="smaller.TLabel").grid(row=0, column=5, padx=5, pady=5)
            ttk.Label(self.scrollable_frame, text="Failure", style="smaller.TLabel").grid(row=0, column=6, padx=5, pady=5)

            if (os.path.basename(self.selected_file_str.get()) == "Green_Line_PLC_XandLup.py"):
                #build grid for 80 blocks
                #self.block_vars = {}

                #block for Enter track from yard
                check_box = ttk.Checkbutton(self.scrollable_frame,
                                            variable=self.selected_block,
                                            onvalue=152,
                                            offvalue=-1,
                                            command=lambda idx=152: self.on_block_selected(idx))

                check_box.grid(row=1, column=0, padx=5, pady=5)
                block_label = ttk.Label(
                    self.scrollable_frame,
                    text="Leave Yard",
                    style="smaller.TLabel"
                )
                block_label.grid(row=1, column=1, padx=5, pady=5)
                #get yard data
                desired = self.controller.get_block_data(0)
                occupied_label = ttk.Label(self.scrollable_frame, text=f"{desired['occupied']}", style="smaller.TLabel")
                if desired['occupied']:
                    occupied_label.configure(background="lightgreen")
                occupied_label.grid(row=1, column=2, padx=5, pady=5)
                switch_label = ttk.Label(self.scrollable_frame, text=f"{desired['switch_state']}", style="smaller.TLabel")
                switch_label.grid(row=1, column=3, padx=5, pady=5)
                light_label = ttk.Label(self.scrollable_frame, text=f"{desired['light_state']}", style="smaller.TLabel")
                light_label.grid(row=1, column=4, padx=5, pady=5)
                gate_label = ttk.Label(self.scrollable_frame, text=f"{desired['gate_state']}", style="smaller.TLabel")
                gate_label.grid(row=1, column=5, padx=5, pady=5)
                failure_label = ttk.Label(self.scrollable_frame, text=f"{desired['Failure']}", style="smaller.TLabel")
                failure_label.grid(row=1, column=6, padx=5, pady=5)


                self.block_labels[0] = {
                    "occupied": occupied_label,
                    "switch": switch_label,
                    "light": light_label,
                    "gate": gate_label,
                    "failure": failure_label
                }
                for i in range(80):

                    
                    #self.block_vars[i] = check_box


                    if i <73:
                        block_num = i + 1
                    else:
                        block_num = i + 71
                    section_letter = self.get_section_letter(block_num)

                    check_box = ttk.Checkbutton(self.scrollable_frame,
                                                variable=self.selected_block, 
                                                onvalue=i,
                                                offvalue=-1,
                                                command=lambda idx=i: self.on_block_selected(idx))

                    block_label = ttk.Label(
                        self.scrollable_frame,
                        text=f"{section_letter}{block_num}",
                        style="smaller.TLabel"
                    )

                    check_box.grid(row=i+2, column=0, padx=5, pady=5)
                    block_label.grid(row=i + 2, column=1, padx=5, pady=5)

                    desired = self.controller.get_block_data(block_num)
                    occupied_label = ttk.Label(self.scrollable_frame, text=f"{desired['occupied']}", style="smaller.TLabel")
                    if desired['occupied']:
                        occupied_label.configure(background="lightgreen")
                    occupied_label.grid(row=i+2, column=2, padx=5, pady=5)  
                    switch_label = ttk.Label(self.scrollable_frame, text=f"{desired['switch_state']}", style="smaller.TLabel")
                    switch_label.grid(row=i+2, column=3, padx=5, pady= 5)
                    light_label = ttk.Label(self.scrollable_frame, text=f"{desired['light_state']}", style="smaller.TLabel")
                    light_label.grid(row=i+2, column=4, padx=5, pady=5)
                    gate_label = ttk.Label(self.scrollable_frame, text=f"{desired['gate_state']}", style="smaller.TLabel")
                    gate_label.grid(row=i+2, column=5, padx=5, pady=5)
                    failure_label = ttk.Label(self.scrollable_frame, text=f"{desired['Failure']}", style="smaller.TLabel")  
                    failure_label.grid(row=i+2, column=6, padx=5, pady=5)

                    self.block_labels[block_num] = {
                        "occupied": occupied_label,
                        "switch": switch_label,
                        "light": light_label,
                        "gate": gate_label,
                        "failure": failure_label
                    }
                
                    #block for Enter yard from track
                check_box = ttk.Checkbutton(self.scrollable_frame,
                                            variable=self.selected_block,
                                            onvalue=151,
                                            offvalue=-1,
                                            command=lambda idx=151: self.on_block_selected(idx))
                check_box.grid(row=82, column=0, padx=5, pady=5)
                block_label = ttk.Label(
                    self.scrollable_frame,
                    text="Enter Yard",
                    style="smaller.TLabel"
                )
                block_label.grid(row=82, column=1, padx=5, pady=5)

                desired = self.controller.get_block_data(151)
                occupied_label = ttk.Label(self.scrollable_frame, text=f"{desired['occupied']}", style="smaller.TLabel")
                if desired['occupied']:
                    occupied_label.configure(background="lightgreen")
                occupied_label.grid(row=82, column=2, padx=5, pady=5)
                switch_label = ttk.Label(self.scrollable_frame, text=f"{desired['switch_state']}", style="smaller.TLabel")
                switch_label.grid(row=82, column=3, padx=5, pady=5)
                light_label = ttk.Label(self.scrollable_frame, text=f"{desired['light_state']}", style="smaller.TLabel")
                light_label.grid(row=82, column=4, padx=5, pady=5)
                gate_label = ttk.Label(self.scrollable_frame, text=f"{desired['gate_state']}", style="smaller.TLabel")
                gate_label.grid(row=82, column=5, padx=5, pady=5)
                failure_label = ttk.Label(self.scrollable_frame, text=f"{desired['Failure']}", style="smaller.TLabel")
                failure_label.grid(row=82, column=6, padx=5, pady=5)

                self.block_labels[151] = {
                    "occupied": occupied_label,
                    "switch": switch_label,
                    "light": light_label,
                    "gate": gate_label,
                    "failure": failure_label
                }
            
            elif (os.path.basename(self.selected_file_str.get()) == "Green_Line_PLC_XandLdown.py"):
                #build for 77 blocks

                for i in range(77):
                    block_num = i + 70
                    section_letter = self.get_section_letter(block_num)
                    check_box = ttk.Checkbutton(self.scrollable_frame,
                                                variable=self.selected_block, 
                                                onvalue=i,
                                                offvalue=-1,
                                                command=lambda idx=i: self.on_block_selected(idx))
                    check_box.grid(row=i+1, column=0, padx=5, pady=5)

                    block_label = ttk.Label(
                        self.scrollable_frame,
                        text=f"{section_letter}{block_num}",
                        style="smaller.TLabel"
                    )
                    block_label.grid(row=i + 1, column=1, padx=5, pady=5)
                    desired = self.controller.get_block_data(block_num)
                    occupied_label = ttk.Label(self.scrollable_frame, text=f"{desired['occupied']}", style="smaller.TLabel")
                    if desired['occupied']:
                        occupied_label.configure(background="lightgreen")
                    occupied_label.grid(row=i+1, column=2, padx=5, pady=5)  
                    switch_label = ttk.Label(self.scrollable_frame, text=f"{desired['switch_state']}", style="smaller.TLabel")  
                    switch_label.grid(row=i+1, column=3, padx=5, pady= 5)
                    light_label = ttk.Label(self.scrollable_frame, text=f"{desired['light_state']}", style="smaller.TLabel")
                    light_label.grid(row=i+1, column=4, padx=5, pady=5)
                    gate_label = ttk.Label(self.scrollable_frame, text=f"{desired['gate_state']}", style="smaller.TLabel")
                    gate_label.grid(row=i+1, column=5, padx=5, pady=5)
                    failure_label = ttk.Label(self.scrollable_frame, text=f"{desired['Failure']}", style="smaller.TLabel")  
                    failure_label.grid(row=i+1, column=6, padx=5, pady=5)

                    self.block_labels[block_num] = {
                        "occupied": occupied_label,
                        "switch": switch_label,
                        "light": light_label,
                        "gate": gate_label,
                        "failure": failure_label
                    }

    def update_train_data_labels(self):
        """Update train data labels with current information"""
        train_data = self.controller.get_active_trains()
        
        # Update existing labels
        for train_id, labels in list(self.train_data_labels.items()):
            if train_id in train_data:
                data = train_data[train_id]
                labels["pos"].config(text=str(data.get('pos', 'N/A')))
                labels["speed"].config(text=f"{data.get('cmd speed', 0):.2f}")
                labels["auth"].config(text=f"{data.get('cmd auth', 0):.2f}")
            else:
                # Train no longer active, rebuild the frame
                self.build_input_frame()
                return
        
        # Check if new trains appeared
        if set(train_data.keys()) != set(self.train_data_labels.keys()):
            self.build_input_frame()
        
        self.root.after(200, self.update_train_data_labels)

    def update_block_labels(self):
        for block_id, labels in self.block_labels.items():
            data = self.controller.get_block_data(block_id)
            labels["occupied"].config(text=f"{data['occupied']}")
            # Update background color based on occupancy
            if data['occupied']:
                labels["occupied"].configure(background="lightgreen")
            else:
                labels["occupied"].configure(background="white")
            labels["switch"].config(text=f"{data['switch_state']}")
            labels["light"].config(text=f"{data['light_state']}")
            labels["gate"].config(text=f"{data['gate_state']}")
            labels["failure"].config(text=f"{data['Failure']}")
        
        # Don't rebuild the frame every update - it causes lag
        # Only call update_selected_block_info to refresh values
        if self.selected_block != -1:
            self.update_selected_block_info()

        # Reduced frequency to 1000ms (1 second) to prevent scroll lag
        self.root.after(1000, self.update_block_labels)

    def on_block_selected(self, idx: int):
        # If user clicks the same checkbox again, deselect it
        if idx==0:
            self.selected_block = 0
        
        elif self.selected_block == idx:
            self.selected_block = -1
        else:
            self.selected_block = idx

        # Update the right-side info frame - rebuild when selection changes
        self.build_selected_block_frame()
    
    def build_map_frame(self):
        # Define a style for the map frame widgets
        style = ttk.Style(self.root)
        style.configure("Map.TLabel", font=("Arial", 16, "bold"), background="white")
        style.configure("smaller.TLabel", font=("Arial", 12), background="white")

        # Title label
        title_label = ttk.Label(self.map_frame, text="Track Map", style="Map.TLabel")
        title_label.pack(pady=10)

        # Load and display track map image
        try:
            # Use absolute path based on this module's location
            # This works correctly even when module is imported from different locations
            import sys
            import inspect
            
            # Get the directory of THIS module file
            module_file = inspect.getfile(inspect.currentframe())
            module_dir = os.path.dirname(os.path.abspath(module_file))
            image_path = os.path.join(module_dir, "track_map.png")
            
            # Load image
            image = Image.open(image_path)
            
            # Resize image to fit in the frame (adjust size as needed)
            # Calculate aspect ratio to maintain proportions
            max_width = 400
            max_height = 350
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage - store as instance variable to prevent garbage collection
            self.track_map_photo = ImageTk.PhotoImage(image, master=self.root)
            
            # Create label to display image
            map_label = ttk.Label(self.map_frame, image=self.track_map_photo)
            map_label.image = self.track_map_photo  # Keep a reference to prevent garbage collection
            map_label.pack(pady=10, padx=10)
            
        except FileNotFoundError:
            # Fallback if image not found
            map_display_label = ttk.Label(self.map_frame, text="Track map image not found.", style="smaller.TLabel")
            map_display_label.pack(pady=10)
        except Exception as e:
            # Fallback for any other error
            map_display_label = ttk.Label(self.map_frame, text=f"Error loading map: {str(e)}", style="smaller.TLabel")
            map_display_label.pack(pady=10)

        

    def build_selected_block_frame(self):
        #clear frame first
        for widget in self.selected_block_frame.winfo_children():
            widget.destroy()
        
        # Initialize label references dictionary
        self.selected_block_labels = {}
        
        try:
            # Define a style for the selected block frame widgets
            style = ttk.Style(self.root)
            style.configure("SelectedBlock.TLabel", font=("Arial", 16, "bold"), background="white")
            style.configure("smaller.TLabel", font=("Arial", 12), background="white")

            # Title label
            title_label = ttk.Label(self.selected_block_frame, text="Selected Block Info", style="SelectedBlock.TLabel")
            title_label.pack(pady=10)

            # Selected block info display (placeholder)
            if self.selected_block == -1:
                self.block_info_label = ttk.Label(self.selected_block_frame, text="Selected block information will be displayed here.", style="smaller.TLabel")
                self.block_info_label.pack(pady=10)
            elif os.path.basename(self.selected_file_str.get()) == "Green_Line_PLC_XandLup.py":
                if self.selected_block <= 79:
                    block = self.selected_block + 1 if self.selected_block < 73 else self.selected_block + 71
                    sec = self.get_section_letter(block)
                    self.selected_block_data = self.controller.get_block_data(block)  
                elif self.selected_block == 151:
                    block=151
                    self.selected_block_data = self.controller.get_block_data(block)
                    
                elif self.selected_block == 152:
                    block=0
                    self.selected_block_data = self.controller.get_block_data(block)
                
                id = self.selected_block_data["block_id"]
                occupied = self.selected_block_data["occupied"]
                switch_state_enum = self.selected_block_data["switch_state"]
                light_state_enum = self.selected_block_data["light_state"]
                gate_state_enum = self.selected_block_data["gate_state"]
                failure_enum = self.selected_block_data["Failure"]

                switch_state, light_state, gate_state, failure = self.get_all_strings(switch_state_enum, light_state_enum, gate_state_enum, failure_enum,id)

                if self.selected_block <=79:
                    id_label = ttk.Label(self.selected_block_frame, text=f"Block ID: {sec}{block}", style="smaller.TLabel")
                elif self.selected_block ==151:
                    id_label = ttk.Label(self.selected_block_frame, text=f"Block ID: Enter Yard(151)", style="smaller.TLabel")
                elif self.selected_block ==152:
                    id_label = ttk.Label(self.selected_block_frame, text=f"Block ID: Leave Yard(0)", style="smaller.TLabel")
                id_label.pack(pady=5)
                self.selected_block_labels['id'] = id_label
                
                occupied_label = ttk.Label(self.selected_block_frame, text=f"Occupied: {occupied}", style="smaller.TLabel")
                occupied_label.pack(pady=5)
                self.selected_block_labels['occupied'] = occupied_label
                
                switch_label = ttk.Label(self.selected_block_frame, text=f"Switch State: {switch_state}", style="smaller.TLabel")
                switch_label.pack(pady=5)
                self.selected_block_labels['switch'] = switch_label
                
                light_label = ttk.Label(self.selected_block_frame, text=f"Light State: {light_state}", style="smaller.TLabel")
                light_label.pack(pady=5)
                self.selected_block_labels['light'] = light_label
                
                gate_label = ttk.Label(self.selected_block_frame, text=f"Gate State: {gate_state}", style="smaller.TLabel")
                gate_label.pack(pady=5)
                self.selected_block_labels['gate'] = gate_label
                
                failure_label = ttk.Label(self.selected_block_frame, text=f"Failure: {failure}", style="smaller.TLabel")
                failure_label.pack(pady=5)
                self.selected_block_labels['failure'] = failure_label

            elif os.path.basename(self.selected_file_str.get()) == "Green_Line_PLC_XandLdown.py":
                block = self.selected_block + 70
                sec = self.get_section_letter(block)
                self.selected_block_data = self.controller.get_block_data(block)  

                id = block
                occupied = self.selected_block_data["occupied"]
                switch_state_enum = self.selected_block_data["switch_state"]
                light_state_enum = self.selected_block_data["light_state"]
                gate_state_enum = self.selected_block_data["gate_state"]
                failure_enum = self.selected_block_data["Failure"]

                switch_state, light_state, gate_state, failure = self.get_all_strings(switch_state_enum, light_state_enum, gate_state_enum, failure_enum,id)    

                id_label = ttk.Label(self.selected_block_frame, text=f"Block ID: {sec}{block}", style="smaller.TLabel")
                id_label.pack(pady=5)
                self.selected_block_labels['id'] = id_label
                
                occupied_label = ttk.Label(self.selected_block_frame, text=f"Occupied: {occupied}", style="smaller.TLabel")
                occupied_label.pack(pady=5)
                self.selected_block_labels['occupied'] = occupied_label
                
                switch_label = ttk.Label(self.selected_block_frame, text=f"Switch State: {switch_state}", style="smaller.TLabel")
                switch_label.pack(pady=5)
                self.selected_block_labels['switch'] = switch_label
                
                light_label = ttk.Label(self.selected_block_frame, text=f"Light State: {light_state}", style="smaller.TLabel")
                light_label.pack(pady=5)
                self.selected_block_labels['light'] = light_label
                
                gate_label = ttk.Label(self.selected_block_frame, text=f"Gate State: {gate_state}", style="smaller.TLabel")
                gate_label.pack(pady=5)
                self.selected_block_labels['gate'] = gate_label
                
                failure_label = ttk.Label(self.selected_block_frame, text=f"Failure: {failure}", style="smaller.TLabel")
                failure_label.pack(pady=5)
                self.selected_block_labels['failure'] = failure_label
            
        except Exception as e:
            # If there's an error, display it
            error_label = ttk.Label(self.selected_block_frame, text=f"Error: {str(e)}", style="smaller.TLabel")
            error_label.pack(pady=10)
            print(f"Error in build_selected_block_frame: {e}")

    def update_selected_block_info(self):
        """Update selected block info without rebuilding the entire frame - prevents lag"""
        if self.selected_block == -1:
            return
        
        # Check if labels exist
        if not hasattr(self, 'selected_block_labels') or not self.selected_block_labels:
            return  # Labels haven't been built yet
        
        # Just refresh the data, don't rebuild widgets
        try:
            if os.path.basename(self.selected_file_str.get()) == "Green_Line_PLC_XandLup.py":
                if self.selected_block <= 79:
                    block = self.selected_block + 1 if self.selected_block < 73 else self.selected_block + 71
                elif self.selected_block == 151:
                    block = 151
                elif self.selected_block == 152:
                    block = 0
                else:
                    return
                self.selected_block_data = self.controller.get_block_data(block)
            elif os.path.basename(self.selected_file_str.get()) == "Green_Line_PLC_XandLdown.py":
                block = self.selected_block + 70
                self.selected_block_data = self.controller.get_block_data(block)
            else:
                return
            
            # Now update the label texts without destroying them
            id = self.selected_block_data["block_id"]
            occupied = self.selected_block_data["occupied"]
            switch_state_enum = self.selected_block_data["switch_state"]
            light_state_enum = self.selected_block_data["light_state"]
            gate_state_enum = self.selected_block_data["gate_state"]
            failure_enum = self.selected_block_data["Failure"]

            switch_state, light_state, gate_state, failure = self.get_all_strings(switch_state_enum, light_state_enum, gate_state_enum, failure_enum, id)

            # Update existing labels
            self.selected_block_labels['occupied'].config(text=f"Occupied: {occupied}")
            self.selected_block_labels['switch'].config(text=f"Switch State: {switch_state}")
            self.selected_block_labels['light'].config(text=f"Light State: {light_state}")
            self.selected_block_labels['gate'].config(text=f"Gate State: {gate_state}")
            self.selected_block_labels['failure'].config(text=f"Failure: {failure}")
            
        except Exception as e:
            print(f"Error updating selected block info: {e}")
            pass  # Silently ignore errors during update



                
    
    def toggle_maintenance(self):
        # Toggle the state manually
        self.maintenance_enabled = not self.maintenance_enabled
        
        if self.maintenance_enabled:
            # Enable maintenance mode in controller
            self.controller.maintenance_mode = True
            self.switch_menu['state'] = 'readonly'
            self.state_menu['state'] = 'readonly'
            self.upload_button['state'] = 'normal'
            self.apply_switch_button['state'] = 'normal'
        else:
            # Disable maintenance mode and clear overrides
            self.controller.maintenance_mode = False
            self.controller.manual_switch_overrides.clear()
            self.switch_menu['state'] = 'disabled'
            self.state_menu['state'] = 'disabled'
            self.upload_button['state'] = 'disabled'
            self.apply_switch_button['state'] = 'disabled'

    def get_section_letter(self, block_num: int):
        block_num -= 1  # Adjust for 0-based index
        if block_num == 151:
            return 'Enter Yard'
        elif block_num == 152:
            return 'Leave Yard'
        if block_num < 3:
            return 'A'
        elif block_num < 6:
            return 'B'
        elif block_num < 12:
            return 'C'
        elif block_num < 16:
            return 'D'
        elif block_num < 20:
            return 'E'
        elif block_num < 28:
            return 'F'
        elif block_num < 32:
            return 'G'
        elif block_num < 35:
            return 'H'
        elif block_num < 57:
            return 'I'
        elif block_num < 62:
            return 'J'
        elif block_num < 68:
            return 'K'
        elif block_num < 73:
            return 'L'
        elif block_num < 76:
            return 'm'
        elif block_num < 85:
            return 'N'
        elif block_num < 88:
            return 'O'
        elif block_num < 97:
            return 'P'
        elif block_num < 100:
            return 'Q'
        elif block_num == 100:
            return 'R'
        elif block_num < 104:
            return 'S'
        elif block_num < 109:
            return 'T'
        elif block_num < 115:
            return 'U'
        elif block_num < 121:   
            return 'V'
        elif block_num < 143:
            return 'W'
        elif block_num < 146:
            return 'X'
        elif block_num < 149:
            return 'Y'  
        else:
            return 'Z'
    
    def get_all_strings(self,switch_state_enum, light_state_enum, gate_state_enum, failure_enum,id):

        if id in [13,28,57,63,77,85]:
            if id == 13 and switch_state_enum == 0:
                switch_state = "D13->A1"
            elif id == 13 and switch_state_enum == 1:
                switch_state = "D13->C12"
            elif id == 28 and switch_state_enum == 0:
                switch_state = "F28->G29"
            elif id == 28 and switch_state_enum == 1:
                switch_state = "F28->Z150"
            elif id == 57 and switch_state_enum == 0:
                switch_state = "I57->J58"
            elif id == 57 and switch_state_enum == 1:
                switch_state = "I57->Yard"
            elif id == 63 and switch_state_enum == 0:
                switch_state = "K63->Yard"
            elif id == 63 and switch_state_enum == 1:
                switch_state = "K63->J62"
            elif id == 77 and switch_state_enum == 0:
                switch_state = "N77->M76"
            elif id == 77 and switch_state_enum == 1:
                switch_state = "N77->R101"
            elif id == 85 and switch_state_enum == 0:
                switch_state = "N85->O86"
            elif id == 85 and switch_state_enum == 1:
                switch_state = "N85->Q100"
        else: 
            switch_state = "N/A"
        if id in [0,3,7,29,58,62,76,86,100,101,150,151]:
            #make sure is a string 
            
            
            if light_state_enum == "00":
                light_state = "Super Green"
            elif light_state_enum == "01":
                light_state = "Green"
            elif light_state_enum == "10":
                light_state = "Yellow"
            elif light_state_enum == "11":
                light_state = "Red"
        else:
            light_state = "N/A"
        #if id == 0:
            #light_state = "Green"
        if id in [19,108]:
            if gate_state_enum == 0:
                gate_state = "Down"
            elif gate_state_enum == 1:
                gate_state = "Up"
        else:
            gate_state = "N/A"
        if failure_enum == 0:
            failure = "No Failure"
        elif failure_enum == 1:
            failure = "Broken Track"
        elif failure_enum == 2:
            failure = "Power Failure"
        elif failure_enum == 3:
            failure = "Circuit Failure"
        
        return switch_state, light_state, gate_state, failure



def main():
    # Create first UI window (still a Tk)
    vital1 = sw_vital_check.sw_vital_check()
    controller1 = sw_wayside_controller.sw_wayside_controller(vital1, "Green_Line_PLC_XandLup.py")
    ui1 = sw_wayside_controller_ui(controller1)
    ui1.title("Wayside Controller 1")
    ui1.geometry("1200x800")

    # Create second UI window (another Tk)
    vital2 = sw_vital_check.sw_vital_check()
    controller2 = sw_wayside_controller.sw_wayside_controller(vital2, "Green_Line_PLC_XandLdown.py")
    #ui2 = sw_wayside_controller_ui(controller2)
    #ui2.title("Wayside Controller 2")
    #ui2.geometry("1200x800")

    # Bring both windows to front
    #ui1.lift()
    #ui2.lift()

    # Run *one* mainloop (both Tk windows share it)
    tk.mainloop()


if __name__ == "__main__":
    main()

