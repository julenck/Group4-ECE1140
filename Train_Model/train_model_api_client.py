"""Train Model API Client
Communicates with the central REST API server for Train Model operations.

This client handles:
- Getting commanded speed, authority, and controller inputs from server
- Sending physics outputs (velocity, position, acceleration, temperature) to server
- Sending passenger data to server

Author: Generated for Phase 2 of REST API Refactor
"""
import requests
import json
from typing import Dict, Optional

class TrainModelAPIClient:
    """Client API for Train Model to communicate with REST server."""
    
    def __init__(self, train_id: int, server_url: str = "http://localhost:5000", 
                 timeout: float = 5.0, max_retries: int = 3):
        """Initialize Train Model API client.
        
        Args:
            train_id: The train ID this client manages
            server_url: URL of the REST API server (default: "http://localhost:5000")
            timeout: Request timeout in seconds (default: 5.0)
            max_retries: Maximum number of retries for failed requests (default: 3)
        """
        self.train_id = train_id
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Endpoints
        self.physics_endpoint = f"{self.server_url}/api/train/{train_id}/physics"
        self.inputs_endpoint = f"{self.server_url}/api/train/{train_id}/inputs"
        self.state_endpoint = f"{self.server_url}/api/train/{train_id}/state"
        
        # Cache for when server is unreachable
        self._cached_inputs = None
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test connection to server."""
        try:
            health = requests.get(f"{self.server_url}/api/health", timeout=self.timeout)
            if health.status_code == 200:
                print(f"[Train Model API] ✓ Connected to server: {self.server_url}")
                print(f"[Train Model API] ✓ Managing Train {self.train_id}")
            else:
                print(f"[Train Model API] ⚠ Server responded with status {health.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[Train Model API] ✗ ERROR: Cannot reach server at {self.server_url}")
            print(f"[Train Model API] ✗ Error: {e}")
            print(f"[Train Model API] ⚠ Will use cached data when available")
    
    def get_wayside_commands(self) -> Optional[Dict]:
        """Get commanded speed/authority from wayside via wayside_to_train.json.
        
        CORRECT BOUNDARY: Wayside → wayside_to_train.json → Train Model
        
        Returns commands from wayside including:
        - Commanded Speed
        - Commanded Authority
        - Beacon data (Current Station, Next Station)
        
        Returns:
            dict: Wayside commands for this train, or None if server unreachable
        """
        commands_endpoint = f"{self.server_url}/api/train_model/{self.train_id}/commands"
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(commands_endpoint, timeout=self.timeout)
                if response.status_code == 200:
                    commands = response.json()
                    return commands
                elif response.status_code == 404:
                    if attempt == 0:
                        print(f"[Train Model API] Train {self.train_id} commands not found")
                    return None
                else:
                    if attempt == self.max_retries - 1:
                        print(f"[Train Model API] Server error {response.status_code}")
                        
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[Train Model API] Request timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[Train Model API] Request failed: {e}")
        
        return None
    
    def get_control_outputs(self) -> Optional[Dict]:
        """Get control outputs from Train Controller via train_states.json.
        
        CORRECT BOUNDARY: Train Controller → train_states.json (outputs) → Train Model
        
        Returns control outputs from Train Controller including:
        - power_command
        - service_brake
        - emergency_brake
        - left_door, right_door
        - interior_lights, exterior_lights
        - set_temperature
        
        Returns:
            dict: Controller outputs for Train Model, or None if server unreachable
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.get(self.inputs_endpoint, timeout=self.timeout)
                if response.status_code == 200:
                    inputs = response.json()
                    self._cached_inputs = inputs  # Update cache
                    return inputs
                elif response.status_code == 404:
                    if attempt == 0:
                        print(f"[Train Model API] Train {self.train_id} not found on server")
                    return None
                else:
                    if attempt == self.max_retries - 1:
                        print(f"[Train Model API] Server error {response.status_code}")
                        
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[Train Model API] Request timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[Train Model API] Request failed: {e}")
        
        # All retries failed - use cached data
        if self._cached_inputs is not None:
            print(f"[Train Model API] Using cached control outputs")
            return self._cached_inputs
        return None
    
    def update_physics(self, velocity: float, position: float, acceleration: float, temperature: float) -> bool:
        """Send physics outputs to server.
        
        Args:
            velocity: Current train velocity (mph)
            position: Current train position (feet or meters)
            acceleration: Current acceleration (ft/s^2 or m/s^2)
            temperature: Current train temperature (°F)
            
        Returns:
            bool: True if successful, False otherwise
        """
        physics_data = {
            'velocity_mph': velocity,
            'position': position,
            'acceleration': acceleration,
            'temperature_F': temperature
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.physics_endpoint, json=physics_data, timeout=self.timeout)
                if response.status_code == 200:
                    return True
                elif attempt == self.max_retries - 1:
                    print(f"[Train Model API] Physics update failed with status {response.status_code}")
                    
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[Train Model API] Physics update timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[Train Model API] Physics update failed: {e}")
        
        return False
    
    def update_passengers(self, onboard: int, boarding: int, disembarking: int) -> bool:
        """Send passenger data to server.
        
        Args:
            onboard: Number of passengers currently on board
            boarding: Number of passengers boarding at current station
            disembarking: Number of passengers disembarking at current station
            
        Returns:
            bool: True if successful, False otherwise
        """
        passenger_data = {
            'passengers_onboard': onboard,
            'passengers_boarding': boarding,
            'passengers_disembarking': disembarking
        }
        
        # Update via state endpoint (physics endpoint is for physics only)
        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.state_endpoint, json=passenger_data, timeout=self.timeout)
                if response.status_code == 200:
                    return True
                elif attempt == self.max_retries - 1:
                    print(f"[Train Model API] Passenger update failed with status {response.status_code}")
                    
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[Train Model API] Passenger update timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[Train Model API] Passenger update failed: {e}")
        
        return False
    
    def update_beacon_data(self, current_station: str, next_stop: str, station_side: str) -> bool:
        """Send beacon data to server.
        
        Args:
            current_station: Name of current station
            next_stop: Name of next stop
            station_side: Side where doors should open ("Left", "Right", or "")
            
        Returns:
            bool: True if successful, False otherwise
        """
        beacon_data = {
            'current_station': current_station,
            'next_stop': next_stop,
            'station_side': station_side
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.state_endpoint, json=beacon_data, timeout=self.timeout)
                if response.status_code == 200:
                    return True
                elif attempt == self.max_retries - 1:
                    print(f"[Train Model API] Beacon update failed with status {response.status_code}")
                    
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[Train Model API] Beacon update timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[Train Model API] Beacon update failed: {e}")
        
        return False
    
    def update_failure_modes(self, engine_failure: bool = False, signal_failure: bool = False, 
                            brake_failure: bool = False) -> bool:
        """Send failure mode data to server.
        
        Args:
            engine_failure: Engine failure status
            signal_failure: Signal pickup failure status
            brake_failure: Brake failure status
            
        Returns:
            bool: True if successful, False otherwise
        """
        failure_data = {
            'train_model_engine_failure': engine_failure,
            'train_model_signal_failure': signal_failure,
            'train_model_brake_failure': brake_failure
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.state_endpoint, json=failure_data, timeout=self.timeout)
                if response.status_code == 200:
                    return True
                elif attempt == self.max_retries - 1:
                    print(f"[Train Model API] Failure mode update failed with status {response.status_code}")
                    
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[Train Model API] Failure mode update timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[Train Model API] Failure mode update failed: {e}")
        
        return False


