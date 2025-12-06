"""CTC API Client
Communicates with the central REST API server for CTC operations.

This client handles:
- Getting all dispatched trains
- Dispatching new trains
- Sending speed/authority commands to trains
- Getting track occupancy data

Author: Generated for Phase 2 of REST API Refactor
"""
import requests
import json
from typing import Dict, List, Optional

class CTCAPIClient:
    """Client API for CTC to communicate with REST server."""
    
    def __init__(self, server_url: str = "http://localhost:5000", 
                 timeout: float = 5.0, max_retries: int = 3):
        """Initialize CTC API client.
        
        Args:
            server_url: URL of the REST API server (default: "http://localhost:5000")
            timeout: Request timeout in seconds (default: 5.0)
            max_retries: Maximum number of retries for failed requests (default: 3)
        """
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Endpoints
        self.trains_endpoint = f"{self.server_url}/api/ctc/trains"
        self.dispatch_endpoint = f"{self.server_url}/api/ctc/dispatch"
        self.occupancy_endpoint = f"{self.server_url}/api/ctc/occupancy"
        
        # Cache for when server is unreachable
        self._cached_trains = None
        self._cached_occupancy = None
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test connection to server."""
        try:
            health = requests.get(f"{self.server_url}/api/health", timeout=self.timeout)
            if health.status_code == 200:
                print(f"[CTC API] ✓ Connected to server: {self.server_url}")
            else:
                print(f"[CTC API] ⚠ Server responded with status {health.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[CTC API] ✗ ERROR: Cannot reach server at {self.server_url}")
            print(f"[CTC API] ✗ Error: {e}")
            print(f"[CTC API] ⚠ Will use cached data when available")
    
    def get_trains(self) -> Optional[Dict]:
        """Get all dispatched trains from server.
        
        Returns a dictionary with all train data including:
        - Train IDs
        - Current positions
        - Commanded speeds
        - Authorities
        - Current stations
        
        Returns:
            dict: All train data, or None if server unreachable
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.get(self.trains_endpoint, timeout=self.timeout)
                if response.status_code == 200:
                    trains = response.json()
                    self._cached_trains = trains  # Update cache
                    return trains
                else:
                    if attempt == self.max_retries - 1:
                        print(f"[CTC API] Get trains failed with status {response.status_code}")
                        
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[CTC API] Get trains timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[CTC API] Get trains failed: {e}")
        
        # All retries failed - use cached data
        if self._cached_trains is not None:
            print(f"[CTC API] Using cached train data")
            return self._cached_trains
        return None
    
    def dispatch_train(self, line: str, station: str, arrival_time: str = "") -> Optional[str]:
        """Dispatch new train from CTC.
        
        Args:
            line: Track line (e.g., "Green", "Red")
            station: Starting station name
            arrival_time: Optional scheduled arrival time
            
        Returns:
            str: New train name if successful, None otherwise
        """
        dispatch_data = {
            'line': line,
            'station': station,
            'arrival_time': arrival_time
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.dispatch_endpoint, json=dispatch_data, timeout=self.timeout)
                if response.status_code == 200:
                    result = response.json()
                    # Server returns "train" (train name), not "train_id"
                    train_name = result.get('train')
                    if train_name:
                        print(f"[CTC API] ✓ Train '{train_name}' dispatched successfully")
                        return train_name
                    else:
                        if attempt == self.max_retries - 1:
                            print(f"[CTC API] Dispatch failed: server returned 200 but missing 'train' field in response")
                else:
                    if attempt == self.max_retries - 1:
                        print(f"[CTC API] Dispatch failed with status {response.status_code}")
                        
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[CTC API] Dispatch timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[CTC API] Dispatch failed: {e}")
        
        return None
    
    def send_command(self, train_name: str, speed: float, authority: float, active: int = 1) -> bool:
        """Send speed/authority command to wayside via ctc_track_controller.json.
        
        CORRECT BOUNDARY: CTC → ctc_track_controller.json → Wayside → Train
        
        Args:
            train_name: Name of the train (e.g., "Train 1", "Train 2")
            speed: Commanded speed (mph)
            authority: Commanded authority (blocks or feet)
            active: Train active status (1 = active, 0 = inactive)
            
        Returns:
            bool: True if successful, False otherwise
        """
        command_endpoint = f"{self.server_url}/api/ctc/commands"
        command_data = {
            'train': train_name,
            'speed': speed,
            'authority': authority,
            'active': active
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(command_endpoint, json=command_data, timeout=self.timeout)
                if response.status_code == 200:
                    return True
                else:
                    if attempt == self.max_retries - 1:
                        print(f"[CTC API] Command to {train_name} failed with status {response.status_code}")
                        
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[CTC API] Command to {train_name} timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[CTC API] Command to {train_name} failed: {e}")
        
        return False
    
    def get_occupancy(self) -> Optional[List[int]]:
        """Get track occupancy array from wayside.
        
        Returns an array where each index represents a block number,
        and the value is the train ID occupying that block (0 if empty).
        
        Returns:
            list: Track occupancy array, or None if server unreachable
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.get(self.occupancy_endpoint, timeout=self.timeout)
                if response.status_code == 200:
                    occupancy_data = response.json()
                    occupancy = occupancy_data.get('occupancy', [])
                    self._cached_occupancy = occupancy  # Update cache
                    return occupancy
                else:
                    if attempt == self.max_retries - 1:
                        print(f"[CTC API] Get occupancy failed with status {response.status_code}")
                        
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[CTC API] Get occupancy timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[CTC API] Get occupancy failed: {e}")
        
        # All retries failed - use cached data
        if self._cached_occupancy is not None:
            print(f"[CTC API] Using cached occupancy data")
            return self._cached_occupancy
        return None
    
    def get_status(self) -> Optional[Dict]:
        """Get train status from wayside via ctc_track_controller.json.
        
        CORRECT BOUNDARY: Wayside → ctc_track_controller.json → CTC
        
        Returns CTC status including train positions, states reported by wayside.
        
        Returns:
            dict: CTC status data, or None if server unreachable
        """
        status_endpoint = f"{self.server_url}/api/ctc/status"
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(status_endpoint, timeout=self.timeout)
                if response.status_code == 200:
                    status = response.json()
                    return status
                else:
                    if attempt == self.max_retries - 1:
                        print(f"[CTC API] Get status failed with status {response.status_code}")
                        
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"[CTC API] Get status timed out after {self.timeout}s")
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[CTC API] Get status failed: {e}")
        
        return None


if __name__ == "__main__":
    # Test the client
    import sys
    
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    else:
        server_url = "http://localhost:5000"
    
    print(f"Testing CTC API Client with server: {server_url}")
    
    client = CTCAPIClient(server_url=server_url)
    
    print("\n--- Getting all trains ---")
    trains = client.get_trains()
    if trains:
        # CTC endpoint returns train names (e.g., "Train 1") not "train_1" format
        print(f"Found {len(trains)} trains")
        for train_name in trains.keys():
            print(f"  {train_name}")
    
    print("\n--- Dispatching a train ---")
    train_name = client.dispatch_train(line="Green", station="YARD", arrival_time="08:00:00")
    if train_name:
        print(f"Dispatched train: {train_name}")
    else:
        print("Dispatch failed")
    
    print("\n--- Sending command via CTC → wayside boundary ---")
    # CORRECT: CTC sends to ctc_track_controller.json, wayside reads it
    print("Sending command to Train 1 via ctc_track_controller.json...")
    success = client.send_command(train_name="Train 1", speed=30.0, authority=100.0, active=1)
    print(f"Command: {'SUCCESS' if success else 'FAILED'}")
    
    print("\n--- Getting status from wayside ---")
    status = client.get_status()
    if status and "Trains" in status:
        print(f"Status received: {len(status['Trains'])} trains tracked")
        for train_name, train_data in list(status['Trains'].items())[:3]:
            print(f"  {train_name}: Pos={train_data.get('Train Position', 0)}, Active={train_data.get('Active', 0)}")
    else:
        print("No status data available")
    
    print("\n--- Getting track occupancy ---")
    occupancy = client.get_occupancy()
    if occupancy:
        occupied_blocks = [i for i, train in enumerate(occupancy) if train != 0]
        print(f"Occupied blocks: {occupied_blocks[:10]}...")  # Show first 10

