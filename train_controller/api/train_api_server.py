"""REST API Server for Train System
Manages all JSON state files and provides endpoints for clients.

This server runs on the main computer and allows Raspberry Pi devices
to access train state data over the network. 

Author: James Struyk, Julen Coca-Knorr
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from threading import Lock, Thread
from datetime import datetime
import time

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from Raspberry Pis

# File paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)

# Module-specific data directories
DATA_DIR = os.path.join(parent_dir, "data")
TRAIN_MODEL_DIR = os.path.join(project_root, "Train_Model")
WAYSIDE_DIR = os.path.join(project_root, "track_controller", "New_SW_Code")

# Communication files (respecting module boundaries)
TRAIN_STATES_FILE = os.path.join(DATA_DIR, "train_states.json")
TRAIN_DATA_FILE = os.path.join(TRAIN_MODEL_DIR, "train_data.json")
CTC_TRACK_CONTROLLER_FILE = os.path.join(project_root, "ctc_track_controller.json")
WAYSIDE_TO_TRAIN_FILE = os.path.join(WAYSIDE_DIR, "wayside_to_train.json")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Thread-safe file access
file_lock = Lock()
sync_running = True  # Flag to control sync thread

def read_json_file(filepath):
    """Thread-safe JSON file read."""
    with file_lock:
        try:
            if not os.path.exists(filepath):
                return {}
            with open(filepath, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[Server] Error reading {filepath}: {e}")
            return {}

def write_json_file(filepath, data):
    """Thread-safe JSON file write with sorted keys for train_states.json."""
    with file_lock:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Sort keys if writing to train_states.json to maintain consistent order (train_1, train_2, etc.)
            if 'train_states.json' in filepath and isinstance(data, dict):
                # Sort top-level keys (train_1, train_2, etc.)
                data = {k: data[k] for k in sorted(data.keys())}
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[Server] Error writing {filepath}: {e}")

def sync_states_to_train_data():
    """Sync controller outputs from train_states.json to train_data.json.
    
    This writes controller outputs (power_command, etc.) back to train_data.json
    so the Train Model can read and apply them.
    
    Reads from train_states.json (nested inputs/outputs structure)
    and writes to train_data.json (nested inputs/outputs structure).
    """
    try:
        # Read current states
        train_states = read_json_file(TRAIN_STATES_FILE)
        train_data = read_json_file(TRAIN_DATA_FILE)
        
        if not train_states:
            return
        
        # For each train in states, update its inputs in train_data
        # (Controller outputs become Train Model inputs)
        for key in train_states.keys():
            if key.startswith("train_"):
                train_section = train_states[key]
                outputs = train_section.get("outputs", {})
                
                # Ensure train exists in train_data
                if key not in train_data:
                    train_data[key] = {"inputs": {}, "outputs": {}}
                if "inputs" not in train_data[key]:
                    train_data[key]["inputs"] = {}
                
                # Update INPUTS in train_data from controller OUTPUTS
                # These are the controller outputs that Train Model needs as inputs
                train_data[key]["inputs"]["power_command"] = outputs.get("power_command", 0.0)
                train_data[key]["inputs"]["service_brake"] = outputs.get("service_brake", False)
                train_data[key]["inputs"]["emergency_brake"] = outputs.get("emergency_brake", False)
                train_data[key]["inputs"]["left_door"] = outputs.get("left_door", False)
                train_data[key]["inputs"]["right_door"] = outputs.get("right_door", False)
                train_data[key]["inputs"]["interior_lights"] = outputs.get("interior_lights", True)
                train_data[key]["inputs"]["exterior_lights"] = outputs.get("exterior_lights", True)
                train_data[key]["inputs"]["set_temperature"] = outputs.get("set_temperature", 70.0)
        
        # Write back to train_data.json
        write_json_file(TRAIN_DATA_FILE, train_data)
        
    except Exception as e:
        print(f"[Server] Error syncing states to train_data: {e}")

def sync_train_data_to_states():
    """Background thread that syncs bidirectionally between train_data.json and train_states.json.
    
    1. Syncs Train Model inputs (FROM train_data.json TO train_states.json)
       - Controllers read these via REST API
    2. Syncs Controller outputs (FROM train_states.json TO train_data.json)
       - Train Model reads these to control the train
    """
    global sync_running
    print("[Server] Bidirectional sync thread started (500ms interval)")
    print("[Server] Syncing train_data.json ↔ train_states.json")
    
    while sync_running:
        try:
            # STEP 1: Sync Train Model inputs FROM train_data.json TO train_states.json
            # (Controllers read these via REST API)
            train_data = read_json_file(TRAIN_DATA_FILE)
            
            if not train_data:
                time.sleep(0.5)
                continue
            
            # Read current train_states.json
            train_states = read_json_file(TRAIN_STATES_FILE)
            
            # Sync each train_X section
            for key in train_data.keys():
                if key.startswith("train_"):
                    section = train_data[key]
                    inputs = section.get("inputs", {})
                    outputs = section.get("outputs", {})
                    
                    # Ensure train exists in states with proper inputs/outputs structure
                    # CRITICAL: Skip trains that don't exist in train_states - they should be created by dispatch, not sync!
                    # This prevents resetting kp/ki to None if the train entry gets corrupted/deleted
                    if key not in train_states:
                        print(f"[Server] Warning: {key} found in train_data.json but not in train_states.json - skipping sync")
                        print(f"[Server] This train should be dispatched via CTC to properly initialize train_states")
                        continue  # Skip this train - don't create it with None kp/ki!
                    
                    # Ensure inputs/outputs structure exists (handle legacy flat format)
                    # CRITICAL: Don't replace the entire dict - preserve existing outputs (kp, ki, lights, etc.)!
                    if "inputs" not in train_states[key]:
                        # Only add missing inputs, preserve existing outputs
                        if isinstance(train_states[key], dict):
                            # Check if we're about to lose ANY output values
                            if "outputs" in train_states[key] and train_states[key]["outputs"]:
                                print(f"[Server] WARNING: {key} missing inputs but has existing outputs - PRESERVING ALL OUTPUTS")
                                print(f"[Server] Outputs: {list(train_states[key]['outputs'].keys())}")
                            train_states[key]["inputs"] = {}
                        else:
                            # Completely malformed - must replace (should be rare)
                            print(f"[Server] ERROR: {key} is not a dict (type={type(train_states[key])}), replacing with default structure")
                            train_states[key] = {"inputs": {}, "outputs": {}}
                    
                    # CLEAN UP: Remove flat fields (legacy format) - only keep inputs/outputs structure
                    keys_to_remove = [k for k in train_states[key].keys() if k not in ['inputs', 'outputs']]
                    for k in keys_to_remove:
                        del train_states[key][k]
                    
                    # Ensure ALL required input fields exist with defaults (matches train_controller_api.py)
                    if "inputs" not in train_states[key]:
                        train_states[key]["inputs"] = {}
                    inputs_section = train_states[key]["inputs"]
                    
                    # Set defaults for any missing input fields
                    if "commanded_speed" not in inputs_section:
                        inputs_section["commanded_speed"] = 0.0
                    if "commanded_authority" not in inputs_section:
                        inputs_section["commanded_authority"] = 0.0
                    if "speed_limit" not in inputs_section:
                        inputs_section["speed_limit"] = 0.0
                    if "train_velocity" not in inputs_section:
                        inputs_section["train_velocity"] = 0.0
                    if "current_station" not in inputs_section:
                        inputs_section["current_station"] = ""
                    if "next_stop" not in inputs_section:
                        inputs_section["next_stop"] = ""
                    if "station_side" not in inputs_section:
                        inputs_section["station_side"] = ""
                    if "train_temperature" not in inputs_section:
                        inputs_section["train_temperature"] = 0.0
                    if "train_model_engine_failure" not in inputs_section:
                        inputs_section["train_model_engine_failure"] = False
                    if "train_model_signal_failure" not in inputs_section:
                        inputs_section["train_model_signal_failure"] = False
                    if "train_model_brake_failure" not in inputs_section:
                        inputs_section["train_model_brake_failure"] = False
                    if "train_controller_engine_failure" not in inputs_section:
                        inputs_section["train_controller_engine_failure"] = False
                    if "train_controller_signal_failure" not in inputs_section:
                        inputs_section["train_controller_signal_failure"] = False
                    if "train_controller_brake_failure" not in inputs_section:
                        inputs_section["train_controller_brake_failure"] = False
                    if "beacon_read_blocked" not in inputs_section:
                        inputs_section["beacon_read_blocked"] = False
                    
                    # Update ONLY inputs section with train_data (preserve outputs!)
                    train_states[key]["inputs"]["commanded_speed"] = inputs.get("commanded speed", 0.0)
                    train_states[key]["inputs"]["commanded_authority"] = inputs.get("commanded authority", 0.0)
                    train_states[key]["inputs"]["speed_limit"] = inputs.get("speed limit", 0.0)
                    train_states[key]["inputs"]["train_velocity"] = outputs.get("velocity_mph", 0.0)
                    train_states[key]["inputs"]["train_temperature"] = outputs.get("temperature_F", 70.0)
                    train_states[key]["inputs"]["train_model_engine_failure"] = inputs.get("train_model_engine_failure", False)
                    train_states[key]["inputs"]["train_model_signal_failure"] = inputs.get("train_model_signal_failure", False)
                    train_states[key]["inputs"]["train_model_brake_failure"] = inputs.get("train_model_brake_failure", False)
                    
                    # Also sync beacon info (current_station, next_station, side_door)
                    train_states[key]["inputs"]["current_station"] = inputs.get("current station", "")
                    train_states[key]["inputs"]["next_stop"] = inputs.get("next station", "")
                    train_states[key]["inputs"]["station_side"] = inputs.get("side_door", "")
                    
                    # Ensure ALL required output fields exist with defaults (matches train_controller_api.py)
                    if "outputs" not in train_states[key]:
                        print(f"[Server] WARNING: {key} missing outputs section - creating empty dict (will be filled with defaults)")
                        train_states[key]["outputs"] = {}
                    outputs_section = train_states[key]["outputs"]
                    
                    # DEBUG: Log what's in outputs before setting defaults
                    existing_outputs = list(outputs_section.keys())
                    if existing_outputs:
                        print(f"[Server] DEBUG: {key} has existing outputs: {existing_outputs}")
                    
                    # Set defaults for any missing output fields (preserves existing values)
                    if "manual_mode" not in outputs_section:
                        outputs_section["manual_mode"] = False
                    if "driver_velocity" not in outputs_section:
                        outputs_section["driver_velocity"] = 0.0
                    if "service_brake" not in outputs_section:
                        outputs_section["service_brake"] = False
                    if "right_door" not in outputs_section:
                        outputs_section["right_door"] = False
                    if "left_door" not in outputs_section:
                        outputs_section["left_door"] = False
                    if "interior_lights" not in outputs_section:
                        outputs_section["interior_lights"] = True  # Default ON (matches train_controller_api.py line 105)
                    if "exterior_lights" not in outputs_section:
                        outputs_section["exterior_lights"] = True  # Default ON (matches train_controller_api.py line 106)
                    if "set_temperature" not in outputs_section:
                        outputs_section["set_temperature"] = 70.0
                    if "temperature_up" not in outputs_section:
                        outputs_section["temperature_up"] = False
                    if "temperature_down" not in outputs_section:
                        outputs_section["temperature_down"] = False
                    if "announcement" not in outputs_section:
                        outputs_section["announcement"] = ""
                    if "announce_pressed" not in outputs_section:
                        outputs_section["announce_pressed"] = False
                    if "emergency_brake" not in outputs_section:
                        outputs_section["emergency_brake"] = False
                    # CRITICAL: Only set kp/ki to None if they don't exist
                    # NEVER overwrite existing values (user may have set them via UI)
                    if "kp" not in outputs_section:
                        outputs_section["kp"] = None  # Must be set through UI (matches train_controller_api.py line 103)
                    if "ki" not in outputs_section:
                        outputs_section["ki"] = None  # Must be set through UI (matches train_controller_api.py line 104)
                    if "engineering_panel_locked" not in outputs_section:
                        outputs_section["engineering_panel_locked"] = False
                    if "power_command" not in outputs_section:
                        outputs_section["power_command"] = 0.0
            
            # DEBUG: Before writing, check what we're about to save
            for key in train_states.keys():
                if key.startswith("train_"):
                    outputs = train_states[key].get("outputs", {})
                    kp_val = outputs.get("kp")
                    ki_val = outputs.get("ki")
                    lights = outputs.get("interior_lights")
                    if kp_val is not None or ki_val is not None or lights is not None:
                        print(f"[Server] DEBUG: About to save {key}: kp={kp_val}, ki={ki_val}, interior_lights={lights}")
            
            # Write updated states back
            write_json_file(TRAIN_STATES_FILE, train_states)
            
            # STEP 2: Sync Controller outputs FROM train_states.json TO train_data.json
            # (Train Model reads these to control the train)
            sync_states_to_train_data()
            
        except Exception as e:
            print(f"[Server] Error in sync thread: {e}")
        
        time.sleep(0.5)  # Sync every 500ms (same as UI update rate)
    
    print("[Server] Train data sync thread stopped")

# ========== Train State Endpoints ==========

@app.route('/api/train/<int:train_id>/state', methods=['GET'])
def get_train_state(train_id):
    """Get state for a specific train.
    
    Returns a FLAT structure by merging inputs and outputs.
    This allows clients (Raspberry Pi) to access all fields at the top level.
    """
    data = read_json_file(TRAIN_STATES_FILE)
    train_key = f"train_{train_id}"
    
    if train_key in data:
        train_section = data[train_key]
        
        # Flatten the structure: merge inputs and outputs into a single dict
        flat_state = {}
        if "inputs" in train_section:
            flat_state.update(train_section["inputs"])
        if "outputs" in train_section:
            flat_state.update(train_section["outputs"])
        
        # Add train_id to the flat state
        flat_state["train_id"] = train_id
        
        return jsonify(flat_state), 200
    else:
        return jsonify({"error": f"Train {train_id} not found"}), 404

@app.route('/api/train/<int:train_id>/state', methods=['POST', 'PUT'])
def update_train_state(train_id):
    """Update state for a specific train (partial update)."""
    updates = request.json
    if not updates:
        return jsonify({"error": "No data provided"}), 400
    
    data = read_json_file(TRAIN_STATES_FILE)
    train_key = f"train_{train_id}"
    
    # Define which fields go in inputs vs outputs
    input_fields = {'commanded_speed', 'commanded_authority', 'speed_limit', 'train_velocity', 
                    'current_station', 'next_stop', 'station_side', 'train_temperature',
                    'train_model_engine_failure', 'train_model_signal_failure', 
                    'train_model_brake_failure', 'train_controller_engine_failure',
                    'train_controller_signal_failure', 'train_controller_brake_failure',
                    'beacon_read_blocked'}
    output_fields = {'manual_mode', 'driver_velocity', 'service_brake', 'right_door', 'left_door',
                     'interior_lights', 'exterior_lights', 'set_temperature', 'temperature_up',
                     'temperature_down', 'announcement', 'announce_pressed', 'emergency_brake',
                     'kp', 'ki', 'engineering_panel_locked', 'power_command'}
    
    # Initialize train if it doesn't exist with proper structure
    if train_key not in data:
        data[train_key] = {
            "inputs": {
                "commanded_speed": 0.0,
                "commanded_authority": 0.0,
                "speed_limit": 0.0,
                "train_velocity": 0.0,
                "next_stop": "",
                "station_side": "",
                "train_temperature": 70.0,
                "current_station": "",
                "train_model_engine_failure": False,
                "train_model_signal_failure": False,
                "train_model_brake_failure": False,
                "train_controller_engine_failure": False,
                "train_controller_signal_failure": False,
                "train_controller_brake_failure": False,
                "beacon_read_blocked": False
            },
            "outputs": {
                "manual_mode": False,
                "driver_velocity": 0.0,
                "service_brake": False,
                "emergency_brake": False,
                "power_command": 0.0,
                "kp": None,
                "ki": None,
                "right_door": False,
                "left_door": False,
                "interior_lights": True,
                "exterior_lights": True,
                "set_temperature": 70.0,
                "temperature_up": False,
                "temperature_down": False,
                "announcement": "",
                "announce_pressed": False,
                "engineering_panel_locked": False
            }
        }
    
    # Ensure inputs/outputs structure exists
    # CRITICAL: Don't replace the entire dict - preserve existing outputs (kp, ki, etc.)!
    if "inputs" not in data[train_key]:
        if isinstance(data[train_key], dict):
            # Only add missing inputs, preserve existing outputs
            if "outputs" in data[train_key]:
                kp_val = data[train_key]["outputs"].get("kp")
                ki_val = data[train_key]["outputs"].get("ki")
                if kp_val is not None or ki_val is not None:
                    print(f"[Server] Warning: train_{train_id} missing inputs but has kp={kp_val}, ki={ki_val} - preserving outputs")
            data[train_key]["inputs"] = {}
        else:
            # Completely malformed - must replace
            print(f"[Server] Warning: train_{train_id} is not a dict, replacing with default structure")
            data[train_key] = {"inputs": {}, "outputs": {}}
    
    # CLEAN UP: Remove flat fields (legacy format) - only keep inputs/outputs structure
    keys_to_remove = [k for k in data[train_key].keys() if k not in ['inputs', 'outputs']]
    for k in keys_to_remove:
        del data[train_key][k]
    
    # Ensure outputs section exists before writing to it
    if "inputs" not in data[train_key]:
        data[train_key]["inputs"] = {}
    if "outputs" not in data[train_key]:
        data[train_key]["outputs"] = {}
    
    # Update fields in appropriate sections
    for key, value in updates.items():
        if key in input_fields:
            data[train_key]["inputs"][key] = value
        elif key in output_fields:
            data[train_key]["outputs"][key] = value
    
    write_json_file(TRAIN_STATES_FILE, data)
    
    # Immediately sync controller outputs back to train_data.json
    # This ensures Train Model gets updates without waiting for sync cycle
    if any(key in output_fields for key in updates.keys()):
        sync_states_to_train_data()
    
    print(f"[Server] Train {train_id} state updated: {list(updates.keys())}")
    return jsonify({"message": "State updated", "state": data[train_key]}), 200

@app.route('/api/trains', methods=['GET'])
def get_all_trains():
    """Get all train states."""
    data = read_json_file(TRAIN_STATES_FILE)
    
    # Filter to only return train_X entries
    trains = {k: v for k, v in data.items() if k.startswith('train_')}
    
    return jsonify(trains), 200

@app.route('/api/train/<int:train_id>/reset', methods=['POST'])
def reset_train_state(train_id):
    """Reset a train to default state."""
    data = read_json_file(TRAIN_STATES_FILE)
    train_key = f"train_{train_id}"
    
    default_state = {
        "inputs": {
            "commanded_speed": 0.0,
            "commanded_authority": 0.0,
            "speed_limit": 0.0,
            "train_velocity": 0.0,
            "next_stop": "",
            "station_side": "",
            "train_temperature": 70.0,
            "current_station": "",
            "train_model_engine_failure": False,
            "train_model_signal_failure": False,
            "train_model_brake_failure": False,
            "train_controller_engine_failure": False,
            "train_controller_signal_failure": False,
            "train_controller_brake_failure": False,
            "beacon_read_blocked": False
        },
        "outputs": {
            "manual_mode": False,
            "driver_velocity": 0.0,
            "service_brake": False,
            "emergency_brake": False,
            "right_door": False,
            "left_door": False,
            "interior_lights": True,
            "exterior_lights": True,
            "set_temperature": 70.0,
            "temperature_up": False,
            "temperature_down": False,
            "announcement": "",
            "announce_pressed": False,
            "kp": None,
            "ki": None,
            "engineering_panel_locked": False,
            "power_command": 0.0
        }
    }
    
    data[train_key] = default_state
    write_json_file(TRAIN_STATES_FILE, data)
    
    print(f"[Server] Train {train_id} reset to defaults")
    return jsonify({"message": "State reset", "state": default_state}), 200

@app.route('/api/train/<int:train_id>', methods=['DELETE'])
def delete_train(train_id):
    """Delete a train's state."""
    data = read_json_file(TRAIN_STATES_FILE)
    train_key = f"train_{train_id}"
    
    if train_key in data:
        del data[train_key]
        write_json_file(TRAIN_STATES_FILE, data)
        print(f"[Server] Train {train_id} deleted")
        return jsonify({"message": f"Train {train_id} deleted"}), 200
    else:
        return jsonify({"error": f"Train {train_id} not found"}), 404

