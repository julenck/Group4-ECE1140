"""Train Controller API module for state management and module communication.

This module handles data persistence using JSON files and provides interfaces
for communication between Train Controller and Train Model modules.
"""

import json
import os
from typing import Dict, Optional

class train_controller_api:
    """Manages train state persistence and module communication using JSON."""
    
    def __init__(self):
        """Initialize API with default state."""
        # Create data directory in train_controller folder
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.data_dir = os.path.join(base_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.state_file = os.path.join(self.data_dir, "train_state.json")
        
        # Default state template
        self.default_state = {
            # Inputs FROM Train Model
            'commanded_speed': 0.0,      # mph
            'commanded_authority': 0.0,   # yards
            'speed_limit': 40.0,         # mph
            'velocity': 0.0,             # mph
            'next_stop': '',             # station name
            'station_side': 'right',     # left/right
            'train_temperature': 70,     # °F
            'engine_failure': False,
            'signal_failure': False,
            'brake_failure': False,
            
            # Internal Train Controller State
            'set_speed': 'commanded_speed',           # mph
            'service_brake': 0,         # percentage
            'right_door': False,
            'left_door': False,
            'lights': False,
            'set_temperature': 70,      # Driver's desired temperature (°F)
            'temperature_up': False,
            'temperature_down': False,
            'announcement': '',
            'emergency_brake': False,
            'kp': 0.0,
            'ki': 0.0,
            'engineering_panel_locked': False,
            
            # Outputs TO Train Model
            'power_command': 0.0,        # W
        }
        
        # Initialize state file if it doesn't exist or is empty/malformed
        try:
            if not os.path.exists(self.state_file) or os.path.getsize(self.state_file) == 0:
                self.save_state(self.default_state)
            else:
                # Validate existing file
                with open(self.state_file, 'r') as f:
                    try:
                        json.load(f)
                    except json.JSONDecodeError:
                        # File exists but is malformed, overwrite with defaults
                        self.save_state(self.default_state)
        except Exception as e:
            print(f"Error initializing state file: {e}")
            # Ensure we have a valid state file
            self.save_state(self.default_state)

    def update_state(self, state_dict: dict) -> None:
        """Update train state with new values.
        
        Args:
            state_dict: Dictionary containing updated values
        """
        current_state = self.get_state()
        current_state.update(state_dict)
        self.save_state(current_state)

    def get_state(self) -> dict:
        """Get current train state.
        
        Returns:
            dict: Current state of the train. Returns default state if there are any issues.
        """
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    try:
                        return json.load(f)
                    except json.JSONDecodeError as e:
                        print(f"Error reading state file: {e}")
                        # Reset to default state if file is corrupted
                        self.save_state(self.default_state)
            return self.default_state.copy()
        except Exception as e:
            print(f"Error accessing state file: {e}")
            return self.default_state.copy()

    def save_state(self, state: dict) -> None:
        """Save train state to file.
        
        Args:
            state: Complete state dictionary to save
            
        The method ensures all required fields are present in the state
        by merging with default values for any missing fields.
        """
        try:
            # Ensure all default fields are present
            complete_state = self.default_state.copy()
            complete_state.update(state)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            
            # Write state atomically using a temporary file
            temp_file = self.state_file + '.tmp'
            with open(temp_file, 'w') as f:
                json.dump(complete_state, f, indent=4)
            
            # Rename temp file to actual file (atomic operation)
            os.replace(temp_file, self.state_file)
        except Exception as e:
            print(f"Error saving state: {e}")
            # If all else fails, try direct write
            with open(self.state_file, 'w') as f:
                json.dump(self.default_state.copy(), f, indent=4)

    def receive_from_train_model(self, data: dict) -> None:
        """Receive updates from Train Model.
        
        Args:
            data: Dictionary containing Train Model outputs
        """
        relevant_data = {
            k: v for k, v in data.items() 
            if k in ['commanded_speed', 'commanded_authority', 'speed_limit',
                    'velocity', 'next_stop', 'station_side', 'train_temperature',
                    'engine_failure', 'signal_failure', 'brake_failure']
        }
        self.update_state(relevant_data)

    def send_to_train_model(self) -> dict:
        """Send control outputs to Train Model.
        
        Returns:
            dict: Control outputs for Train Model
        """
        state = self.get_state()
        return {
            'power_command': state['power_command'],
            'service_brake': state['service_brake'],
            'emergency_brake': state['emergency_brake'],
            'right_door': state['right_door'],
            'left_door': state['left_door'],
            'lights': state['lights'],
            'temperature_up': state['temperature_up'],
            'temperature_down': state['temperature_down']
        }