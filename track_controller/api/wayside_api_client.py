"""Wayside/Track Controller API Client
Communicates with the central REST API server for Wayside operations.

This client handles:
- Getting CTC commands (speed, authority, switch positions)
- Updating wayside state (switches, lights, gates, occupancy)
- Getting train positions in controlled blocks

Author: Generated for Phase 2 of REST API Refactor
"""
import requests
import json
from typing import Dict, List, Optional

class WaysideAPIClient:
    """Client API for Wayside Controller to communicate with REST server."""
    
    def __init__(self, wayside_id: int, server_url: str = "http://localhost:5000", 
                 timeout: float = 5.0, max_retries: int = 3):
        """Initialize Wayside API client.
        
        Args:
            wayside_id: The wayside controller ID (1, 2, etc.)
            server_url: URL of the REST API server (default: "http://localhost:5000")
            timeout: Request timeout in seconds (default: 5.0)
            max_retries: Maximum number of retries for failed requests (default: 3)
        """
        self.wayside_id = wayside_id
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Endpoints
        self.state_endpoint = f"{self.server_url}/api/wayside/state"
        self.switches_endpoint = f"{self.server_url}/api/wayside/switches"
        self.lights_endpoint = f"{self.server_url}/api/wayside/lights"
        self.ctc_commands_endpoint = f"{self.server_url}/api/wayside/ctc_commands"
        self.train_status_endpoint = f"{self.server_url}/api/wayside/train_status"
        self.train_physics_endpoint = f"{self.server_url}/api/wayside/train_physics"  # CORRECT: Read from train_data.json
        self.train_commands_endpoint = f"{self.server_url}/api/wayside/train_commands"
        
        # Cache for when server is unreachable
        self._cached_state = None
        self._cached_trains = None
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test connection to server."""
        try:
            health = requests.get(f"{self.server_url}/api/health", timeout=self.timeout)
            if health.status_code == 200:
                print(f"[Wayside API] ✓ Connected to server: {self.server_url}")
                print(f"[Wayside API] ✓ Wayside Controller {self.wayside_id}")
            else:
                print(f"[Wayside API] ⚠ Server responded with status {health.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[Wayside API] ✗ ERROR: Cannot reach server at {self.server_url}")
            print(f"[Wayside API] ✗ Error: {e}")
            print(f"[Wayside API] ⚠ Will use cached data when available")
    
    def get_ctc_commands(self) -> Optional[Dict]:
        """Get CTC commands from ctc_track_controller.json.
        
        CORRECT BOUNDARY: CTC → ctc_track_controller.json → Wayside
        
        Returns commands including:
        - Active status for trains
        - Suggested Speed commands
        - Suggested Authority commands
        - Switch position commands
        - Block closures
        
        Returns:
            dict: CTC commands from ctc_track_controller.json, or None if server unreachable
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.get(self.ctc_commands_endpoint, timeout=self.timeout)
                if response.status_code == 200:
                    commands = response.json()
                    self._cached_state = commands  # Update cache
                    return commands
                else:
                    if attempt == self.max_retries - 1:
                        print(f"[Wayside API] Get CTC commands failed with status {response.status_code}")
                        
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[Wayside API] Get CTC commands timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[Wayside API] Get CTC commands failed: {e}")
        
        # All retries failed - use cached data
        if self._cached_state is not None:
            print(f"[Wayside API] Using cached CTC command data")
            return self._cached_state
        return None
    
    def update_state(self, switches: Dict[int, int] = None, lights: Dict[int, str] = None, 
                    gates: Dict[int, bool] = None, occupancy: List[int] = None) -> bool:
        """Update wayside state on server.
        
        Args:
            switches: Dictionary of {block_number: position} (0=main, 1=divergent)
            lights: Dictionary of {block_number: color} ("red", "yellow", "green")
            gates: Dictionary of {block_number: is_closed}
            occupancy: List of block occupancy (train_id at each block, 0 if empty)
            
        Returns:
            bool: True if successful, False otherwise
        """
        state_data = {
            f'wayside_{self.wayside_id}': {
                'switches': switches or {},
                'lights': lights or {},
                'gates': gates or {},
                'occupancy': occupancy or []
            }
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.state_endpoint, json=state_data, timeout=self.timeout)
                if response.status_code == 200:
                    return True
                else:
                    if attempt == self.max_retries - 1:
                        print(f"[Wayside API] State update failed with status {response.status_code}")
                        
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[Wayside API] State update timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[Wayside API] State update failed: {e}")
        
        return False
    
    def update_switches(self, switch_positions: Dict[int, int]) -> bool:
        """Update switch positions on server.
        
        Args:
            switch_positions: Dictionary of {block_number: position}
                             position: 0 = main/straight, 1 = divergent
            
        Returns:
            bool: True if successful, False otherwise
        """
        switch_data = {
            'wayside_id': self.wayside_id,
            'switches': switch_positions
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.switches_endpoint, json=switch_data, timeout=self.timeout)
                if response.status_code == 200:
                    return True
                else:
                    if attempt == self.max_retries - 1:
                        print(f"[Wayside API] Switch update failed with status {response.status_code}")
                        
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[Wayside API] Switch update timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[Wayside API] Switch update failed: {e}")
        
        return False
    
    def update_lights(self, light_states: Dict[int, str]) -> bool:
        """Update light states on server.
        
        Args:
            light_states: Dictionary of {block_number: color}
                         color: "red", "yellow", or "green"
            
        Returns:
            bool: True if successful, False otherwise
        """
        light_data = {
            'wayside_id': self.wayside_id,
            'lights': light_states
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.lights_endpoint, json=light_data, timeout=self.timeout)
                if response.status_code == 200:
                    return True
                else:
                    if attempt == self.max_retries - 1:
                        print(f"[Wayside API] Light update failed with status {response.status_code}")
                        
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[Wayside API] Light update timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[Wayside API] Light update failed: {e}")
        
        return False
    
    def get_train_speeds(self) -> Optional[Dict[str, float]]:
        """Get train velocities from train_data.json.
        
        CORRECT BOUNDARY: Train Model → train_data.json → Wayside
        
        Wayside ONLY needs velocities from train_data.json for:
        - Safety calculations (occupancy detection based on speed)
        - Writing "Train Speed" back to wayside_to_train.json
        
        Wayside calculates train positions itself using block occupancy!
        
        Returns a dictionary of trains and their velocities:
        {
            "Train 1": velocity_mph,
            "Train 2": velocity_mph,
            ...
        }
        
        Returns:
            dict: Train velocities (matching wayside's load_train_speeds() method), or None if unreachable
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.get(self.train_physics_endpoint, timeout=self.timeout)
                if response.status_code == 200:
                    train_data = response.json()
                    self._cached_trains = train_data  # Update cache
                    
                    # Extract ONLY velocities from train_data.json (matching sw_wayside_controller.py:928-954)
                    train_speeds = {}
                    for key, data in train_data.items():
                        if key.startswith('train_'):
                            train_id = int(key.split('_')[1])
                            train_name = f"Train {train_id}"
                            outputs = data.get('outputs', {})
                            # Get velocity in mph (wayside converts to m/s internally if needed)
                            velocity_mph = outputs.get('velocity_mph', 0.0)
                            train_speeds[train_name] = velocity_mph
                    return train_speeds
                else:
                    if attempt == self.max_retries - 1:
                        print(f"[Wayside API] Get train speeds failed with status {response.status_code}")
                        
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[Wayside API] Get train speeds timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[Wayside API] Get train speeds failed: {e}")
        
        # All retries failed - use cached data
        if self._cached_trains is not None:
            print(f"[Wayside API] Using cached train speed data")
            # Process cached data
            train_speeds = {}
            for key, data in self._cached_trains.items():
                if key.startswith('train_'):
                    train_id = int(key.split('_')[1])
                    train_name = f"Train {train_id}"
                    outputs = data.get('outputs', {})
                    velocity_mph = outputs.get('velocity_mph', 0.0)
                    train_speeds[train_name] = velocity_mph
            return train_speeds
        return None
    
    def update_occupancy(self, occupancy: List[int]) -> bool:
        """Update track occupancy array.
        
        Args:
            occupancy: List where index is block number and value is train ID (0 if empty)
            
        Returns:
            bool: True if successful, False otherwise
        """
        occupancy_data = {
            f'wayside_{self.wayside_id}': {
                'occupancy': occupancy
            }
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.state_endpoint, json=occupancy_data, timeout=self.timeout)
                if response.status_code == 200:
                    return True
                elif attempt == self.max_retries - 1:
                    print(f"[Wayside API] Occupancy update failed with status {response.status_code}")
                    
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[Wayside API] Occupancy update timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[Wayside API] Occupancy update failed: {e}")
        
        return False
    
    def update_train_status(self, train_name: str, position: int, state: str = "", active: int = 1) -> bool:
        """Report train position and state back to CTC via ctc_track_controller.json.
        
        CORRECT BOUNDARY: Wayside → ctc_track_controller.json → CTC
        
        Args:
            train_name: Name of the train (e.g., "Train 1")
            position: Current block number
            state: Train state (e.g., "moving", "stopped")
            active: Active status (1 = active, 0 = stopped/inactive)
            
        Returns:
            bool: True if successful, False otherwise
        """
        status_data = {
            'train': train_name,
            'position': position,
            'state': state,
            'active': active
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.train_status_endpoint, json=status_data, timeout=self.timeout)
                if response.status_code == 200:
                    return True
                elif attempt == self.max_retries - 1:
                    print(f"[Wayside API] Train status update failed with status {response.status_code}")
                    
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[Wayside API] Train status update timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[Wayside API] Train status update failed: {e}")
        
        return False
    
    def send_train_commands(self, train_name: str, commanded_speed: float, commanded_authority: float,
                           current_station: str = "", next_station: str = "") -> bool:
        """Send commands to train via wayside_to_train.json.
        
        CORRECT BOUNDARY: Wayside → wayside_to_train.json → Train Model
        
        Args:
            train_name: Name of the train (e.g., "Train 1")
            commanded_speed: Speed command (mph)
            commanded_authority: Authority command (yds or blocks)
            current_station: Current station (from beacon/track data)
            next_station: Next station (from beacon/track data)
            
        Returns:
            bool: True if successful, False otherwise
        """
        command_data = {
            'train': train_name,
            'commanded_speed': commanded_speed,
            'commanded_authority': commanded_authority,
            'current_station': current_station,
            'next_station': next_station
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.train_commands_endpoint, json=command_data, timeout=self.timeout)
                if response.status_code == 200:
                    return True
                elif attempt == self.max_retries - 1:
                    print(f"[Wayside API] Train command failed with status {response.status_code}")
                    
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[Wayside API] Train command timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[Wayside API] Train command failed: {e}")
        
        return False


if __name__ == "__main__":
    # Test the client
    import sys
    
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    else:
        server_url = "http://localhost:5000"
    
    print(f"Testing Wayside API Client with server: {server_url}")
    
    client = WaysideAPIClient(wayside_id=1, server_url=server_url)
    
    print("\n--- Getting CTC commands (from ctc_track_controller.json) ---")
    commands = client.get_ctc_commands()
    if commands:
        print(f"Received CTC commands")
        if "Trains" in commands:
            print(f"  {len(commands['Trains'])} trains in CTC data")
        if isinstance(commands, dict):
            print(f"  Keys: {list(commands.keys())}")
    else:
        print("No CTC commands available")
    
    print("\n--- Getting train speeds (from train_data.json) ---")
    train_speeds = client.get_train_speeds()
    if train_speeds and len(train_speeds) > 0:
        print(f"Found {len(train_speeds)} trains")
        for train_name, velocity_mph in train_speeds.items():
            print(f"  {train_name}: {velocity_mph:.1f} mph")
    else:
        print("No trains found (train_data.json may be empty)")
    
    print("\n--- Sending train commands (to wayside_to_train.json) ---")
    success = client.send_train_commands("Train 1", commanded_speed=30.0, commanded_authority=100.0,
                                         current_station="Station A", next_station="Station B")
    print(f"Train command: {'SUCCESS' if success else 'FAILED'}")
    print("  Includes: Speed, Authority, Current Station, Next Station")
    
    print("\n--- Reporting train status (to ctc_track_controller.json) ---")
    success = client.update_train_status("Train 1", position=25, state="moving", active=1)
    print(f"Status report: {'SUCCESS' if success else 'FAILED'}")
    
    print("\n--- Updating switch positions ---")
    success = client.update_switches({5: 0, 10: 1})  # Block 5 main, Block 10 divergent
    print(f"Switch update: {'SUCCESS' if success else 'FAILED'}")
    
    print("\n--- Updating light states ---")
    success = client.update_lights({5: "green", 10: "red", 15: "yellow"})
    print(f"Light update: {'SUCCESS' if success else 'FAILED'}")