# ========== Train Physics Endpoints (for Train Model) ==========

@app.route('/api/train/<int:train_id>/physics', methods=['GET'])
def get_train_physics(train_id):
    """Get train physics data from train_data.json.
    
    Returns physics outputs: velocity, acceleration, position, temperature, etc.
    This is used by Train Model UI to display current state.
    """
    train_data = read_json_file(TRAIN_DATA_FILE)
    train_key = f"train_{train_id}"
    
    if train_key in train_data:
        section = train_data[train_key]
        physics = section.get("outputs", {})
        return jsonify(physics), 200
    else:
        return jsonify({"error": f"Train {train_id} physics data not found"}), 404

@app.route('/api/train/<int:train_id>/physics', methods=['POST'])
def update_train_physics(train_id):
    """Update train physics outputs from Train Model.
    
    Train Model writes its physics simulation results here:
    - velocity_mph, acceleration_ftps2, position_yds
    - temperature_F, passengers_onboard, door states, etc.
    """
    updates = request.json
    if not updates:
        return jsonify({"error": "No data provided"}), 400
    
    train_data = read_json_file(TRAIN_DATA_FILE)
    train_key = f"train_{train_id}"
    
    # Initialize train physics section if it doesn't exist
    if train_key not in train_data:
        train_data[train_key] = {"inputs": {}, "outputs": {}, "specs": {}}
    
    if "outputs" not in train_data[train_key]:
        train_data[train_key]["outputs"] = {}
    
    # Update outputs section with physics data
    train_data[train_key]["outputs"].update(updates)
    
    write_json_file(TRAIN_DATA_FILE, train_data)
    
    print(f"[Server] Train {train_id} physics updated: {list(updates.keys())}")
    return jsonify({"message": "Physics updated", "physics": train_data[train_key]["outputs"]}), 200

