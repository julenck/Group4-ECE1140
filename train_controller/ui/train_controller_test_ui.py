"""Test UI module for Train Controller simulation.

This module provides a graphical user interface for testing the Train Controller
functionality. It allows users to simulate train inputs from the train model and 
observe the outputs produced by the driver. The UI is divided into input controls 
for simulating different conditions and displays showing the Driver's 
commands in the driver UI.

The module interfaces with the train_controller_api module to handle state management
and communication with the Train Model.

Typical usage example:
    python test_ui.py 

Dependencies:
    - tkinter: For GUI components
    - train_controller_api: For state management and Train Model communication
"""

import tkinter as tk
from tkinter import ttk
import os
import sys

# Add parent directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Import API from api directory
from api.train_controller_api import train_controller_api


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
        
        Sets up the main window, initializes API connection, and creates
        the input and output frames. Configures grid layout for responsive UI.
        """
        super().__init__()
        self.title("Train Controller Test UI")
        self.api = train_controller_api()
        
        # Create main frames
        self.create_input_frame()
        self.create_output_frame()
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Start periodic updates of driver outputs
        self.update_interval = 500  # 500ms = 0.5 seconds
        self.periodic_update()
    
    def periodic_update(self):
        """Update the output displays periodically to show current driver commands."""
        try:
            # Get both the full state and driver outputs
            state = self.api.get_state()
            driver_outputs = self.api.send_to_train_model()
            
            # Combine them to show complete status
            display_state = {
                'driver_velocity': state['driver_velocity'],
                'power_command': driver_outputs['power_command'],
                'emergency_brake': driver_outputs['emergency_brake'],
                'service_brake': driver_outputs['service_brake'],
                'left_door': driver_outputs['left_door'],
                'right_door': driver_outputs['right_door'],
                'interior_lights': driver_outputs['interior_lights'],
                'exterior_lights': driver_outputs['exterior_lights'],
                'set_temperature': state['set_temperature'],
                'next_stop': state['next_stop'],
                'station_side': state['station_side'],
                'announce_pressed': state['announce_pressed'],
                'manual_mode': state['manual_mode']
            }
            
            self.update_outputs(display_state)
        except Exception as e:
            print(f"Update error: {e}")
        finally:
            # Schedule next update
            self.after(self.update_interval, self.periodic_update)
    
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
        
        # Input fields
        self.commanded_speed_entry = self.make_entry_text(input_frame, "Commanded Speed (mph)", 1, "30")
        self.speed_limit_entry = self.make_entry_text(input_frame, "Speed Limit (mph)", 2, "40")
        self.commanded_authority_entry = self.make_entry_text(input_frame, "Commanded Authority (yds)", 3, "5")
        self.train_velocity_entry = self.make_entry_text(input_frame, "Train Velocity (mph)", 4, "30")
        self.next_stop_beacon_entry = self.make_entry_text(input_frame, "Next Station (for announcements)", 5, "Herron Ave")
        self.station_side_beacon_entry = self.make_entry_dropdown(input_frame, "Station Door Side", 6, ["left", "right"])
        self.current_temperature_entry = self.make_entry_text(input_frame, "Train Temperature (°F)", 7, "70")
        self.train_engine_failure_entry = self.make_entry_dropdown(input_frame, "Train Engine Failure", 8, ["True", "False"], "False")
        self.signal_pickup_failure_entry = self.make_entry_dropdown(input_frame, "Signal Pickup Failure", 9, ["True", "False"], "False")
        self.brake_failure_entry = self.make_entry_dropdown(input_frame, "Brake Failure", 10, ["True", "False"], "False")
        self.manual_mode_entry = self.make_entry_dropdown(input_frame, "Manual Mode", 11, ["True", "False"], "False")

        # Simulate button
        ttk.Button(input_frame, text="Simulate", command=self.simulate).grid(row=12, column=2, columnspan=2, pady=10)

    def create_output_frame(self):
        """Create the output frame showing signals sent to Train Model from the driver."""
        output_frame = ttk.LabelFrame(self, text="Outputs to Train Model")
        output_frame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)
        
        # Status section
        status_frame = ttk.LabelFrame(output_frame, text="Status Information")
        status_frame.grid(row=0, column=0, sticky="NSEW", padx=5, pady=5)
        
        # Driver velocity and power, the driver velocity is the speed the driver is setting with his controls,
        # power command is a value calculated internally based on Kp, Ki, driver velocity (aka Vcmd), and train velocity provided by the train
        self.driver_velocity = self.make_output(status_frame, "Driver Velocity (mph)", 0)
        self.power_command = self.make_output(status_frame, "Power Command (W)", 1)
        self.manual_mode_status = self.make_output(status_frame, "Manual Mode", 2)
        
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
        self.exterior_lights_status = self.make_output(env_frame, "Exterior Lights Status", 0)
        self.interior_lights_status = self.make_output(env_frame, "Interior Lights Status", 1)
        self.set_temperature_status = self.make_output(env_frame, "Set Temperature (°F)", 2)

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

    def reset_to_defaults(self):
        """Reset all input fields to default values."""
        defaults = {
            'commanded_speed': "30",
            'speed_limit': "40",
            'commanded_authority': "30",
            'velocity': "30",
            'next_stop': "Herron Ave",
            'station_side': "right",
            'train_temperature': "70",
            'engine_failure': "False",
            'signal_failure': "False",
            'brake_failure': "False"
        }
        
        # Reset all input fields
        self.commanded_speed_entry.delete(0, tk.END)
        self.commanded_speed_entry.insert(0, defaults['commanded_speed'])
        
        self.speed_limit_entry.delete(0, tk.END)
        self.speed_limit_entry.insert(0, defaults['speed_limit'])
        
        self.commanded_authority_entry.delete(0, tk.END)
        self.commanded_authority_entry.insert(0, defaults['commanded_authority'])
        
        self.train_velocity_entry.delete(0, tk.END)
        self.train_velocity_entry.insert(0, defaults['velocity'])
        
        self.next_stop_beacon_entry.delete(0, tk.END)
        self.next_stop_beacon_entry.insert(0, defaults['next_stop'])
        
        self.station_side_beacon_entry.set(defaults['station_side'])
        
        self.current_temperature_entry.delete(0, tk.END)
        self.current_temperature_entry.insert(0, defaults['train_temperature'])
        
        self.train_engine_failure_entry.set(defaults['engine_failure'])
        self.signal_pickup_failure_entry.set(defaults['signal_failure'])
        self.brake_failure_entry.set(defaults['brake_failure'])
            
    def simulate(self):
        """Run a simulation step with current input values.
        
        Collects all current input values and sends them to the Train Controller
        via the API. This simulates one control cycle of the train controller.
        Only sends values that would come from the Train Model, maintaining
        separation between Train Model inputs and Driver UI controls.
        """
        try:
            # Collect only Train Model inputs
            state_dict = {
                # Speed and authority values from wayside/track
                'commanded_speed': float(self.commanded_speed_entry.get()),
                'speed_limit': float(self.speed_limit_entry.get()),
                'commanded_authority': float(self.commanded_authority_entry.get()),
                'train_velocity': float(self.train_velocity_entry.get()),
                
                # Station and beacon information
                'next_stop': self.next_stop_beacon_entry.get(),
                'station_side': self.station_side_beacon_entry.get(),
                
                # Environmental readings
                'train_temperature': float(self.current_temperature_entry.get()),
                
                # System failures
                'engine_failure': self.train_engine_failure_entry.get() == "True",
                'signal_failure': self.signal_pickup_failure_entry.get() == "True",
                'brake_failure': self.brake_failure_entry.get() == "True",
                
                # Operation mode
                'manual_mode': self.manual_mode_entry.get() == "True"
            }
            
            # Send only Train Model inputs to the Train Controller
            self.api.receive_from_train_model(state_dict)
            
        except ValueError as e:
            print(f"Error converting values: {e}")
        except Exception as e:
            print(f"Simulation error: {e}")

    def update_outputs(self, state_dict):
        """Update all output displays with current state values.
        
        Updates all output fields in the interface to reflect what the Driver UI
        is sending to the Train Model, along with relevant state information.
        
        Args:
            state_dict: Dictionary containing the combined state values:
                - Driver-set values (set_speed, door controls, etc.)
                - Calculated values (power_command)
                - Current train state (temperature, announcements)
        """
        try:
            # Update speed and power displays (from driver controls)
            self.driver_velocity.config(text=f"{state_dict['driver_velocity']:.1f} mph")
            self.power_command.config(text=f"{state_dict['power_command']:.1f} W")
            self.manual_mode_status.config(text="MANUAL" if state_dict['manual_mode'] else "AUTOMATIC")
            
            # Update brake status (from driver controls)
            self.emergency_brake_status.config(
                text="ON" if state_dict['emergency_brake'] else "OFF",
            )
            self.service_brake_status.config(
                text=f"{state_dict['service_brake']:.1f}%"
            )
            
            # Update door status (from driver controls)
            self.left_door_status.config(
                text="OPEN" if state_dict['left_door'] else "CLOSED"
            )
            self.right_door_status.config(
                text="OPEN" if state_dict['right_door'] else "CLOSED"
            )
            
            # Update station announcement
            next_stop = state_dict['next_stop']
            # Only show announcement when announce button is pressed
            if state_dict['announce_pressed'] and next_stop:
                announcement = f"Next Stop: {next_stop}"
                if state_dict['station_side']:
                    announcement += f" ({state_dict['station_side']} side)"
            else:
                announcement = "No announcement"
            self.announcement_status.config(text=announcement)
            
            # Update environmental controls (from driver inputs)
            self.exterior_lights_status.config(
                text="ON" if state_dict['exterior_lights'] else "OFF"
            )
            self.interior_lights_status.config(
                text="ON" if state_dict['interior_lights'] else "OFF"
            )
            
            # Update temperature display
            self.set_temperature_status.config(
                text=f"{state_dict['set_temperature']:.1f}°F"
            )
            
        except Exception as e:
            print(f"Error updating outputs: {e}")

if __name__ == "__main__":
    app = train_controller_test_ui()
    app.mainloop()