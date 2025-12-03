"""Unified REST API Server for Complete Railway System
Manages all JSON state files and provides endpoints for all components:
- Train Controller (existing)
- Track Controller (Wayside) 
- CTC (Centralized Traffic Control)
- Track Model

This server runs on the main computer and allows Raspberry Pi devices
to access all system data over the network.

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

# ========== File Paths ==========
current_dir = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = current_dir

# Train Controller files
TRAIN_CONTROLLER_DIR = os.path.join(BASE_DIR, "train_controller", "data")
TRAIN_STATES_FILE = os.path.join(TRAIN_CONTROLLER_DIR, "train_states.json")
TRAIN_DATA_FILE = os.path.join(BASE_DIR, "Train_Model", "train_data.json")

# Track Controller (Wayside) files
TRACK_CONTROLLER_DIR = os.path.join(BASE_DIR, "track_controller", "New_SW_Code")
CTC_TRACK_CONTROLLER_FILE = os.path.join(BASE_DIR, "ctc_track_controller.json")
TRACK_TO_WAYSIDE_FILE = os.path.join(TRACK_CONTROLLER_DIR, "track_to_wayside.json")
WAYSIDE_TO_TRAIN_FILE = os.path.join(TRACK_CONTROLLER_DIR, "wayside_to_train.json")

# CTC files
CTC_DATA_FILE = os.path.join(BASE_DIR, "ctc_data.json")

# Track Model files
TRACK_MODEL_FILE = os.path.join(BASE_DIR, "track_model_Train_Model.json")

# Ensure directories exist
os.makedirs(TRAIN_CONTROLLER_DIR, exist_ok=True)
os.makedirs(TRACK_CONTROLLER_DIR, exist_ok=True)

# Thread-safe file access
file_lock = Lock()
sync_running = True  # Flag to control sync thread

# ========== Helper Functions ==========

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
            # Write to temp file first, then rename (atomic operation)
            temp_filepath = filepath + ".tmp"
            with open(temp_filepath, 'w') as f:
                json.dump(data, f, indent=4)
            os.replace(temp_filepath, filepath)
        except Exception as e:
            print(f"[Server] Error writing {filepath}: {e}")

def safe_update(data, updates):
    """Safely update nested dictionary structure."""
    if not isinstance(updates, dict):
        return data
    
    for key, value in updates.items():
        if isinstance(value, dict) and key in data and isinstance(data[key], dict):
            safe_update(data[key], value)
        else:
            data[key] = value
    return data

# ========== TRAIN CONTROLLER ENDPOINTS ==========
# (Existing train controller API - already working)

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
    
    # Initialize train if it doesn't exist
    if train_key not in data:
        data[train_key] = {
            "train_id": train_id,
            "commanded_speed": 0.0,
            "commanded_authority": 0.0,
            "speed_limit": 0.0,
            "train_velocity": 0.0,
            "driver_velocity": 0.0,
            "service_brake": False,
            "emergency_brake": False,
            "power_command": 0.0,
        }
    
    # Update with provided values
    data[train_key].update(updates)
    data[train_key]["train_id"] = train_id
    
    write_json_file(TRAIN_STATES_FILE, data)
    
    print(f"[Server] Train {train_id} state updated: {list(updates.keys())}")
    return jsonify({"message": "State updated", "state": data[train_key]}), 200

@app.route('/api/trains', methods=['GET'])
def get_all_trains():
    """Get all train states."""
    data = read_json_file(TRAIN_STATES_FILE)
    trains = {k: v for k, v in data.items() if k.startswith('train_')}
    return jsonify(trains), 200

# ========== TRACK CONTROLLER (WAYSIDE) ENDPOINTS ==========

@app.route('/api/wayside/<int:wayside_id>/state', methods=['GET'])
def get_wayside_state(wayside_id):
    """Get state for a specific wayside controller.
    
    This replaces reading from ctc_track_controller.json and track_to_wayside.json
    """
    # Combine data from multiple sources
    ctc_data = read_json_file(CTC_TRACK_CONTROLLER_FILE)
    track_data = read_json_file(TRACK_TO_WAYSIDE_FILE)
    
    # Return combined state
    state = {
        "wayside_id": wayside_id,
        "ctc_commands": ctc_data.get("Trains", {}),
        "track_data": track_data,
        "timestamp": datetime.now().isoformat()
    }
    
    return jsonify(state), 200

@app.route('/api/wayside/<int:wayside_id>/state', methods=['POST', 'PUT'])
def update_wayside_state(wayside_id):
    """Update wayside controller state.
    
    This replaces writing to wayside_to_train.json
    """
    updates = request.json
    if not updates:
        return jsonify({"error": "No data provided"}), 400
    
    # Read current wayside output file
    data = read_json_file(WAYSIDE_TO_TRAIN_FILE)
    
    # Update with new data
    safe_update(data, updates)
    
    write_json_file(WAYSIDE_TO_TRAIN_FILE, data)
    
    print(f"[Server] Wayside {wayside_id} state updated")
    return jsonify({"message": "Wayside state updated", "state": data}), 200

@app.route('/api/wayside/train_commands', methods=['GET'])
def get_wayside_train_commands():
    """Get all train commands from wayside to trains.
    
    This is used by train model to read wayside_to_train.json
    """
    data = read_json_file(WAYSIDE_TO_TRAIN_FILE)
    return jsonify(data), 200

@app.route('/api/wayside/train_commands', methods=['POST'])
def update_wayside_train_commands():
    """Update train commands from wayside.
    
    This allows wayside to write commands for trains
    """
    updates = request.json
    if not updates:
        return jsonify({"error": "No data provided"}), 400
    
    data = read_json_file(WAYSIDE_TO_TRAIN_FILE)
    safe_update(data, updates)
    write_json_file(WAYSIDE_TO_TRAIN_FILE, data)
    
    print(f"[Server] Wayside train commands updated")
    return jsonify({"message": "Train commands updated", "data": data}), 200

# ========== CTC ENDPOINTS ==========

@app.route('/api/ctc/state', methods=['GET'])
def get_ctc_state():
    """Get CTC state data.
    
    This replaces reading from ctc_data.json
    """
    data = read_json_file(CTC_DATA_FILE)
    return jsonify(data), 200

@app.route('/api/ctc/state', methods=['POST', 'PUT'])
def update_ctc_state():
    """Update CTC state.
    
    This replaces writing to ctc_data.json
    """
    updates = request.json
    if not updates:
        return jsonify({"error": "No data provided"}), 400
    
    data = read_json_file(CTC_DATA_FILE)
    safe_update(data, updates)
    write_json_file(CTC_DATA_FILE, data)
    
    print(f"[Server] CTC state updated")
    return jsonify({"message": "CTC state updated", "state": data}), 200

@app.route('/api/ctc/trains', methods=['GET'])
def get_ctc_trains():
    """Get CTC train dispatcher data."""
    data = read_json_file(CTC_DATA_FILE)
    trains = data.get("Dispatcher", {}).get("Trains", {})
    return jsonify(trains), 200

@app.route('/api/ctc/trains/<train_name>', methods=['GET'])
def get_ctc_train(train_name):
    """Get specific train data from CTC."""
    data = read_json_file(CTC_DATA_FILE)
    trains = data.get("Dispatcher", {}).get("Trains", {})
    
    if train_name in trains:
        return jsonify(trains[train_name]), 200
    else:
        return jsonify({"error": f"Train {train_name} not found in CTC"}), 404

@app.route('/api/ctc/trains/<train_name>', methods=['POST', 'PUT'])
def update_ctc_train(train_name):
    """Update specific train in CTC dispatcher."""
    updates = request.json
    if not updates:
        return jsonify({"error": "No data provided"}), 400
    
    data = read_json_file(CTC_DATA_FILE)
    
    # Ensure structure exists
    if "Dispatcher" not in data:
        data["Dispatcher"] = {}
    if "Trains" not in data["Dispatcher"]:
        data["Dispatcher"]["Trains"] = {}
    
    # Update or create train
    if train_name not in data["Dispatcher"]["Trains"]:
        data["Dispatcher"]["Trains"][train_name] = {}
    
    data["Dispatcher"]["Trains"][train_name].update(updates)
    
    write_json_file(CTC_DATA_FILE, data)
    
    print(f"[Server] CTC train {train_name} updated")
    return jsonify({"message": "Train updated", "train": data["Dispatcher"]["Trains"][train_name]}), 200

@app.route('/api/ctc/track_controller', methods=['GET'])
def get_ctc_track_controller():
    """Get CTC to Track Controller commands.
    
    This replaces reading from ctc_track_controller.json
    """
    data = read_json_file(CTC_TRACK_CONTROLLER_FILE)
    return jsonify(data), 200

@app.route('/api/ctc/track_controller', methods=['POST', 'PUT'])
def update_ctc_track_controller():
    """Update CTC to Track Controller commands.
    
    This replaces writing to ctc_track_controller.json
    """
    updates = request.json
    if not updates:
        return jsonify({"error": "No data provided"}), 400
    
    data = read_json_file(CTC_TRACK_CONTROLLER_FILE)
    safe_update(data, updates)
    write_json_file(CTC_TRACK_CONTROLLER_FILE, data)
    
    print(f"[Server] CTC track controller commands updated")
    return jsonify({"message": "Track controller commands updated", "data": data}), 200

# ========== TRACK MODEL ENDPOINTS ==========

@app.route('/api/track_model/state', methods=['GET'])
def get_track_model_state():
    """Get track model state."""
    data = read_json_file(TRACK_MODEL_FILE)
    return jsonify(data), 200

@app.route('/api/track_model/state', methods=['POST', 'PUT'])
def update_track_model_state():
    """Update track model state."""
    updates = request.json
    if not updates:
        return jsonify({"error": "No data provided"}), 400
    
    data = read_json_file(TRACK_MODEL_FILE)
    safe_update(data, updates)
    write_json_file(TRACK_MODEL_FILE, data)
    
    print(f"[Server] Track model state updated")
    return jsonify({"message": "Track model updated", "data": data}), 200

@app.route('/api/track_model/blocks', methods=['GET'])
def get_track_blocks():
    """Get specific blocks from track model."""
    data = read_json_file(TRACK_MODEL_FILE)
    return jsonify(data), 200

# ========== HEALTH CHECK ==========

@app.route('/api/health', methods=['GET'])
def health_check():
    """Check if server is running."""
    return jsonify({
        "status": "ok",
        "message": "Unified Railway System API Server running",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "train_controller": True,
            "track_controller": True,
            "ctc": True,
            "track_model": True
        }
    }), 200

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information."""
    return jsonify({
        "name": "Unified Railway System REST API Server",
        "version": "2.0",
        "description": "Central server for all railway system components",
        "components": ["Train Controller", "Track Controller (Wayside)", "CTC", "Track Model"],
        "endpoints": {
            "health": "GET /api/health",
            "train_controller": {
                "get_all": "GET /api/trains",
                "get_train": "GET /api/train/<id>/state",
                "update_train": "POST /api/train/<id>/state"
            },
            "track_controller": {
                "get_wayside": "GET /api/wayside/<id>/state",
                "update_wayside": "POST /api/wayside/<id>/state",
                "get_train_commands": "GET /api/wayside/train_commands",
                "update_train_commands": "POST /api/wayside/train_commands"
            },
            "ctc": {
                "get_state": "GET /api/ctc/state",
                "update_state": "POST /api/ctc/state",
                "get_trains": "GET /api/ctc/trains",
                "get_train": "GET /api/ctc/trains/<name>",
                "update_train": "POST /api/ctc/trains/<name>",
                "get_track_commands": "GET /api/ctc/track_controller",
                "update_track_commands": "POST /api/ctc/track_controller"
            },
            "track_model": {
                "get_state": "GET /api/track_model/state",
                "update_state": "POST /api/track_model/state",
                "get_blocks": "GET /api/track_model/blocks"
            }
        }
    }), 200