@app.route('/api/train/<int:train_id>/inputs', methods=['GET'])
def get_train_inputs(train_id):
    """Get train inputs from train_data.json.
    
    Returns controller commands: power_command, brake states, door commands, etc.
    Train Model reads these to control the train simulation.
    """
    train_data = read_json_file(TRAIN_DATA_FILE)
    train_key = f"train_{train_id}"
    
    if train_key in train_data:
        section = train_data[train_key]
        inputs = section.get("inputs", {})
        return jsonify(inputs), 200
    else:
        return jsonify({"error": f"Train {train_id} inputs not found"}), 404

# ========== CTC Endpoints ==========

@app.route('/api/ctc/trains', methods=['GET'])
def get_ctc_trains():
    """Get all CTC train dispatch data.
    
    Returns train commands, speeds, authorities, stations, etc.
    """
    try:
        ctc_data_file = os.path.join(os.path.dirname(os.path.dirname(DATA_DIR)), "ctc_data.json")
        ctc_data = read_json_file(ctc_data_file)
        
        # Return dispatcher trains section
        trains = ctc_data.get("Dispatcher", {}).get("Trains", {})
        return jsonify(trains), 200
    except Exception as e:
        print(f"[Server] Error reading CTC data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ctc/train/<int:train_id>/command', methods=['POST'])
def send_ctc_command(train_id):
    """Send CTC command to train (speed, authority).
    
    CTC uses this to command trains with suggested speed and authority.
    Updates train_states.json inputs section.
    """
    command = request.json
    if not command:
        return jsonify({"error": "No command provided"}), 400
    
    # Extract speed and authority
    commanded_speed = command.get('commanded_speed', command.get('speed'))
    commanded_authority = command.get('commanded_authority', command.get('authority'))
    
    if commanded_speed is None or commanded_authority is None:
        return jsonify({"error": "Must provide commanded_speed and commanded_authority"}), 400
    
    # Update train state
    data = read_json_file(TRAIN_STATES_FILE)
    train_key = f"train_{train_id}"
    
    if train_key not in data:
        return jsonify({"error": f"Train {train_id} not found"}), 404
    
    # Update inputs section
    if "inputs" not in data[train_key]:
        data[train_key]["inputs"] = {}
    
    data[train_key]["inputs"]["commanded_speed"] = float(commanded_speed)
    data[train_key]["inputs"]["commanded_authority"] = float(commanded_authority)
    
    write_json_file(TRAIN_STATES_FILE, data)
    
    print(f"[Server] CTC command sent to Train {train_id}: speed={commanded_speed}, authority={commanded_authority}")
    return jsonify({"message": "Command sent", "train_id": train_id}), 200

@app.route('/api/ctc/dispatch', methods=['POST'])
def dispatch_train_ctc():
    """Dispatch new train from CTC.
    
    Creates new train entry with specified line, station, and arrival time.
    """
    dispatch_data = request.json
    if not dispatch_data:
        return jsonify({"error": "No dispatch data provided"}), 400
    
    try:
        ctc_data_file = os.path.join(os.path.dirname(os.path.dirname(DATA_DIR)), "ctc_data.json")
        ctc_data = read_json_file(ctc_data_file)
        
        if "Dispatcher" not in ctc_data:
            ctc_data["Dispatcher"] = {}
        if "Trains" not in ctc_data["Dispatcher"]:
            ctc_data["Dispatcher"]["Trains"] = {}
        
        train_name = dispatch_data.get("train", "Train 1")
        ctc_data["Dispatcher"]["Trains"][train_name] = {
            "Line": dispatch_data.get("line", ""),
            "Suggested Speed": dispatch_data.get("speed", ""),
            "Authority": dispatch_data.get("authority", ""),
            "Station Destination": dispatch_data.get("station", ""),
            "Arrival Time": dispatch_data.get("arrival_time", ""),
            "Position": "",
            "State": "",
            "Current Station": ""
        }
        
        write_json_file(ctc_data_file, ctc_data)
        
        print(f"[Server] Train dispatched: {train_name}")
        return jsonify({"message": "Train dispatched", "train": train_name}), 200
    except Exception as e:
        print(f"[Server] Error dispatching train: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ctc/occupancy', methods=['GET'])
def get_ctc_occupancy():
    """Get track occupancy from wayside controllers.
    
    Returns array of occupied blocks for CTC display.
    """
    try:
        ctc_input_file = os.path.join(os.path.dirname(os.path.dirname(DATA_DIR)), "hw_wayside_to_ctc.json")
        ctc_data = read_json_file(ctc_input_file)
        
        occupancy = ctc_data.get("G-Occupancy", [])
        return jsonify({"occupancy": occupancy}), 200
    except Exception as e:
        print(f"[Server] Error reading occupancy: {e}")
        return jsonify({"error": str(e)}), 500

# ========== Wayside/Track Controller Endpoints ==========

@app.route('/api/wayside/state', methods=['GET'])
def get_wayside_state():
    """Get all wayside controller state.
    
    Returns switches, lights, gates, and occupancy for all wayside controllers.
    """
    try:
        # Read from track model output file
        wayside_file = os.path.join(os.path.dirname(os.path.dirname(DATA_DIR)), "track_controller", "New_SW_Code", "track_to_wayside.json")
        wayside_data = read_json_file(wayside_file)
        
        return jsonify(wayside_data), 200
    except Exception as e:
        print(f"[Server] Error reading wayside state: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/wayside/state', methods=['POST'])
def update_wayside_state():
    """Update wayside state (switches, lights, gates, occupancy).
    
    Wayside controllers use this to report their output state.
    """
    updates = request.json
    if not updates:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        # Write to wayside output file
        wayside_file = os.path.join(os.path.dirname(os.path.dirname(DATA_DIR)), "hw_wayside_to_track.json")
        wayside_data = read_json_file(wayside_file)
        
        # Update with new data
        wayside_data.update(updates)
        
        write_json_file(wayside_file, wayside_data)
        
        print(f"[Server] Wayside state updated: {list(updates.keys())}")
        return jsonify({"message": "Wayside state updated"}), 200
    except Exception as e:
        print(f"[Server] Error updating wayside state: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/wayside/switches', methods=['POST'])
def update_wayside_switches():
    """Update switch positions.
    
    Wayside controllers use this to report switch state changes.
    """
    switch_data = request.json
    if not switch_data:
        return jsonify({"error": "No switch data provided"}), 400
    
    try:
        wayside_file = os.path.join(os.path.dirname(os.path.dirname(DATA_DIR)), "hw_wayside_to_track.json")
        wayside_data = read_json_file(wayside_file)
        
        if "G-switches" not in wayside_data:
            wayside_data["G-switches"] = []
        
        # Update switches
        switches = switch_data.get("switches", [])
        wayside_data["G-switches"] = switches
        
        write_json_file(wayside_file, wayside_data)
        
        print(f"[Server] Switches updated: {len(switches)} switches")
        return jsonify({"message": "Switches updated"}), 200
    except Exception as e:
        print(f"[Server] Error updating switches: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/wayside/lights', methods=['POST'])
def update_wayside_lights():
    """Update light states.
    
    Wayside controllers use this to report light state changes.
    """
    light_data = request.json
    if not light_data:
        return jsonify({"error": "No light data provided"}), 400
    
    try:
        wayside_file = os.path.join(os.path.dirname(os.path.dirname(DATA_DIR)), "hw_wayside_to_track.json")
        wayside_data = read_json_file(wayside_file)
        
        if "G-lights" not in wayside_data:
            wayside_data["G-lights"] = []
        
        # Update lights
        lights = light_data.get("lights", [])
        wayside_data["G-lights"] = lights
        
        write_json_file(wayside_file, wayside_data)
        
        print(f"[Server] Lights updated: {len(lights)} lights")
        return jsonify({"message": "Lights updated"}), 200
    except Exception as e:
        print(f"[Server] Error updating lights: {e}")
        return jsonify({"error": str(e)}), 500

# ========== CORRECTED MODULE-BOUNDARY-RESPECTING ENDPOINTS ==========

# CTC Endpoints (interact with ctc_track_controller.json)
@app.route('/api/ctc/commands', methods=['POST'])
def set_ctc_commands():
    """CTC sends commands to wayside via ctc_track_controller.json.
    
    CORRECT BOUNDARY: CTC → ctc_track_controller.json → Wayside
    """
    command_data = request.json
    if not command_data:
        return jsonify({"error": "No command data provided"}), 400
    
    try:
        ctc_data = read_json_file(CTC_TRACK_CONTROLLER_FILE)
        
        # Ensure structure exists
        if "Trains" not in ctc_data:
            ctc_data["Trains"] = {}
        
        # Update train commands
        train_name = command_data.get("train", "Train 1")
        if train_name not in ctc_data["Trains"]:
            ctc_data["Trains"][train_name] = {
                "Active": 0,
                "Suggested Speed": 0,
                "Suggested Authority": 0,
                "Train Position": 0,
                "Train State": ""
            }
        
        # Update commanded values
        if "speed" in command_data:
            ctc_data["Trains"][train_name]["Suggested Speed"] = float(command_data["speed"])
        if "authority" in command_data:
            ctc_data["Trains"][train_name]["Suggested Authority"] = float(command_data["authority"])
        if "active" in command_data:
            ctc_data["Trains"][train_name]["Active"] = int(command_data["active"])
        
        write_json_file(CTC_TRACK_CONTROLLER_FILE, ctc_data)
        
        print(f"[Server] CTC command sent to {train_name}: speed={command_data.get('speed')}, auth={command_data.get('authority')}")
        return jsonify({"message": "Command sent to wayside"}), 200
    except Exception as e:
        print(f"[Server] Error setting CTC commands: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ctc/status', methods=['GET'])
def get_ctc_status():
    """CTC reads status from wayside via ctc_track_controller.json.
    
    CORRECT BOUNDARY: Wayside → ctc_track_controller.json → CTC
    """
    try:
        ctc_data = read_json_file(CTC_TRACK_CONTROLLER_FILE)
        return jsonify(ctc_data), 200
    except Exception as e:
        print(f"[Server] Error reading CTC status: {e}")
        return jsonify({"error": str(e)}), 500

# Wayside Endpoints
@app.route('/api/wayside/ctc_commands', methods=['GET'])
def get_wayside_ctc_commands():
    """Wayside reads CTC commands from ctc_track_controller.json.
    
    CORRECT BOUNDARY: CTC → ctc_track_controller.json → Wayside
    """
    try:
        ctc_data = read_json_file(CTC_TRACK_CONTROLLER_FILE)
        return jsonify(ctc_data), 200
    except Exception as e:
        print(f"[Server] Error reading CTC commands for wayside: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/wayside/train_status', methods=['POST'])
def update_wayside_train_status():
    """Wayside writes train position/state back to ctc_track_controller.json.
    
    CORRECT BOUNDARY: Wayside → ctc_track_controller.json → CTC
    """
    status_data = request.json
    if not status_data:
        return jsonify({"error": "No status data provided"}), 400
    
    try:
        ctc_data = read_json_file(CTC_TRACK_CONTROLLER_FILE)
        
        if "Trains" not in ctc_data:
            ctc_data["Trains"] = {}
        
        train_name = status_data.get("train", "Train 1")
        if train_name not in ctc_data["Trains"]:
            ctc_data["Trains"][train_name] = {}
        
        # Update position and state from wayside
        if "position" in status_data:
            ctc_data["Trains"][train_name]["Train Position"] = int(status_data["position"])
        if "state" in status_data:
            ctc_data["Trains"][train_name]["Train State"] = status_data["state"]
        if "active" in status_data:
            ctc_data["Trains"][train_name]["Active"] = int(status_data["active"])
        
        write_json_file(CTC_TRACK_CONTROLLER_FILE, ctc_data)
        
        print(f"[Server] Wayside updated {train_name} status: pos={status_data.get('position')}")
        return jsonify({"message": "Train status updated"}), 200
    except Exception as e:
        print(f"[Server] Error updating train status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/wayside/train_physics', methods=['GET'])
def get_wayside_train_physics():
    """Wayside reads train physics from train_data.json.
    
    CORRECT BOUNDARY: Train Model → train_data.json → Wayside
    """
    try:
        train_data = read_json_file(TRAIN_DATA_FILE)
        # Return physics outputs for all trains
        return jsonify(train_data), 200
    except Exception as e:
        print(f"[Server] Error reading train physics: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/wayside/train_commands', methods=['POST'])
def set_wayside_train_commands():
    """Wayside writes commands to wayside_to_train.json.
    
    CORRECT BOUNDARY: Wayside → wayside_to_train.json → Train Model
    """
    command_data = request.json
    if not command_data:
        return jsonify({"error": "No command data provided"}), 400
    
    try:
        wayside_data = read_json_file(WAYSIDE_TO_TRAIN_FILE)
        
        train_name = command_data.get("train", "Train 1")
        if train_name not in wayside_data:
            wayside_data[train_name] = {
                "Commanded Speed": 0,
                "Commanded Authority": 0,
                "Beacon": {"Current Station": "", "Next Station": ""},
                "Train Speed": 0
            }
        
        # Ensure Beacon structure exists
        if "Beacon" not in wayside_data[train_name]:
            wayside_data[train_name]["Beacon"] = {"Current Station": "", "Next Station": ""}
        
        # Update commands
        if "commanded_speed" in command_data:
            wayside_data[train_name]["Commanded Speed"] = float(command_data["commanded_speed"])
        if "commanded_authority" in command_data:
            wayside_data[train_name]["Commanded Authority"] = float(command_data["commanded_authority"])
        
        # Update beacon data (Current Station AND Next Station)
        if "current_station" in command_data:
            wayside_data[train_name]["Beacon"]["Current Station"] = str(command_data["current_station"])
        if "next_station" in command_data:
            wayside_data[train_name]["Beacon"]["Next Station"] = str(command_data["next_station"])
        
        write_json_file(WAYSIDE_TO_TRAIN_FILE, wayside_data)
        
        print(f"[Server] Wayside set commands for {train_name}: speed={command_data.get('commanded_speed')}, auth={command_data.get('commanded_authority')}")
        return jsonify({"message": "Commands written to wayside_to_train.json"}), 200
    except Exception as e:
        print(f"[Server] Error writing wayside commands: {e}")
        return jsonify({"error": str(e)}), 500

# Train Model Endpoints
@app.route('/api/train_model/<int:train_id>/commands', methods=['GET'])
def get_train_model_commands(train_id):
    """Train Model reads commands from wayside_to_train.json.
    
    CORRECT BOUNDARY: Wayside → wayside_to_train.json → Train Model
    """
    try:
        print(f"[Server] Reading from: {WAYSIDE_TO_TRAIN_FILE}")
        wayside_data = read_json_file(WAYSIDE_TO_TRAIN_FILE)
        train_name = f"Train {train_id}"
        
        print(f"[Server] Looking for {train_name}, available trains: {list(wayside_data.keys())}")
        
        if train_name in wayside_data:
            print(f"[Server] Found {train_name} commands")
            return jsonify(wayside_data[train_name]), 200
        else:
            print(f"[Server] {train_name} not found in wayside_to_train.json")
            return jsonify({"error": f"{train_name} not found"}), 404
    except Exception as e:
        print(f"[Server] Error reading train model commands: {e}")
        return jsonify({"error": str(e)}), 500

# ========== Health Check ==========

@app.route('/api/health', methods=['GET'])
def health_check():
    """Check if server is running."""
    return jsonify({
        "status": "ok",
        "message": "Train API Server running",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information."""
    return jsonify({
        "name": "Train System REST API Server",
        "version": "2.0",
        "endpoints": {
            "GET /api/health": "Server health check",
            "GET /api/trains": "Get all train states",
            "GET /api/train/<id>/state": "Get specific train state",
            "POST /api/train/<id>/state": "Update train state",
            "POST /api/train/<id>/reset": "Reset train to defaults",
            "DELETE /api/train/<id>": "Delete train",
            "GET /api/train/<id>/physics": "Get train physics data",
            "POST /api/train/<id>/physics": "Update train physics",
            "GET /api/train/<id>/inputs": "Get train controller inputs",
            "GET /api/ctc/trains": "Get all CTC trains",
            "POST /api/ctc/train/<id>/command": "Send CTC command",
            "POST /api/ctc/dispatch": "Dispatch new train",
            "GET /api/ctc/occupancy": "Get track occupancy",
            "GET /api/wayside/state": "Get wayside state",
            "POST /api/wayside/state": "Update wayside state",
            "POST /api/wayside/switches": "Update switches",
            "POST /api/wayside/lights": "Update lights"
        }
    }), 200

if __name__ == '__main__':
    print("=" * 70)
    print("  TRAIN SYSTEM REST API SERVER v2.0 - BOUNDARY RESPECTING")
    print("=" * 70)
    print(f"\nData directory: {DATA_DIR}")
    print(f"\nCommunication Files:")
    print(f"  train_states.json: {TRAIN_STATES_FILE}")
    print(f"  train_data.json: {TRAIN_DATA_FILE}")
    print(f"  ctc_track_controller.json: {CTC_TRACK_CONTROLLER_FILE}")
    print(f"  wayside_to_train.json: {WAYSIDE_TO_TRAIN_FILE}")
    print(f"\nFile Check:")
    print(f"  train_states.json exists: {os.path.exists(TRAIN_STATES_FILE)}")
    print(f"  train_data.json exists: {os.path.exists(TRAIN_DATA_FILE)}")
    print(f"  ctc_track_controller.json exists: {os.path.exists(CTC_TRACK_CONTROLLER_FILE)}")
    print(f"  wayside_to_train.json exists: {os.path.exists(WAYSIDE_TO_TRAIN_FILE)}")
    print("\nServer starting on http://0.0.0.0:5000")
    print("All components should connect to: http://<server-ip>:5000\n")
    print("Available endpoints:")
    print("  Train Controller:")
    print("    GET  /api/train/<id>/state    - Get train state")
    print("    POST /api/train/<id>/state    - Update train state")
    print("  Train Model:")
    print("    GET  /api/train/<id>/physics  - Get physics data")
    print("    POST /api/train/<id>/physics  - Update physics")
    print("    GET  /api/train/<id>/inputs   - Get controller inputs")
    print("  CTC:")
    print("    GET  /api/ctc/trains          - Get all trains")
    print("    POST /api/ctc/train/<id>/cmd  - Send command")
    print("    POST /api/ctc/dispatch        - Dispatch train")
    print("    GET  /api/ctc/occupancy       - Get occupancy")
    print("  Wayside:")
    print("    GET  /api/wayside/state       - Get wayside state")
    print("    POST /api/wayside/state       - Update state")
    print("=" * 70)
    
    # Start background sync thread
    sync_thread = Thread(target=sync_train_data_to_states, daemon=True)
    sync_thread.start()
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n[Server] Shutting down...")
        sync_running = False
        sync_thread.join(timeout=2.0)
    finally:
        sync_running = False
