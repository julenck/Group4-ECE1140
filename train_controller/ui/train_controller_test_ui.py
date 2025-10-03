"""Test UI module for Train Controller simulation.

This module provides a graphical user interface for testing the Train Controller
functionality. It allows users to simulate various train inputs from the train
model and observe the outputs produced by the driver. The UI is divided into input controls for simulating
different conditions and output displays showing the Driver's commands in the driver UI.

The module interfaces with the train_database module to get the train states
between the test UI and the main train controller interface.

Typical usage example:
    python test_ui.py

Dependencies:
    - tkinter: For GUI components
    - train_database: For state persistence
"""

import tkinter as tk

from tkinter import ttk
import os
import sys

# Add parent directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Import database directly from models directory
from database.database import train_database


class train_controller_test_ui(tk.Tk):
    """Test interface for Train Controller module.
    
    This class provides a graphical interface for testing train controller
    functionality. It allows testers to:
        - Create and select multiple train instances
        - Set train parameters and simulate conditions
        - Monitor controller outputs and system status
        - Test failure scenarios and safety responses
    
    The interface is divided into two main sections:
        - Input Frame: For setting train parameters and conditions
        - Output Frame: For displaying controller responses and train status
    
    Attributes:
        db: train_database instance for train I/O information
        train_id_var: StringVar tracking current train selection
        train_selector: Combobox for train selection
        Various UI elements for inputs and outputs (entries, labels, etc.)
    """
    
    def __init__(self):
        """Initialize the test UI window and create interface elements.
        
        Sets up the main window, initializes database connection, and creates
        the input and output frames. Configures grid layout for responsive UI.
        """
        super().__init__()
        self.title("Train Controller Test UI")
        self.db = train_database()
        
        # Create main frames
        self.create_input_frame()
        self.create_output_frame()
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
    
    def create_input_frame(self):
        """Create and configure the input control frame.
        
        Creates a frame containing all input controls for train simulation:
            - Train selection and creation
            - Speed and authority settings
            - Station and beacon information
            - Brake controls
            - Failure simulation switches
        
        The frame is organized in a grid layout with labeled sections for
        different types of controls.
        """
        input_frame = ttk.LabelFrame(self, text="Force Inputs")
        input_frame.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)


        # Train selection
        train_frame = ttk.Frame(input_frame)
        train_frame.grid(row=0, column=0, columnspan=2, pady=5)
        
        ttk.Label(train_frame, text="Select Train ID:").grid(row=0, column=0, padx=5)
        self.train_id_var = tk.StringVar()
        self.train_selector = ttk.Combobox(train_frame, textvariable=self.train_id_var, state="readonly", width=10)
        self.train_selector.grid(row=0, column=1, padx=5)
        

        ttk.Button(train_frame, text="New Train", command=self.add_new_train).grid(row=0, column=2, padx=5)
        
        # Update train list
        self.update_train_list()
        
        # Bind selection change event
        self.train_selector.bind('<<ComboboxSelected>>', self.on_train_selected)
        
        # Input fields
        self.commanded_speed_entry = self.make_entry_text(input_frame, "Commanded Speed (mph)", 1, "30")
        self.speed_limit_entry = self.make_entry_text(input_frame, "Speed Limit (mph)", 2, "40")
        self.commanded_authority_entry = self.make_entry_text(input_frame, "Commanded Authority (yds)", 3, "5")
        self.train_velocity_entry = self.make_entry_text(input_frame, "Train Velocity (mph)", 4, "30")
        self.next_stop_beacon_entry = self.make_entry_text(input_frame, "Next Station (for announcements)", 5, "Herron Ave")
        self.station_side_beacon_entry = self.make_entry_dropdown(input_frame, "Station Door Side", 6, ["left", "right"])
        self.current_temperature_entry = self.make_entry_text(input_frame, "Train Temperature (°F)", 7, "70")
        self.service_brake_entry = self.make_entry_text(input_frame, "Service Brake (%)", 8, "30")
        self.emergency_brake_entry = self.make_entry_dropdown(input_frame, "Emergency Brake", 9, ["on", "off"], "off")
        self.train_engine_failure_entry = self.make_entry_dropdown(input_frame, "Train Engine Failure", 10, ["True", "False"], "False")
        self.signal_pickup_failure_entry = self.make_entry_dropdown(input_frame, "Signal Pickup Failure", 11, ["True", "False"], "False")
        self.brake_failure_entry = self.make_entry_dropdown(input_frame, "Brake Failure", 12, ["True", "False"], "False")

        # Simulate button
        ttk.Button(input_frame, text="Simulate", command=self.simulate).grid(row=12, column=2, columnspan=2, pady=10)

    def create_output_frame(self):
        """Create the output frame showing signals sent to Train Model from the driver."""
        output_frame = ttk.LabelFrame(self, text="Outputs to Train Model")
        output_frame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)
        
        # Status section
        status_frame = ttk.LabelFrame(output_frame, text="Status Information")
        status_frame.grid(row=0, column=0, sticky="NSEW", padx=5, pady=5)
        
        # set speed and power, the set speed is the speed the driver is setting with his controls,
        # power command is a value calculated internally based on Kp, Ki, driver set speed (aka Vcmd), and Velocity provided by the train
        self.set_speed = self.make_output(status_frame, "Set Speed (mph)", 0)
        self.power_command = self.make_output(status_frame, "Power Command (W)", 1)
        
        # Braking section
        brake_frame = ttk.LabelFrame(output_frame, text="Brake Status")
        brake_frame.grid(row=2, column=0, sticky="NSEW", padx=5, pady=5)
        self.emergency_brake_status = self.make_output(brake_frame, "Emergency Brake", 0)
        self.service_brake_status = self.make_output(brake_frame, "Service Brake %", 1)
        
        # Station control section
        station_frame = ttk.LabelFrame(output_frame, text="Station Controls")
        station_frame.grid(row=3, column=0, sticky="NSEW", padx=5, pady=5)
        self.announcement_status = self.make_output(station_frame, "Current Announcement", 0)
        self.right_door_status = self.make_output(station_frame, "Right Door Status", 1)
        self.left_door_status = self.make_output(station_frame, "Left Door Status", 2)
        
        # Environmental controls section
        env_frame = ttk.LabelFrame(output_frame, text="Environmental Controls")
        env_frame.grid(row=4, column=0, sticky="NSEW", padx=5, pady=5)
        self.lights_status = self.make_output(env_frame, "Lights Status", 0)
        self.current_temperature_status = self.make_output(env_frame, "Current Temperature (°F)", 1)

    def make_entry_text(self, parent, label, row, default=""):
        """Create a labeled text entry field.
        
        Args:
            parent: Parent widget to contain the entry
            label: String label for the entry field
            row: Grid row number for placement
            default: Default value for the entry (default: "")
            
        Returns:
            ttk.Entry: The created entry widget
        """
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=5)
        entry = ttk.Entry(parent)
        entry.insert(0, default)
        entry.grid(row=row, column=1, padx=5, pady=5)
        return entry
    
    def make_entry_dropdown(self, parent, label, row, values, default=None):
        """Create a labeled dropdown (combobox) field.
        
        Args:
            parent: Parent widget to contain the dropdown
            label: String label for the dropdown
            row: Grid row number for placement
            values: List of string values for the dropdown
            default: Default selected value (default: first value in list)
            
        Returns:
            ttk.Combobox: The created combobox widget
        """
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=5)
        combo = ttk.Combobox(parent, values=values, state="readonly")
        if default is not None:
            combo.set(default)
        else:
            combo.set(values[0])
        combo.grid(row=row, column=1, padx=5, pady=5)
        return combo

    def make_output(self, parent, label, row):
        """Create a labeled output display field.
        
        Args:
            parent: Parent widget to contain the output display
            label: String label for the output field
            row: Grid row number for placement
            
        Returns:
            ttk.Label: The created label widget for displaying values
        """
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=5)
        value_label = ttk.Label(parent, text="---")
        value_label.grid(row=row, column=1, padx=5, pady=5)
        return value_label

    def update_train_list(self):
        """Update the train selector dropdown with current train IDs.
        
        Retrieves the list of train IDs from the database and updates the
        train selector combobox. If there are trains and none is selected,
        selects the first train in the list.
        """
        train_ids = train_database.get_all_train_ids(self.db)
        
        self.train_selector['values'] = train_ids
        if train_ids and not self.train_selector.get():
            self.train_selector.set(train_ids[0])
            
    def add_new_train(self):
        """Create a new train instance with default initial state.
        Creates a new train entry in the database so that we can test a HW train and
        a SW train without having to implement 2 different test UI's with a unique ID and
        default initial parameter values. Updates the train selector and
        automatically selects the new train.
        
        Initial state includes:
            - Default speeds (30 mph)
            - Default authority (30 yds)
            - Default station (Herron Ave, right side)
            - All systems functioning (no failures)
        """
        # Get existing train IDs
        existing_ids = self.db.get_all_train_ids()
        # Create new ID (max + 1, or 1 if no trains exist)
        new_id = max(existing_ids) + 1 if existing_ids else 1
        
        # Create initial state for new train
        initial_state = {
            'commanded_speed': "30",
            'speed_limit': "40",
            'commanded_authority': "30",
            'velocity': "30",
            'next_stop': "Herron Ave",
            'station_side': "right",
            'train_temperature': "70",
            'service_brake': "30",
            'emergency_brake': "off",
            'engine_failure': "False",
            'signal_failure': "False",
            'brake_failure': "False"
        }
        
        # Add new train to database
        self.db.update_train_state(new_id, initial_state)
        
        # Update train list and select new train
        self.update_train_list()
        self.train_selector.set(new_id)
        self.on_train_selected(None)
        
    def on_train_selected(self, event):
        """Handle train selection change event.
        
        Updates all input fields with the current state of the selected train
        from the database.
        
        Args:
            event: The selection event (not used, can be None)
        """
        train_id = int(self.train_selector.get())
        state = self.db.get_train_state(train_id)
        if state:
            # Update input fields with current train state
            self.commanded_speed_entry.delete(0, tk.END)
            self.commanded_speed_entry.insert(0, str(state[1]))  # commanded_speed
            # ... update other fields similarly
            
    def simulate(self):
        """Run a simulation step with current input values.
        
        Collects all current input values, updates the train state in the
        database, and refreshes the output display. This simulates one
        control cycle of the train controller.
        
        The simulation includes:
            - Speed and authority parameters
            - Station and beacon information
            - Brake settings
            - System failure states
            
        Does nothing if no train is selected.
        """
        if not self.train_selector.get():
            return
            
        train_id = int(self.train_selector.get())
        # Collect all input values
        state_dict = {
            'commanded_speed': self.commanded_speed_entry.get(),
            'speed_limit': self.speed_limit_entry.get(),
            'commanded_authority': self.commanded_authority_entry.get(),
            'velocity': self.train_velocity_entry.get(),
            'next_stop': self.next_stop_beacon_entry.get(),
            'station_side': self.station_side_beacon_entry.get(),
            'train_temperature': self.current_temperature_entry.get(),
            'service_brake': self.service_brake_entry.get(),
            'emergency_brake': self.emergency_brake_entry.get(),
            'engine_failure': self.train_engine_failure_entry.get(),
            'signal_failure': self.signal_pickup_failure_entry.get(),
            'brake_failure': self.brake_failure_entry.get()
        }
        
        # Update database with current train ID
        self.db.update_train_state(train_id, state_dict)
        
        # Update output display
        self.update_outputs(state_dict)

    def update_outputs(self, state_dict):
        """Update all output displays with current state values.
        
        Updates all output fields in the interface to reflect the current
        train state. Handles missing values by using appropriate defaults.
        
        Args:
            state_dict: Dictionary containing the current train state values:
                - Speed and power values
                - Brake status
                - Door controls
                - Environmental controls
                - System failures
                
        The method updates:
            - Speed and power displays
            - Brake status indicators
            - Door status based on station side
            - Station announcements
            - Environmental control status
            - System failure indicators
        """
        # Update speed and power
        self.set_speed.config(text=f"{state_dict.get('set_speed', '0')} mph")
        self.power_command.config(text=f"{state_dict.get('power_command', '0')} W")
        
        # Update brake status
        self.emergency_brake_status.config(text=state_dict.get('emergency_brake', 'off').upper())
        self.service_brake_status.config(text=f"{state_dict.get('service_brake', '0')}%")
        
        # # Update door status based on station side this should only update based on the driver input
        # if state_dict.get('station_side') == 'left':
        #     self.left_door_status.config(text="OPEN")
        #     self.right_door_status.config(text="CLOSED")
        # else:  # default to right if not specified
        #     self.left_door_status.config(text="CLOSED")
        #     self.right_door_status.config(text="OPEN")
        
        # Update station announcement
        self.announcement_status.config(text=state_dict.get('next_stop', 'No announcement'))
        
        # Update environmental controls
        self.lights_status.config(text=str(state_dict.get('lights', 'OFF')).upper())
        
        # Handle temperature controls
        current_temp = int(self.current_temperature_entry.get())
        if state_dict.get('temperature_up') == "True":
            current_temp += 1
        if state_dict.get('temperature_down') == "True":
            current_temp -= 1
        # Show temperature controls status
        self.current_temperature_status.config(text=f"{current_temp}°F")

if __name__ == "__main__":
    app = train_controller_test_ui()
    app.mainloop()