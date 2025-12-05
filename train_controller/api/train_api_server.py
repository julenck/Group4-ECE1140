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
DATA_DIR = os.path.join(parent_dir, "data")
TRAIN_STATES_FILE = os.path.join(DATA_DIR, "train_states.json")
TRAIN_DATA_FILE = os.path.join(os.path.dirname(parent_dir), "Train Model", "train_data.json")

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
    """Thread-safe JSON file write."""
    with file_lock:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[Server] Error writing {filepath}: {e}")

def sync_states_to_train_data():
    """Sync controller outputs from train_states.json to train_data.json.
    
    This writes controller outputs (power_command, etc.) back to train_data.json
    so the Train Model can read and apply them.
    """
    try:
        # Read current states
        train_states = read_json_file(TRAIN_STATES_FILE)
        train_data = read_json_file(TRAIN_DATA_FILE)
        
        if not train_states:
            return
        
        # For each train in states, update its outputs in train_data
        for key in train_states.keys():
            if key.startswith("train_"):
                train_section = train_states[key]
                outputs = train_section.get("outputs", {})
                
                # Ensure train exists in train_data
                if key not in train_data:
                    train_data[key] = {"inputs": {}, "outputs": {}}
                if "outputs" not in train_data[key]:
                    train_data[key]["outputs"] = {}
                
                # Update outputs in train_data from train_states
                # These are the controller outputs that Train Model needs
                controller_outputs = {
                    "power_command": outputs.get("power_command", 0.0),
                    "service_brake": outputs.get("service_brake", False),
                    "emergency_brake": outputs.get("emergency_brake", False),
                    "left_door": outputs.get("left_door", False),
                    "right_door": outputs.get("right_door", False),
                    "interior_lights": outputs.get("interior_lights", True),
                    "exterior_lights": outputs.get("exterior_lights", True),
                    "set_temperature": outputs.get("set_temperature", 70.0)
                }
                
                train_data[key]["outputs"].update(controller_outputs)
        
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
                    if key not in train_states:
                        # Extract train_id from key
                        train_id = int(key.split("_")[1])
                        train_states[key] = {
                            "inputs": {
                                "commanded_speed": 0.0,
                                "commanded_authority": 0.0,
                                "speed_limit": 0.0,
                                "train_velocity": 0.0,
                                "next_stop": "",
                                "station_side": "Right",
                                "train_temperature": 70.0,
                                "train_model_engine_failure": False,
                                "train_model_signal_failure": False,
                                "train_model_brake_failure": False,
                                "train_controller_engine_failure": False,
                                "train_controller_signal_failure": False,
                                "train_controller_brake_failure": False,
                                "current_station": "",
                                "beacon_read_blocked": False
                            },
                            "outputs": {
                                "manual_mode": False,
                                "driver_velocity": 0.0,
                                "service_brake": False,
                                "right_door": False,
                                "left_door": False,
                                "interior_lights": True,
                                "exterior_lights": True,
                                "set_temperature": 70.0,
                                "temperature_up": False,
                                "temperature_down": False,
                                "announcement": "",
                                "announce_pressed": False,
                                "emergency_brake": False,
                                "kp": None,
                                "ki": None,
                                "engineering_panel_locked": False,
                                "power_command": 0.0
                            }
                        }
                    
                    # Ensure inputs/outputs structure exists (handle legacy flat format)
                    if "inputs" not in train_states[key]:
                        train_states[key] = {
                            "inputs": {},
                            "outputs": {}
                        }
                    
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
                    train_states[key]["inputs"]["station_side"] = inputs.get("side_door", "Right")
            
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
    """Get state for a specific train."""
    data = read_json_file(TRAIN_STATES_FILE)
    train_key = f"train_{train_id}"
    
    if train_key in data:
        return jsonify(data[train_key]), 200
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
                "station_side": "Right",
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
    if "inputs" not in data[train_key]:
        data[train_key] = {"inputs": {}, "outputs": {}}
    
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
            "station_side": "Right",
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
        "version": "1.0",
        "endpoints": {
            "GET /api/health": "Server health check",
            "GET /api/trains": "Get all train states",
            "GET /api/train/<id>/state": "Get specific train state",
            "POST /api/train/<id>/state": "Update train state",
            "POST /api/train/<id>/reset": "Reset train to defaults",
            "DELETE /api/train/<id>": "Delete train"
        }
    }), 200

if __name__ == '__main__':
    print("=" * 70)
    print("  TRAIN SYSTEM REST API SERVER")
    print("=" * 70)
    print(f"\nData directory: {DATA_DIR}")
    print(f"State file: {TRAIN_STATES_FILE}")
    print(f"Train data file: {TRAIN_DATA_FILE}")
    print("\nServer starting on http://0.0.0.0:5000")
    print("Raspberry Pis should connect to: http://<server-ip>:5000\n")
    print("Available endpoints:")
    print("  GET  /api/health              - Server health check")
    print("  GET  /api/trains              - Get all trains")
    print("  GET  /api/train/<id>/state    - Get train state")
    print("  POST /api/train/<id>/state    - Update train state")
    print("  POST /api/train/<id>/reset    - Reset train state")
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
