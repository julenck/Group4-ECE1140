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
        
        self.state_file = os.path.join(self.data_dir, "train_states.json")
        
        # Default state template
        self.train_states = {
            # Inputs FROM Train Model
            'commanded_speed': 0.0,      # mph
            'commanded_authority': 0.0,   # yards
            'speed_limit': 0.0,         # mph
            'train_velocity': 0.0,             # mph
            'next_stop': '',             # station name
            'station_side': '',     # left/right
            'train_temperature': 0.0,   # °F
            'engine_failure': False,
            'signal_failure': False,
            'brake_failure': False,
            'manual_mode': False,       # manual/automatic mode
            
            # Internal Train Controller State
            'driver_velocity': 0.0,           # mph - driver's set speed, will be initialized to match commanded_speed
            'service_brake': 0,         # percentage (0-100)
            'right_door': False,        # door state
            'left_door': False,         # door state
            'interior_lights': False,   # interior lights state
            'exterior_lights': False,   # exterior lights state
            'set_temperature': 0.0,     # Driver's desired temperature (°F) - will be initialized to match train_temperature
            'temperature_up': False,    # temperature control
            'temperature_down': False,   # temperature control
            'announcement': '',         # current announcement
            'announce_pressed': False,  # tracks if announcement button is pressed
            'emergency_brake': False,   # emergency brake state
            'kp': 0.0,                 # proportional gain
            'ki': 0.0,                 # integral gain
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
                        return json.load(f)
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
                json.dump(self.train_states.copy(), f, indent=4)

    def reset_state(self) -> None:
        """Reset train state to default values."""
        self.save_state(self.train_states.copy())

    def read_train_model_file(self) -> Optional[Dict]:
        """Read the latest Train Model output JSON (train_to_controller.json)."""
        try:
            base_dir = os.path.dirname(os.path.dirname(__file__))  # train_controller/
            train_model_path = os.path.join(os.path.dirname(base_dir), "Train Model", "train_to_controller.json")

            print(f"[DEBUG] Looking for JSON at: {train_model_path}")

            if not os.path.exists(train_model_path):
                print("[TrainControllerAPI] train_to_controller.json not found.")
                return None

            with open(train_model_path, 'r') as f:
                data = json.load(f)
            return data

        except json.JSONDecodeError:
            print("[TrainControllerAPI] Invalid JSON format in train_to_controller.json.")
            return None
        except Exception as e:
            print(f"[TrainControllerAPI] Error reading train_to_controller.json: {e}")
            return None
        
    def map_train_model_data(self, raw: Dict) -> Dict:
        """Map Train Model JSON keys to Controller expected format."""
        mapped = {
            'commanded_speed': raw.get('commanded_speed_mph', 0.0),
            'commanded_authority': raw.get('commanded_authority_yds', 0.0),
            'train_velocity': raw.get('train_velocity_mph', 0.0),
            'train_temperature': raw.get('train_temperature_F', 0.0),
            'emergency_brake': raw.get('emergency_brake', False)
        }

        failure_modes = raw.get('failure_modes', {})
        mapped.update({
            'engine_failure': failure_modes.get('engine_failure', False),
            'signal_failure': failure_modes.get('signal_pickup_failure', False),
            'brake_failure': failure_modes.get('brake_failure', False),
        })

        return mapped
    
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

    raw_data = api.read_train_model_file()
    if raw_data:
        mapped_data = api.map_train_model_data(raw_data)
        api.receive_from_train_model(mapped_data)
        print("[Controller] State updated from Train Model")
    else:
        print("[Controller] No Train Model data found.")
