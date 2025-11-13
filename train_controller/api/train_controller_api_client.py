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
    
    def __init__(self, train_id: int, server_url: str = "http://192.168.1.100:5000", 
                 timeout: float = 5.0, max_retries: int = 3):
        """Initialize API client.
        
        Args:
            train_id: The train ID this client manages.
            server_url: URL of the REST API server (e.g., "http://192.168.1.100:5000")
            timeout: Request timeout in seconds (default: 5.0)
            max_retries: Maximum number of retries for failed requests (default: 3)
        """
        self.train_id = train_id
        self.server_url = server_url.rstrip('/')
        self.state_endpoint = f"{self.server_url}/api/train/{train_id}/state"
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Cache for state when server is unreachable
        self._cached_state = None
        
        # Default state (fallback if server unreachable)
        self.default_state = {
            "train_id": train_id,
            # Inputs FROM Train Model
            "commanded_speed": 0.0,
            "commanded_authority": 0.0,
            "speed_limit": 0.0,
            "train_velocity": 0.0,
            "current_station": "",
            "next_stop": "",
            "station_side": "",
            "train_temperature": 70.0,
            
            # Train Model Failure Flags (activated by Train Model)
            "train_model_engine_failure": False,
            "train_model_signal_failure": False,
            "train_model_brake_failure": False,
            
            # Train Controller Failure Flags (detected by Train Controller)
            "train_controller_engine_failure": False,
            "train_controller_signal_failure": False,
            "train_controller_brake_failure": False,
            
            # Signal for Train Controller (set by Train Model when beacon read is blocked)
            "beacon_read_blocked": False,
            
            # Internal Train Controller State
            "manual_mode": False,
            "driver_velocity": 0.0,
            "service_brake": False,
            "right_door": False,
            "left_door": False,
            "interior_lights": False,
            "exterior_lights": False,
            "set_temperature": 70.0,
            "temperature_up": False,
            "temperature_down": False,
            "announcement": "",
            "announce_pressed": False,
            "emergency_brake": False,
            "kp": 0.0,
            "ki": 0.0,
            "engineering_panel_locked": False,
            
            # Outputs TO Train Model
            "power_command": 0.0
        }
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test connection to server."""
        try:
            health = requests.get(f"{self.server_url}/api/health", timeout=self.timeout)
            if health.status_code == 200:
                print(f"[API Client] ✓ Connected to server: {self.server_url}")
                print(f"[API Client] ✓ Managing Train {self.train_id}")
                print(f"[API Client] ✓ Timeout: {self.timeout}s, Max retries: {self.max_retries}")
            else:
                print(f"[API Client] ⚠ Server responded with status {health.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[API Client] ✗ ERROR: Cannot reach server at {self.server_url}")
            print(f"[API Client] ✗ Error: {e}")
            print(f"[API Client] ⚠ Using fallback local state")
    
    def get_state(self) -> dict:
        """Get current train state from server.
        
        Returns:
            dict: Current train state. Returns cached/default state if server unreachable.
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.get(self.state_endpoint, timeout=self.timeout)
                if response.status_code == 200:
                    state = response.json()
                    self._cached_state = state  # Update cache
                    return state
                elif response.status_code == 404:
                    # Train doesn't exist yet, return defaults
                    if attempt == 0:  # Only print once
                        print(f"[API Client] Train {self.train_id} not found on server, using defaults")
                    return self.default_state.copy()
                else:
                    if attempt == self.max_retries - 1:
                        print(f"[API Client] Server error {response.status_code}, using cache")
                    
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[API Client] Request timed out after {self.timeout}s (attempt {attempt + 1}/{self.max_retries})")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[API Client] Request failed: {e}")
        
        # All retries failed - use cached state or default
        if self._cached_state is not None:
            return self._cached_state.copy()
        return self.default_state.copy()
    
    def update_state(self, state_dict: dict) -> None:
        """Update train state on server.
        
        Args:
            state_dict: Dictionary of state values to update.
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.state_endpoint, json=state_dict, timeout=self.timeout)
                if response.status_code == 200:
                    # Update local cache with successful write
                    if self._cached_state is not None:
                        self._cached_state.update(state_dict)
                    return  # Success
                elif attempt == self.max_retries - 1:
                    print(f"[API Client] Update failed with status {response.status_code}")
                    
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[API Client] Update timed out after {self.timeout}s (attempt {attempt + 1}/{self.max_retries})")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[API Client] Update request failed: {e}")
        
        # Update local cache even if server update failed
        if self._cached_state is not None:
            self._cached_state.update(state_dict)
    
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
            response = requests.post(reset_endpoint, timeout=self.timeout)
            if response.status_code == 200:
                print(f"[API Client] Train {self.train_id} state reset")
                self._cached_state = None  # Clear cache
            else:
                print(f"[API Client] Reset failed with status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[API Client] Reset request failed: {e}")
    
    def update_from_train_data(self) -> None:
        """Stub method for compatibility with local API.
        
        In client mode, the server handles reading from train_data.json.
        The Train Model writes directly to the server, so this is a no-op.
        """
        pass
    
    def receive_from_train_model(self, data: dict) -> None:
        """Receive updates from Train Model.
        
        Args:
            data: Dictionary containing Train Model outputs
        """
        # Filter relevant data from train model
        # NOTE: manual_mode is controller-only state, not from Train Model
        relevant_data = {
            k: v for k, v in data.items() 
            if k in ['commanded_speed', 'commanded_authority', 'speed_limit',
                    'train_velocity', 'current_station', 'next_stop', 'station_side', 
                    'train_temperature', 'train_model_engine_failure', 
                    'train_model_signal_failure', 'train_model_brake_failure',
                    'beacon_read_blocked']
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
