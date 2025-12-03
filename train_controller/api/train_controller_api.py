"""Train Controller API module for state management and module communication.

This module handles data persistence using JSON files and provides interfaces
for communication between Train Controller and Train Model modules. 
"""

import json
import os
import threading
import time
import tempfile
import shutil
from typing import Dict, Optional

# Debug mode flag - Set to False to disable verbose logging
DEBUG_MODE = False

# Global file lock for thread-safe access to train_states.json
# Using RLock (reentrant lock) to allow same thread to acquire lock multiple times
_file_lock = threading.Lock()


def _safe_write_json(path: str, data: dict) -> bool:
    """Write JSON with atomic writes and retry logic.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        payload = json.dumps(data, indent=4)
        out_dir = os.path.dirname(os.path.abspath(path))
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        
        # Use unique temp file with process ID to avoid conflicts
        tmp_dir = os.path.dirname(os.path.abspath(path))
        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.tmp', dir=tmp_dir, text=True)
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Write to temp file using the file descriptor
                with os.fdopen(tmp_fd, 'w') as f:
                    f.write(payload)
                    f.flush()
                    os.fsync(f.fileno())
                
                # Atomic replace
                os.replace(tmp_path, path)
                return True
                
            except PermissionError as e:
                if attempt < max_retries - 1:
                    wait_time = 0.05 * (2 ** attempt)  # Exponential backoff
                    time.sleep(wait_time)
                    # Reopen temp file for next attempt
                    try:
                        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.tmp', dir=tmp_dir, text=True)
                    except Exception:
                        break
                else:
                    print(f"[WRITE ERROR] Failed to write {path} after {max_retries} attempts: {e}")
                    try:
                        os.close(tmp_fd)
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                    except Exception:
                        pass
                    return False
            except Exception as e:
                print(f"[WRITE ERROR] Unexpected error writing {path}: {e}")
                try:
                    os.close(tmp_fd)
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass
                return False
        return False
    except Exception as e:
        print(f"[WRITE ERROR] Failed to prepare write for {path}: {e}")
        return False


def _create_backup(path: str):
    """Create a backup of the JSON file before modifying it."""
    if os.path.exists(path):
        backup_path = path + ".backup"
        try:
            shutil.copy2(path, backup_path)
        except Exception as e:
            if DEBUG_MODE:
                print(f"[BACKUP WARNING] Could not create backup of {path}: {e}")


def _restore_from_backup(path: str) -> bool:
    """Restore JSON file from backup if main file is corrupted."""
    backup_path = path + ".backup"
    if os.path.exists(backup_path):
        try:
            # Verify backup is valid JSON
            with open(backup_path, 'r') as f:
                json.load(f)
            # Backup is valid, restore it
            shutil.copy2(backup_path, path)
            print(f"[RESTORE] Restored {path} from backup")
            return True
        except Exception as e:
            print(f"[RESTORE ERROR] Could not restore from backup: {e}")
            return False
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
        
        # Cache for last successfully read state (to handle temporary file locks)
        self._cached_state = None
        
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
        
        self.default_outputs = {
            # Outputs TO Train Model (Train Controller commands)
            'manual_mode': False,
            'driver_velocity': 0.0,
            'service_brake': False,
            'right_door': False,
            'left_door': False,
            'interior_lights': False,
            'exterior_lights': False,
            'set_temperature': 70.0,
            'temperature_up': False,
            'temperature_down': False,
            'announcement': '',
            'announce_pressed': False,
            'emergency_brake': False,
            'kp': None,  # Must be set through UI
            'ki': None,  # Must be set through UI
            'engineering_panel_locked': False,
            'power_command': 0.0,
        }
        
        # Legacy flat structure for backward compatibility
        self.train_states = {**self.default_inputs, **self.default_outputs}
        
        # Initialize state file - preserve kp/ki if they already exist
        try:
            print(f"[API INIT] Initializing train_controller_api for train_id={train_id}")
            # Read existing state to preserve kp/ki values
            existing_state = self.get_state()
            existing_kp = existing_state.get('kp')
            existing_ki = existing_state.get('ki')
            
            # Initialize default state with matched values
            initial_state = self.train_states.copy()
            initial_state['driver_velocity'] = initial_state['commanded_speed']
            initial_state['set_temperature'] = initial_state['train_temperature']
            
            # Preserve existing kp/ki if they were set (not None)
            if existing_kp is not None:
                initial_state['kp'] = existing_kp
                print(f"[API INIT] Preserving existing kp={existing_kp}")
            else:
                initial_state['kp'] = None
            
            if existing_ki is not None:
                initial_state['ki'] = existing_ki
                print(f"[API INIT] Preserving existing ki={existing_ki}")
            else:
                initial_state['ki'] = None
                
            self.save_state(initial_state)
            print(f"[API INIT] State saved successfully")
        except Exception as e:
            print(f"[API INIT] Error initializing state file: {e}")
            # Ensure we have a valid state file with proper initialization
            initial_state = self.train_states.copy()
            initial_state['driver_velocity'] = initial_state['commanded_speed']
            initial_state['set_temperature'] = initial_state['train_temperature']
            initial_state['kp'] = None
            initial_state['ki'] = None
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
        """Get current train state with retry logic and caching.
        
        Returns:
            dict: Current state of the train (merged inputs + outputs). Uses cached state on temporary errors.
        """
        max_retries = 3
        retry_delay = 0.05  # 50ms between retries
        
        with _file_lock:
            for attempt in range(max_retries):
                try:
                    if os.path.exists(self.state_file):
                        with open(self.state_file, 'r') as f:
                            try:
                                all_states = json.load(f)
                                
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
                                            self._cached_state = result.copy()  # Update cache
                                            return result
                                        else:
                                            # Old flat structure - merge with defaults
                                            result = self.train_states.copy()
                                            result.update(section)
                                            self._cached_state = result.copy()  # Update cache
                                            return result
                                    else:
                                        # Return default state if train section doesn't exist
                                        default = self.train_states.copy()
                                        default['train_id'] = self.train_id
                                        self._cached_state = default.copy()  # Update cache
                                        return default
                                else:
                                    # Legacy mode: read from root level, support both old and new structure
                                    if 'inputs' in all_states and 'outputs' in all_states:
                                        result = self.train_states.copy()
                                        result.update(all_states.get('inputs', {}))
                                        result.update(all_states.get('outputs', {}))
                                        self._cached_state = result.copy()  # Update cache
                                        return result
                                    else:
                                        result = self.train_states.copy()
                                        result.update(all_states)
                                        self._cached_state = result.copy()  # Update cache
                                        return result
                            except json.JSONDecodeError as e:
                                # ALWAYS log JSON errors (not just in DEBUG_MODE)
                                print(f"[READ ERROR] JSON decode error in {self.state_file}: {e}")
                                
                                # Try to restore from backup on first attempt
                                if attempt == 0:
                                    print(f"[RESTORE] Attempting to restore from backup...")
                                    if _restore_from_backup(self.state_file):
                                        # Retry reading after restore
                                        time.sleep(retry_delay)
                                        continue
                                
                                # DON'T reset during runtime - only return cached state
                                if self._cached_state is not None:
                                    print(f"[CACHE] Using cached state due to JSON error")
                                    return self._cached_state.copy()
                                
                                # If no cache and last attempt, return default
                                if attempt == max_retries - 1:
                                    print(f"[DEFAULT] Returning default state (no cache available)")
                                    return self.train_states.copy()
                                
                                time.sleep(retry_delay)
                                continue
                                
                    # File doesn't exist yet - return default
                    return self.train_states.copy()
                    
                except (PermissionError, OSError) as e:
                    # File temporarily locked - retry or use cache
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    else:
                        # Max retries reached - use cached state if available
                        if self._cached_state is not None:
                            return self._cached_state.copy()
                        return self.train_states.copy()
                        
                except Exception as e:
                    if DEBUG_MODE:
                        print(f"[Train {self.train_id}] Unexpected error accessing state file: {e}")
                    # Use cached state if available
                    if self._cached_state is not None:
                        return self._cached_state.copy()
                    return self.train_states.copy()
                    
            # Shouldn't reach here, but return cached or default
            if self._cached_state is not None:
                return self._cached_state.copy()
            return self.train_states.copy()

    def save_state(self, state: dict) -> None:
        """Save train state to file with inputs/outputs structure.
        
        Args:
            state: Complete state dictionary to save
            
        The method separates state into inputs (from Train Model) and outputs (to Train Model).
        """
        with _file_lock:
            try:
                # Create backup before modifying
                _create_backup(self.state_file)
                
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
                        try:
                            with open(self.state_file, 'r') as f:
                                all_states = json.load(f)
                        except (json.JSONDecodeError, Exception) as e:
                            print(f"[SAVE ERROR] Could not read existing state, attempting restore: {e}")
                            if _restore_from_backup(self.state_file):
                                try:
                                    with open(self.state_file, 'r') as f:
                                        all_states = json.load(f)
                                except Exception:
                                    all_states = {}
                            else:
                                all_states = {}
                    else:
                        all_states = {}
                    
                    train_key = f"train_{self.train_id}"
                    
                    # Create clean inputs/outputs structure (no flat duplicate fields)
                    inputs = self.default_inputs.copy()
                    outputs = self.default_outputs.copy()
                    
                    # Sort complete_state into inputs and outputs
                    for key, value in complete_state.items():
                        # Skip nested train_X sections and train_id
                        if key.startswith('train_') and isinstance(value, dict):
                            continue
                        elif key == 'train_id':
                            continue
                        # Categorize into inputs or outputs
                        elif key in self.default_inputs:
                            inputs[key] = value
                        elif key in self.default_outputs:
                            outputs[key] = value
                    
                    # Only store inputs and outputs sections
                    all_states[train_key] = {
                        'inputs': inputs,
                        'outputs': outputs
                    }
                    
                    # Use safe atomic write
                    if _safe_write_json(self.state_file, all_states):
                        # Update cache after successful write
                        self._cached_state = complete_state.copy()
                    else:
                        print(f"[SAVE ERROR] Failed to save state for train {self.train_id}")
                else:
                    # Legacy mode: save with inputs/outputs structure at root
                    if os.path.exists(self.state_file):
                        try:
                            with open(self.state_file, 'r') as f:
                                all_states = json.load(f)
                        except (json.JSONDecodeError, Exception) as e:
                            print(f"[SAVE ERROR] Could not read existing state, attempting restore: {e}")
                            if _restore_from_backup(self.state_file):
                                try:
                                    with open(self.state_file, 'r') as f:
                                        all_states = json.load(f)
                                except Exception:
                                    all_states = {}
                            else:
                                all_states = {}
                    else:
                        all_states = {}
                    
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
                    
                    # Use safe atomic write
                    if _safe_write_json(self.state_file, all_states):
                        # Update cache after successful write
                        self._cached_state = complete_state.copy()
                    else:
                        print(f"[SAVE ERROR] Failed to save state (legacy mode)")

            except Exception as e:
                print(f"[SAVE ERROR] Unexpected error in save_state: {e}")
                # Don't try fallback - could make things worse

    def reset_state(self) -> None:
        """Reset train state to default values."""
        self.save_state(self.train_states.copy())

    def read_train_data_json(self) -> Optional[Dict]:
        """Read the latest train_data.json directly from Train_Model folder."""
        try:
            base_dir = os.path.dirname(os.path.dirname(__file__))  # train_controller/
            train_data_path = os.path.join(os.path.dirname(base_dir), "Train_Model", "train_data.json")

            if DEBUG_MODE:
                print(f"[DEBUG] Reading Train Model data from: {train_data_path}")

            if not os.path.exists(train_data_path):
                if DEBUG_MODE:
                    print("[TrainControllerAPI] train_data.json not found in Train_Model folder.")
                return None

            with open(train_data_path, 'r') as f:
                data = json.load(f)
            return data

        except json.JSONDecodeError:
            if DEBUG_MODE:
                print("[TrainControllerAPI] Invalid JSON format in train_data.json.")
            return None
        except (PermissionError, OSError) as e:
            # Silently ignore permission errors - file may be locked by another process
            return None
        except Exception as e:
            if DEBUG_MODE:
                print(f"[TrainControllerAPI] Error reading train_data.json: {e}")
            return None

    def update_from_train_data(self) -> None:
        """Read and update controller state directly from Train Model's train_data.json."""
        data = self.read_train_data_json()
        if not data:
            if DEBUG_MODE:
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
            'commanded_speed': outputs.get('commanded_speed', 0.0),
            'commanded_authority': outputs.get('authority_yds', 0.0),
            'speed_limit': outputs.get('speed_limit', 0.0),
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
        if DEBUG_MODE:
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
