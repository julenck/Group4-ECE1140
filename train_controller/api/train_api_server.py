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
from threading import Lock
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from Raspberry Pis

# File paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
DATA_DIR = os.path.join(parent_dir, "data")
TRAIN_STATES_FILE = os.path.join(DATA_DIR, "train_states.json")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Thread-safe file access
file_lock = Lock()

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
            "kp": 0.0,
            "ki": 0.0,
            "next_stop": "Station A",
            "station_side": "Right",
            "train_temperature": 70.0,
            "set_temperature": 70.0,
            "engine_failure": False,
            "signal_failure": False,
            "brake_failure": False,
            "manual_mode": False,
            "right_door": False,
            "left_door": False,
            "interior_lights": True,
            "exterior_lights": True,
            "temperature_up": False,
            "temperature_down": False,
            "announcement": "",
            "announce_pressed": False,
            "engineering_panel_locked": False
        }
    
    # Update with provided values
    data[train_key].update(updates)
    data[train_key]["train_id"] = train_id  # Ensure train_id is always set
    
    write_json_file(TRAIN_STATES_FILE, data)
    
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
        "train_id": train_id,
        "commanded_speed": 0.0,
        "commanded_authority": 0.0,
        "speed_limit": 0.0,
        "train_velocity": 0.0,
        "next_stop": "Station A",
        "station_side": "Right",
        "train_temperature": 70.0,
        "engine_failure": False,
        "signal_failure": False,
        "brake_failure": False,
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
        "kp": 0.0,
        "ki": 0.0,
        "engineering_panel_locked": False,
        "power_command": 0.0
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
    print("\nServer starting on http://0.0.0.0:5000")
    print("Raspberry Pis should connect to: http://<server-ip>:5000\n")
    print("Available endpoints:")
    print("  GET  /api/health              - Server health check")
    print("  GET  /api/trains              - Get all trains")
    print("  GET  /api/train/<id>/state    - Get train state")
    print("  POST /api/train/<id>/state    - Update train state")
    print("  POST /api/train/<id>/reset    - Reset train state")
    print("=" * 70)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
