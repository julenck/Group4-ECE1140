"""Train Controller API Client for Raspberry Pi
Communicates with the central REST API server instead of local JSON files.

This client is used on Raspberry Pi devices to access train state
data from the central server over the network.

Author: James Struyk, Julen Coca-Knorr
"""
import requests
import json
from typing import Dict, Optional

class train_controller_api_client:
    """Client API that communicates with REST server."""
    
    def __init__(self, train_id: int, server_url: str = "http://192.168.1.100:5000"):
        """Initialize API client.
        
        Args:
            train_id: The train ID this client manages.
            server_url: URL of the REST API server (e.g., "http://192.168.1.100:5000")
        """
        self.train_id = train_id
        self.server_url = server_url.rstrip('/')
        self.state_endpoint = f"{self.server_url}/api/train/{train_id}/state"
        
        # Default state (fallback if server unreachable)
        self.default_state = {
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
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test connection to server."""
        try:
            health = requests.get(f"{self.server_url}/api/health", timeout=2)
            if health.status_code == 200:
                print(f"[API Client] ✓ Connected to server: {self.server_url}")
                print(f"[API Client] ✓ Managing Train {self.train_id}")
            else:
                print(f"[API Client] ⚠ Server responded with status {health.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[API Client] ✗ ERROR: Cannot reach server at {self.server_url}")
            print(f"[API Client] ✗ Error: {e}")
            print(f"[API Client] ⚠ Using fallback local state")
    
    def get_state(self) -> dict:
        """Get current train state from server.
        
        Returns:
            dict: Current train state. Returns default state if server unreachable.
        """
        try:
            response = requests.get(self.state_endpoint, timeout=1)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                # Train doesn't exist yet, return defaults
                print(f"[API Client] Train {self.train_id} not found on server, using defaults")
                return self.default_state.copy()
            else:
                print(f"[API Client] Server error {response.status_code}, using local cache")
                return self.default_state.copy()
        except requests.exceptions.RequestException as e:
            print(f"[API Client] Request failed: {e}, using local cache")
            return self.default_state.copy()
    
    def update_state(self, state_dict: dict) -> None:
        """Update train state on server.
        
        Args:
            state_dict: Dictionary of state values to update.
        """
        try:
            response = requests.post(self.state_endpoint, json=state_dict, timeout=1)
            if response.status_code != 200:
                print(f"[API Client] Update failed with status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[API Client] Update request failed: {e}")
    
    def save_state(self, state: dict) -> None:
        """Save complete train state to server.
        
        Args:
            state: Complete state dictionary to save.
        """
        # For compatibility with local API interface
        self.update_state(state)
    
    def reset_state(self) -> None:
        """Reset train state to defaults on server."""
        try:
            reset_endpoint = f"{self.server_url}/api/train/{self.train_id}/reset"
            response = requests.post(reset_endpoint, timeout=1)
            if response.status_code == 200:
                print(f"[API Client] Train {self.train_id} state reset")
            else:
                print(f"[API Client] Reset failed with status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[API Client] Reset request failed: {e}")
    
    def receive_from_train_model(self, data: dict) -> None:
        """Receive updates from Train Model.
        
        Args:
            data: Dictionary containing Train Model outputs
        """
        # Filter relevant data from train model
        relevant_data = {
            k: v for k, v in data.items() 
            if k in ['commanded_speed', 'commanded_authority', 'speed_limit',
                    'train_velocity', 'next_stop', 'station_side', 'train_temperature',
                    'engine_failure', 'signal_failure', 'brake_failure', 'manual_mode']
        }
        
        self.update_state(relevant_data)
    
    def send_to_train_model(self) -> dict:
        """Send control outputs to Train Model.
        
        Returns:
            dict: Control outputs for Train Model
        """
        state = self.get_state()
        return {
            'power_command': state.get('power_command', 0.0),
            'service_brake': state.get('service_brake', False),
            'emergency_brake': state.get('emergency_brake', False),
            'right_door': state.get('right_door', False),
            'left_door': state.get('left_door', False),
            'interior_lights': state.get('interior_lights', True),
            'exterior_lights': state.get('exterior_lights', True),
            'temperature_up': state.get('temperature_up', False),
            'temperature_down': state.get('temperature_down', False)
        }


if __name__ == "__main__":
    # Test the client
    import sys
    
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    else:
        server_url = "http://192.168.1.100:5000"
    
    print(f"Testing API Client with server: {server_url}")
    
    client = train_controller_api_client(train_id=1, server_url=server_url)
    
    print("\n--- Getting current state ---")
    state = client.get_state()
    print(f"Train velocity: {state.get('train_velocity', 0)} mph")
    print(f"Service brake: {state.get('service_brake', False)}")
    
    print("\n--- Updating state ---")
    client.update_state({"service_brake": True, "driver_velocity": 30.0})
    
    print("\n--- Getting updated state ---")
    state = client.get_state()
    print(f"Service brake: {state.get('service_brake', False)}")
    print(f"Driver velocity: {state.get('driver_velocity', 0)} mph")
