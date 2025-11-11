"""Train Controller API module for state management and module communication.

This module handles data persistence using JSON files and provides interfaces
for communication between Train Controller and Train Model modules.
"""

import json
import os
from typing import Dict, Optional

class train_controller_api:
    """Manages train state persistence and module communication using JSON."""
    
    def __init__(self, train_id=None):
        """Initialize API with default state.
        
        Args:
            train_id: Optional train ID for multi-train support. If None, uses root level (legacy).
        """
        self.train_id = train_id  # None means root level, otherwise use train_X
        
        # Create data directory in train_controller folder
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.data_dir = os.path.join(base_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.state_file = os.path.join(self.data_dir, "train_states.json")
        
        # Default state template
        self.train_states = {
            # Inputs FROM Train Model
            'commanded_speed': 60.0,      # mph - realistic commanded speed
            'commanded_authority': 1000.0,   # yards - enough authority to move
            'speed_limit': 60.0,         # mph - realistic speed limit
            'train_velocity': 0.0,             # mph - train starts at rest
            'next_stop': 'Station A',             # station name
            'station_side': 'Right',     # left/right
            'train_temperature': 70.0,   # °F - comfortable room temperature
            'engine_failure': False,
            'signal_failure': False,
            'brake_failure': False,
            'manual_mode': False,       # manual/automatic mode
            
            # Internal Train Controller State
            'driver_velocity': 0.0,           # mph - driver's set speed, will be initialized to match commanded_speed
            'service_brake': False,         # boolean
            'right_door': False,        # door state
            'left_door': False,         # door state
            'interior_lights': True,   # interior lights state - on by default
            'exterior_lights': True,   # exterior lights state - on by default
            'set_temperature': 70.0,     # Driver's desired temperature (°F) - will be initialized to match train_temperature
            'temperature_up': False,    # temperature control
            'temperature_down': False,   # temperature control
            'announcement': '',         # current announcement
            'announce_pressed': False,  # tracks if announcement button is pressed
            'emergency_brake': False,   # emergency brake state
            'kp': 0.0,                  # proportional gain - default to 0 until set by user
            'ki': 0.0,                  # integral gain - default to 0 until set by user
            'engineering_panel_locked': False,  # engineering panel state
            
            # Outputs TO Train Model
            'power_command': 0.0,        # power in Watts
        }
        
        # Initialize state file if it doesn't exist or is empty/malformed
        try:
            if not os.path.exists(self.state_file) or os.path.getsize(self.state_file) == 0:
                # Initialize default state with matched values
                initial_state = self.train_states.copy()
                initial_state['driver_velocity'] = initial_state['commanded_speed']
                initial_state['set_temperature'] = initial_state['train_temperature']
                self.save_state(initial_state)
            else:
                # Validate existing file
                with open(self.state_file, 'r') as f:
                    try:
                        current_state = json.load(f)
                        # Ensure all required fields are present
                        for key in self.train_states:
                            if key not in current_state:
                                current_state[key] = self.train_states[key]
                        # Always ensure driver_velocity and set_temperature match their inputs if not set
                        if 'driver_velocity' not in current_state:
                            current_state['driver_velocity'] = current_state['commanded_speed']
                        if 'set_temperature' not in current_state:
                            current_state['set_temperature'] = current_state['train_temperature']
                        self.save_state(current_state)
                    except json.JSONDecodeError:
                        # File exists but is malformed, overwrite with defaults
                        initial_state = self.train_states.copy()
                        initial_state['driver_velocity'] = initial_state['commanded_speed']
                        initial_state['set_temperature'] = initial_state['train_temperature']
                        self.save_state(initial_state)
        except Exception as e:
            print(f"Error initializing state file: {e}")
            # Ensure we have a valid state file with proper initialization
            initial_state = self.train_states.copy()
            initial_state['driver_velocity'] = initial_state['commanded_speed']
            initial_state['set_temperature'] = initial_state['train_temperature']
            self.save_state(initial_state)

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
                        all_states = json.load(f)
                        
                        # If train_id is specified, read from train_X section
                        if self.train_id is not None:
                            train_key = f"train_{self.train_id}"
                            if train_key in all_states:
                                return all_states[train_key]
                            else:
                                # Return default state if train section doesn't exist
                                default = self.train_states.copy()
                                default['train_id'] = self.train_id
                                return default
                        else:
                            # Legacy mode: read from root level
                            return all_states
                    except json.JSONDecodeError as e:
                        print(f"Error reading state file: {e}")
                        # Reset to default state if file is corrupted
                        self.save_state(self.train_states)
            return self.train_states.copy()
        except Exception as e:
            print(f"Error accessing state file: {e}")
            return self.train_states.copy()

    def save_state(self, state: dict) -> None:
        """Save train state to file.
        
        Args:
            state: Complete state dictionary to save
            
        The method ensures all required fields are present in the state
        by merging with default values for any missing fields.
        """
        try:
            # Ensure all default fields are present
            complete_state = self.train_states.copy()
            complete_state.update(state)
            if self.train_id is not None:
                complete_state['train_id'] = self.train_id
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            
            if self.train_id is not None:
                # Multi-train mode: update specific train's section at ROOT level only
                if os.path.exists(self.state_file):
                    with open(self.state_file, 'r') as f:
                        all_states = json.load(f)
                else:
                    all_states = {}
                
                # IMPORTANT: Only update at root level, never nested
                # Remove any nested train_X keys from complete_state to prevent nesting
                clean_state = {}
                for key, value in complete_state.items():
                    # Skip nested train_X sections and only keep actual state data
                    if not (key.startswith('train_') and isinstance(value, dict)):
                        clean_state[key] = value
                    elif key == f"train_{self.train_id}":  # Keep train_id field
                        clean_state['train_id'] = self.train_id
                
                train_key = f"train_{self.train_id}"
                all_states[train_key] = clean_state
                
                with open(self.state_file, 'w') as f:
                    json.dump(all_states, f, indent=4)
            else:
                # Legacy mode: save to root level
                with open(self.state_file, 'w') as f:
                    json.dump(complete_state, f, indent=4)

        except Exception as e:
            print(f"Error saving state: {e}")
            # If all else fails, try direct write
            with open(self.state_file, 'w') as f:
                json.dump(self.train_states.copy(), f, indent=4)

    def reset_state(self) -> None:
        """Reset train state to default values."""
        self.save_state(self.train_states.copy())

    def read_train_data_json(self) -> Optional[Dict]:
        """Read the latest train_data.json directly from Train Model folder."""
        try:
            base_dir = os.path.dirname(os.path.dirname(__file__))  # train_controller/
            train_data_path = os.path.join(os.path.dirname(base_dir), "Train Model", "train_data.json")

            print(f"[DEBUG] Reading Train Model data from: {train_data_path}")

            if not os.path.exists(train_data_path):
                print("[TrainControllerAPI] train_data.json not found in Train Model folder.")
                return None

            with open(train_data_path, 'r') as f:
                data = json.load(f)
            return data

        except json.JSONDecodeError:
            print("[TrainControllerAPI] Invalid JSON format in train_data.json.")
            return None
        except Exception as e:
            print(f"[TrainControllerAPI] Error reading train_data.json: {e}")
            return None

    def update_from_train_data(self) -> None:
        """Read and update controller state directly from Train Model's train_data.json."""
        data = self.read_train_data_json()
        if not data:
            print("[TrainControllerAPI] No valid data read from Train Model.")
            return

        # === Map relevant keys from train_data.json ===
        inputs = data.get("inputs", {})
        outputs = data.get("outputs", {})

        mapped_data = {
            'commanded_speed': inputs.get('commanded speed', 0.0),
            'commanded_authority': inputs.get('commanded authority', 0.0),
            'speed_limit': inputs.get('speed limit', 0.0),
            'train_velocity': outputs.get('velocity_mph', 0.0),
            'train_temperature': outputs.get('temperature_F', 70.0),
            'engine_failure': inputs.get('engine_failure', False),
            'signal_failure': inputs.get('signal_failure', False),
            'brake_failure': inputs.get('brake_failure', False),
            'manual_mode': inputs.get('manual_mode', False),
        }

        # Update controller state
        self.receive_from_train_model(mapped_data)
        print("[TrainControllerAPI] State successfully updated from Train Model train_data.json.")

    def receive_from_train_model(self, data: dict) -> None:
        """Receive updates from Train Model.
        
        Args:
            data: Dictionary containing Train Model outputs
        """
        # Get current state to check if speed/temperature are changing
        current_state = self.get_state()
        
        # Filter relevant data from train model
        relevant_data = {
            k: v for k, v in data.items() 
            if k in ['commanded_speed', 'commanded_authority', 'speed_limit',
                    'train_velocity', 'next_stop', 'station_side', 'train_temperature',
                    'engine_failure', 'signal_failure', 'brake_failure', 'manual_mode']
        }
        
        # If commanded_speed is changing and driver_velocity matches old commanded_speed,
        # update driver_velocity to match new commanded_speed
        if ('commanded_speed' in relevant_data and 
            current_state['driver_velocity'] == current_state['commanded_speed']):
            relevant_data['driver_velocity'] = relevant_data['commanded_speed']
            
        # If train_temperature is changing and set_temperature matches old train_temperature,
        # update set_temperature to match new train_temperature
        if ('train_temperature' in relevant_data and 
            current_state['set_temperature'] == current_state['train_temperature']):
            relevant_data['set_temperature'] = relevant_data['train_temperature']
            
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
            'interior_lights': state['interior_lights'],
            'exterior_lights': state['exterior_lights'],
            'temperature_up': state['temperature_up'],
            'temperature_down': state['temperature_down']
        }

if __name__ == "__main__":
    api = train_controller_api()
    api.update_from_train_data()