if __name__ == "__main__":
    # Test the client
    import sys
    
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    else:
        server_url = "http://localhost:5000"
    
    print(f"Testing Train Model API Client with server: {server_url}")
    
    client = TrainModelAPIClient(train_id=1, server_url=server_url)
    
    print("\n--- Getting wayside commands (from wayside_to_train.json) ---")
    commands = client.get_wayside_commands()
    if commands:
        print(f"Commanded speed: {commands.get('Commanded Speed', 0)} mph")
        print(f"Commanded authority: {commands.get('Commanded Authority', 0)}")
        beacon = commands.get('Beacon', {})
        if beacon:
            print(f"Current station: {beacon.get('Current Station', 'N/A')}")
            print(f"Next station: {beacon.get('Next Station', 'N/A')}")
        else:
            print("No beacon data available")
    else:
        print("No wayside commands available")
    
    print("\n--- Getting control outputs (from train_states.json outputs) ---")
    control = client.get_control_outputs()
    if control:
        print(f"Power command: {control.get('power_command', 0)} W")
        print(f"Service brake: {control.get('service_brake', False)}")
        print(f"Emergency brake: {control.get('emergency_brake', False)}")
    else:
        print("No control outputs available")
    
    print("\n--- Updating physics (to train_data.json) ---")
    success = client.update_physics(velocity=45.0, position=1000.0, acceleration=2.5, temperature=72.0)
    print(f"Physics update: {'SUCCESS' if success else 'FAILED'}")
    
    print("\n--- Updating beacon data (to train_states.json inputs) ---")
    success = client.update_beacon_data(current_station="Station A", next_stop="Station B", station_side="Right")
    print(f"Beacon update: {'SUCCESS' if success else 'FAILED'}")

