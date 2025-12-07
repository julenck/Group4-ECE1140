"""Train Controller API module for state management and module communication.

This module handles data persistence using JSON files and provides interfaces
for communication between Train Controller and Train Model modules. 
"""

import json
import os
import threading
import tempfile
from typing import Dict, Optional

# Global file lock for thread-safe access to train_states.json
# Using RLock (reentrant lock) to allow same thread to acquire lock multiple times
_file_lock = threading.Lock()

def safe_write_json(filepath: str, data: dict) -> bool:
    """Thread-safe atomic JSON file write with validation.
    
    Writes to a temporary file first, then atomically renames to target.
    This prevents partial writes and race conditions.
    
    Args:
        filepath: Target JSON file path
        data: Dictionary to write as JSON
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Sort keys if writing to train_states.json
        if "train_states.json" in filepath and isinstance(data, dict):
            data = {k: data[k] for k in sorted(data.keys())}
        
        # Validate JSON structure by serializing first
        json_str = json.dumps(data, indent=4)
        
        # Count braces to ensure balance
        if json_str.count('{') != json_str.count('}'):
            print(f"[API] ERROR: Unbalanced braces in JSON data")
            return False
        
        # Write to temporary file in same directory
        dir_name = os.path.dirname(filepath)
        with tempfile.NamedTemporaryFile(mode='w', dir=dir_name, delete=False, suffix='.tmp') as tmp_file:
            tmp_file.write(json_str)
            tmp_path = tmp_file.name
        
        # Atomic rename (overwrites target file)
        # On Windows, os.replace() can fail with "Access Denied" if file is open
        # Use retry logic with brief delay
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if os.path.exists(filepath):
                    # On Windows, try to remove first if replace fails
                    try:
                        os.replace(tmp_path, filepath)
                        break  # Success!
                    except PermissionError:
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(0.01)  # Wait 10ms and retry
                            continue
                        else:
                            # Last attempt - try remove then rename
                            os.remove(filepath)
                            os.rename(tmp_path, filepath)
                            break
                else:
                    os.rename(tmp_path, filepath)
                    break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise  # Re-raise on last attempt
                import time
                time.sleep(0.01)
        
        return True
        
    except Exception as e:
        print(f"[API] ERROR: Failed to write {filepath}: {e}")
        # Clean up temp file if it exists
        try:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except:
            pass
        return False

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
        
        # Default state template with inputs/outputs sections
        self.default_inputs = {
            # Inputs FROM Train Model
            'commanded_speed': 0.0,
            'commanded_authority': 0.0,
            'speed_limit': 0.0,
            'train_velocity': 0.0,
            'current_station': '',
            'next_stop': '',
            'station_side': '',
            'train_temperature': 0.0,
            'train_model_engine_failure': False,
            'train_model_signal_failure': False,
            'train_model_brake_failure': False,
            'train_controller_engine_failure': False,
            'train_controller_signal_failure': False,
            'train_controller_brake_failure': False,
            'beacon_read_blocked': False,
        }
        
        # CRITICAL: Field order must match server and API client to prevent JSON reordering issues
        self.default_outputs = {
            # Outputs TO Train Model (Train Controller commands)
            'manual_mode': False,
            'driver_velocity': 0.0,
            'service_brake': False,
            'emergency_brake': False,
            'power_command': 0.0,
            'kp': None,  # Must be set through UI
            'ki': None,  # Must be set through UI
            'right_door': False,
            'left_door': False,
            'interior_lights': True,  # Default ON (matches server)
            'exterior_lights': True,  # Default ON (matches server)
            'set_temperature': 70.0,
            'temperature_up': False,
            'temperature_down': False,
            'announcement': '',
            'announce_pressed': False,
            'engineering_panel_locked': False,
        }
        
        # Legacy flat structure for backward compatibility
        self.train_states = {**self.default_inputs, **self.default_outputs}
        
        # Check if train state already exists before initializing
        # Only initialize if this is a NEW train
        # CRITICAL: Be conservative - if we can't determine if train exists, assume it DOES exist
        # This prevents accidentally resetting kp/ki to None due to file corruption or race conditions
        train_exists = False
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    existing_states = json.load(f)
                    if self.train_id is not None:
                        train_key = f"train_{self.train_id}"
                        train_exists = train_key in existing_states
                        # If train has kp/ki set in the file, definitely don't reinitialize!
                        if train_exists and isinstance(existing_states.get(train_key), dict):
                            train_dict = existing_states[train_key]
                            # Check both nested and flat formats
                            has_kp_ki = False
                            if 'outputs' in train_dict:
                                kp_val = train_dict['outputs'].get('kp')
                                ki_val = train_dict['outputs'].get('ki')
                                if kp_val is not None or ki_val is not None:
                                    has_kp_ki = True
                                    print(f"[API INIT] train_{self.train_id} has kp={kp_val}, ki={ki_val} - will NOT reinitialize")
                            elif 'kp' in train_dict or 'ki' in train_dict:
                                has_kp_ki = True
                                print(f"[API INIT] train_{self.train_id} has flat kp/ki - will NOT reinitialize")
                            if has_kp_ki:
                                train_exists = True  # Extra safety - never reinitialize if kp/ki are set!
                    else:
                        train_exists = bool(existing_states)
            except Exception as e:
                # If we can't read the file, assume train exists (conservative approach)
                # This prevents accidentally resetting kp/ki due to temporary file issues
                print(f"[API INIT] Warning: Could not read state file: {e} - assuming train exists to be safe")
                train_exists = True
        
        # Only initialize state file if train doesn't exist yet
        # This prevents overwriting existing state (lights, power_command, kp/ki, etc.)
        if not train_exists:
            try:
                print(f"[API INIT] Initializing NEW train_controller_api for train_id={train_id}")
                # Initialize default state with matched values
                initial_state = self.train_states.copy()
                initial_state['driver_velocity'] = initial_state['commanded_speed']
                initial_state['set_temperature'] = initial_state['train_temperature']
                # Ensure kp and ki are None (must be set through UI) - for new trains only!
                initial_state['kp'] = None
                initial_state['ki'] = None
                initial_state['interior_lights'] = True  # Default lights ON for new trains
                initial_state['exterior_lights'] = True
                print(f"[API INIT] Initializing new train with kp={initial_state['kp']}, ki={initial_state['ki']}")
                self.save_state(initial_state)
                print(f"[API INIT] State saved successfully")
            except Exception as e:
                print(f"[API INIT] Error initializing state file: {e}")
        else:
            if self.train_id is not None:
                print(f"[API INIT] train_{self.train_id} already exists - skipping initialization (preserves kp/ki)")
            else:
                print(f"[API INIT] Train already exists, preserving existing state")

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
            dict: Current state of the train (merged inputs + outputs). Returns default state if there are any issues.
        """
        with _file_lock:
            try:
                if os.path.exists(self.state_file):
                    # Retry up to 3 times to handle race conditions with other processes
                    for attempt in range(3):
                        try:
                            with open(self.state_file, 'r') as f:
                                all_states = json.load(f)
                                break  # Success!
                        except json.JSONDecodeError as e:
                            if attempt < 2:  # Retry on first 2 attempts
                                import time
                                time.sleep(0.01)  # Wait 10ms before retry
                                continue
                            else:  # Final attempt failed
                                print(f"[WARNING] JSON decode error after 3 attempts (race condition): {e}")
                                return self.train_states.copy()
                    else:
                        # This shouldn't happen, but just in case
                        return self.train_states.copy()
                    
                    # Successfully loaded all_states, now process it
                    try:
                            
                            # If train_id is specified, read from train_X section
                            if self.train_id is not None:
                                train_key = f"train_{self.train_id}"
                                if train_key in all_states:
                                    section = all_states[train_key]
                                    # Check if it has new inputs/outputs structure
                                    if 'inputs' in section and 'outputs' in section:
                                        # Merge defaults first, then inputs and outputs
                                        result = self.train_states.copy()
                                        result.update(section.get('inputs', {}))
                                        result.update(section.get('outputs', {}))
                                        return result
                                    else:
                                        # Old flat structure - merge with defaults
                                        result = self.train_states.copy()
                                        result.update(section)
                                        return result
                                else:
                                    # Return default state if train section doesn't exist
                                    default = self.train_states.copy()
                                    default['train_id'] = self.train_id
                                    return default
                            else:
                                # Legacy mode: read from root level, support both old and new structure
                                # CRITICAL FIX: If per-train structure exists, use train_1 as default for legacy mode
                                has_per_train_structure = any(key.startswith('train_') for key in all_states.keys())
                                if has_per_train_structure:
                                    print(f"[API] WARNING: Legacy mode detected per-train structure, using train_1 as default")
                                    train_key = "train_1"
                                    if train_key in all_states:
                                        section = all_states[train_key]
                                        if 'inputs' in section and 'outputs' in section:
                                            result = self.train_states.copy()
                                            result.update(section.get('inputs', {}))
                                            result.update(section.get('outputs', {}))
                                            return result
                                    # Fallback to defaults if train_1 doesn't exist or is malformed
                                    return self.train_states.copy()

                                # Original legacy behavior for truly legacy files
                                if 'inputs' in all_states and 'outputs' in all_states:
                                    result = self.train_states.copy()
                                    result.update(all_states.get('inputs', {}))
                                    result.update(all_states.get('outputs', {}))
                                    return result
                                else:
                                    result = self.train_states.copy()
                                    result.update(all_states)
                                    return result
                    except Exception as e:
                        print(f"[WARNING] Error processing state: {e}")
                        return self.train_states.copy()
                else:
                    return self.train_states.copy()
            except Exception as e:
                print(f"Error accessing state file: {e}")
                return self.train_states.copy()

    def save_state(self, state: dict) -> None:
        """Save train state to file with inputs/outputs structure.
        
        Args:
            state: Complete state dictionary to save
            
        The method separates state into inputs (from Train Model) and outputs (to Train Model).
        """
        with _file_lock:
            try:
                # Validate state parameter
                if not isinstance(state, dict):
                    raise ValueError(f"save_state() requires dict, got {type(state)}")
                
                # Use state as-is (no merging with defaults - preserves existing values)
                complete_state = state
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
                
                if self.train_id is not None:
                    # Multi-train mode: update specific train's section at ROOT level only
                    if os.path.exists(self.state_file):
                        try:
                            with open(self.state_file, 'r') as f:
                                content = f.read()
                                if not content or content.strip() == '':
                                    print(f"[API] ERROR: train_states.json is EMPTY! Skipping save to prevent data loss.")
                                    raise IOError("Empty file detected - race condition victim")
                                all_states = json.loads(content)
                        except json.JSONDecodeError as e:
                            print(f"[API] ERROR: train_states.json is CORRUPTED: {e}")
                            print(f"[API] CRITICAL: Refusing to save - would lose existing data!")
                            raise IOError("Corrupted file detected - refusing to overwrite")
                    else:
                        all_states = {}

                    # Clean up legacy flat fields - only keep train_X entries
                    keys_to_remove = [k for k in all_states.keys() if not k.startswith('train_')]
                    for k in keys_to_remove:
                        del all_states[k]
                    
                    train_key = f"train_{self.train_id}"
                    
                    # Read existing state from file (if it exists), otherwise start with defaults
                    # CRITICAL: Preserve existing inputs/outputs separately - don't reset both if one is missing!
                    if train_key in all_states and isinstance(all_states[train_key], dict):
                        existing = all_states[train_key]
                        # Check inputs and outputs SEPARATELY
                        if 'inputs' in existing and isinstance(existing['inputs'], dict):
                            inputs = existing['inputs'].copy()
                        else:
                            inputs = self.default_inputs.copy()
                        
                        if 'outputs' in existing and isinstance(existing['outputs'], dict):
                            outputs = existing['outputs'].copy()
                        else:
                            # Check if we're about to lose kp/ki values
                            if 'kp' in existing or 'ki' in existing:
                                print(f"[API] Warning: train_{self.train_id} has flat kp/ki but missing outputs - preserving values")
                                outputs = self.default_outputs.copy()
                                outputs['kp'] = existing.get('kp', None)
                                outputs['ki'] = existing.get('ki', None)
                            else:
                                outputs = self.default_outputs.copy()
                    else:
                        inputs = self.default_inputs.copy()
                        outputs = self.default_outputs.copy()
                    
                    # Update ONLY the fields present in complete_state (preserves other fields)
                    # DEBUG: Log what we're about to update
                    output_updates = {k: v for k, v in complete_state.items() if k in self.default_outputs}
                    if output_updates:
                        print(f"[API] DEBUG: Updating outputs for train_{self.train_id}: {list(output_updates.keys())}")
                        if 'kp' in output_updates or 'ki' in output_updates:
                            print(f"[API] DEBUG: kp={output_updates.get('kp')}, ki={output_updates.get('ki')}")
                    
                    for key, value in complete_state.items():
                        # Skip nested train_X sections and train_id
                        if key.startswith('train_') and isinstance(value, dict):
                            continue
                        elif key == 'train_id':
                            continue
                        # Categorize into inputs or outputs and update
                        elif key in self.default_inputs:
                            inputs[key] = value
                        elif key in self.default_outputs:
                            outputs[key] = value
                    
                    # Only store inputs and outputs sections
                    all_states[train_key] = {
                        'inputs': inputs,
                        'outputs': outputs
                    }
                    
                    # Atomic write with sorted keys (prevents race conditions and corruption)
                    sorted_states = {k: all_states[k] for k in sorted(all_states.keys())}
                    if not safe_write_json(self.state_file, sorted_states):
                        print(f"[API] CRITICAL: Failed to save train_{self.train_id} state atomically!")
                        raise IOError("Atomic write failed")
                else:
                    # Legacy mode: save with inputs/outputs structure at root
                    # CRITICAL FIX: Don't corrupt per-train structure! If per-train structure exists,
                    # legacy mode should NOT add flat inputs/outputs at root level.
                    if os.path.exists(self.state_file):
                        try:
                            with open(self.state_file, 'r') as f:
                                content = f.read()
                                if not content or content.strip() == '':
                                    print(f"[API] ERROR: train_states.json is EMPTY! Skipping save to prevent data loss.")
                                    raise IOError("Empty file detected - race condition victim")
                                all_states = json.loads(content)
                        except json.JSONDecodeError as e:
                            print(f"[API] ERROR: train_states.json is CORRUPTED: {e}")
                            print(f"[API] CRITICAL: Refusing to save - would lose existing data!")
                            raise IOError("Corrupted file detected - refusing to overwrite")
                    else:
                        all_states = {}

                    # CRITICAL: Check if per-train structure exists
                    has_per_train_structure = any(key.startswith('train_') for key in all_states.keys())

                    if has_per_train_structure:
                        # DON'T add flat inputs/outputs at root - it corrupts per-train data!
                        # Instead, warn and skip the save to prevent corruption
                        print(f"[API] WARNING: Legacy mode detected per-train structure in train_states.json!")
                        print(f"[API] WARNING: Refusing to save to prevent corruption. Use train-specific mode instead.")
                        print(f"[API] WARNING: Software controller should specify train_id instead of using legacy mode.")
                        return  # Skip the save entirely to prevent corruption

                    if 'inputs' not in all_states:
                        all_states['inputs'] = self.default_inputs.copy()
                    if 'outputs' not in all_states:
                        all_states['outputs'] = self.default_outputs.copy()
                    
                    # Sort complete_state into inputs and outputs
                    for key, value in complete_state.items():
                        if key in self.default_inputs:
                            all_states['inputs'][key] = value
                        elif key in self.default_outputs:
                            all_states['outputs'][key] = value
                    
                    # Atomic write with sorted keys (prevents race conditions and corruption)
                    sorted_states = {k: all_states[k] for k in sorted(all_states.keys())}
                    if not safe_write_json(self.state_file, sorted_states):
                        print(f"[API] CRITICAL: Failed to save legacy state atomically!")
                        raise IOError("Atomic write failed")

            except Exception as e:
                print(f"[ERROR] Failed to save train state: {e}")
                print(f"[ERROR] train_id={self.train_id}, state keys={list(state.keys())}")
                import traceback
                traceback.print_exc()
                # DO NOT write corrupted data - preserve existing file

    def reset_state(self) -> None:
        """Reset train state to default values."""
        self.save_state(self.train_states.copy())

    def read_train_data_json(self) -> Optional[Dict]:
        """Read the latest train_data.json directly from Train_Model folder."""
        try:
            base_dir = os.path.dirname(os.path.dirname(__file__))  # train_controller/
            train_data_path = os.path.join(os.path.dirname(base_dir), "Train_Model", "train_data.json")

            print(f"[DEBUG] Reading Train Model data from: {train_data_path}")

            if not os.path.exists(train_data_path):
                print("[TrainControllerAPI] train_data.json not found in Train_Model folder.")
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

        # NEW: pick per-train section if train_id is set
        if self.train_id is not None:
            section_key = f"train_{self.train_id}"
            section = data.get(section_key, {})
            inputs = section.get("inputs", {})
            outputs = section.get("outputs", {})
        else:
            inputs = data.get("inputs", {})
            outputs = data.get("outputs", {})

        mapped_data = {
            'commanded_speed': inputs.get('commanded speed', 0.0),
            'commanded_authority': inputs.get('commanded authority', 0.0),
            'speed_limit': inputs.get('speed limit', 0.0),
            'train_velocity': outputs.get('velocity_mph', 0.0),
            'train_temperature': outputs.get('temperature_F', 0.0),
            'train_model_engine_failure': inputs.get('train_model_engine_failure', False),
            'train_model_signal_failure': inputs.get('train_model_signal_failure', False),
            'train_model_brake_failure': inputs.get('train_model_brake_failure', False),
            # NOTE: manual_mode is a controller-only state, not read from train_data.json
            # NOTE: Do NOT read beacon info (current_station, next_stop, station_side) from train_data.json
            # The Train Model writes beacon info to train_states.json with proper signal failure handling
            # Reading from inputs here would bypass the frozen data logic during signal failure
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
                    'train_velocity', 'current_station', 'next_stop', 'station_side', 'train_temperature',
                    'train_model_engine_failure', 'train_model_signal_failure', 
                    'train_model_brake_failure', 'manual_mode']
        }
        
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