# ========== Background Sync Threads ==========

def sync_train_data_to_states():
    """Background thread that syncs train_data.json to train_states.json."""
    global sync_running
    print("[Server] Train data sync thread started (500ms interval)")
    
    while sync_running:
        try:
            train_data = read_json_file(TRAIN_DATA_FILE)
            if not train_data:
                time.sleep(0.5)
                continue
            
            train_states = read_json_file(TRAIN_STATES_FILE)
            
            # Sync each train_X section
            for key in train_data.keys():
                if key.startswith("train_"):
                    section = train_data[key]
                    inputs = section.get("inputs", {})
                    outputs = section.get("outputs", {})
                    
                    if key not in train_states:
                        train_id = int(key.split("_")[1])
                        train_states[key] = {"train_id": train_id}
                    
                    # Update train_states with inputs from train_data
                    train_states[key]["commanded_speed"] = inputs.get("commanded speed", 0.0)
                    train_states[key]["commanded_authority"] = inputs.get("commanded authority", 0.0)
                    train_states[key]["speed_limit"] = inputs.get("speed limit", 0.0)
                    train_states[key]["train_velocity"] = outputs.get("velocity_mph", 0.0)
                    train_states[key]["train_temperature"] = outputs.get("temperature_F", 70.0)
            
            write_json_file(TRAIN_STATES_FILE, train_states)
            
        except Exception as e:
            print(f"[Server] Error in sync thread: {e}")
        
        time.sleep(0.5)
    
    print("[Server] Train data sync thread stopped")

# ========== Server Startup ==========

if __name__ == '__main__':
    print("=" * 80)
    print("  UNIFIED RAILWAY SYSTEM REST API SERVER")
    print("=" * 80)
    print(f"\n📂 Data Directories:")
    print(f"   Train Controller: {TRAIN_CONTROLLER_DIR}")
    print(f"   Track Controller: {TRACK_CONTROLLER_DIR}")
    print(f"   CTC: {BASE_DIR}")
    print(f"\n🌐 Server starting on http://0.0.0.0:5000")
    print(f"📡 Raspberry Pis should connect to: http://<server-ip>:5000")
    print(f"\n📋 Components:")
    print(f"   ✓ Train Controller")
    print(f"   ✓ Track Controller (Wayside)")
    print(f"   ✓ CTC (Centralized Traffic Control)")
    print(f"   ✓ Track Model")
    print("\n🔧 To stop the server, press Ctrl+C")
    print("=" * 80)
    
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

