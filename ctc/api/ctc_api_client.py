"""CTC API Client

This client allows CTC (Centralized Traffic Control) to communicate with the
central REST API server instead of using direct file I/O.

Usage:
    # Local mode (direct file access - for testing)
    api = CTCAPIClient()
    
    # Remote mode (REST API - for networked operation)
    api = CTCAPIClient(server_url="http://192.168.1.100:5000")

Author: Based on train_controller_api_client.py
"""

import requests
import json
import os
from typing import Dict, Optional, List

class CTCAPIClient:
    """Client for CTC to communicate with REST API server."""
    
    def __init__(self, server_url: Optional[str] = None):
        """Initialize API client.
        
        Args:
            server_url: URL of REST API server (e.g., "http://192.168.1.100:5000")
                       If None, uses local file mode
        """
        self.server_url = server_url
        self.is_remote = server_url is not None
        
        # File paths for local mode
        if not self.is_remote:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.ctc_data_file = os.path.join(base_dir, "ctc_data.json")
            self.ctc_track_controller_file = os.path.join(base_dir, "ctc_track_controller.json")
        
        print(f"[CTC API Client] Mode: {'Remote' if self.is_remote else 'Local'}")
        if self.is_remote:
            print(f"[CTC API Client] Server: {self.server_url}")
    
    def _read_local_json(self, filepath: str) -> Dict:
        """Read JSON file in local mode."""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[CTC API Client] Error reading {filepath}: {e}")
        return {}
    
    def _write_local_json(self, filepath: str, data: Dict) -> bool:
        """Write JSON file in local mode."""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"[CTC API Client] Error writing {filepath}: {e}")
            return False
    
    def get_state(self) -> Dict:
        """Get complete CTC state.
        
        Returns:
            Dictionary with CTC state (dispatcher info, trains, etc.)
        """
        if self.is_remote:
            try:
                response = requests.get(
                    f"{self.server_url}/api/ctc/state",
                    timeout=5
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"[CTC API Client] Error getting state: {response.status_code}")
                    return {}
            except Exception as e:
                print(f"[CTC API Client] Error connecting to server: {e}")
                return {}
        else:
            # Local mode: read from file
            return self._read_local_json(self.ctc_data_file)
    
    def update_state(self, updates: Dict) -> bool:
        """Update CTC state.
        
        Args:
            updates: Dictionary with state updates
            
        Returns:
            True if successful
        """
        if self.is_remote:
            try:
                response = requests.post(
                    f"{self.server_url}/api/ctc/state",
                    json=updates,
                    timeout=5
                )
                return response.status_code == 200
            except Exception as e:
                print(f"[CTC API Client] Error connecting to server: {e}")
                return False
        else:
            # Local mode: read, merge, write
            current_data = self._read_local_json(self.ctc_data_file)
            self._merge_dicts(current_data, updates)
            return self._write_local_json(self.ctc_data_file, current_data)
    
    def get_trains(self) -> Dict:
        """Get all trains from dispatcher.
        
        Returns:
            Dictionary of trains with their states
        """
        if self.is_remote:
            try:
                response = requests.get(
                    f"{self.server_url}/api/ctc/trains",
                    timeout=5
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"[CTC API Client] Error getting trains: {response.status_code}")
                    return {}
            except Exception as e:
                print(f"[CTC API Client] Error connecting to server: {e}")
                return {}
        else:
            # Local mode
            data = self._read_local_json(self.ctc_data_file)
            return data.get("Dispatcher", {}).get("Trains", {})
    
    def get_train(self, train_name: str) -> Dict:
        """Get specific train data.
        
        Args:
            train_name: Name of train (e.g., "Train 1")
            
        Returns:
            Dictionary with train data
        """
        if self.is_remote:
            try:
                response = requests.get(
                    f"{self.server_url}/api/ctc/trains/{train_name}",
                    timeout=5
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"[CTC API Client] Error getting train: {response.status_code}")
                    return {}
            except Exception as e:
                print(f"[CTC API Client] Error connecting to server: {e}")
                return {}
        else:
            # Local mode
            trains = self.get_trains()
            return trains.get(train_name, {})
    
    def update_train(self, train_name: str, updates: Dict) -> bool:
        """Update specific train data.
        
        Args:
            train_name: Name of train (e.g., "Train 1")
            updates: Dictionary with fields to update
            
        Returns:
            True if successful
        """
        if self.is_remote:
            try:
                response = requests.post(
                    f"{self.server_url}/api/ctc/trains/{train_name}",
                    json=updates,
                    timeout=5
                )
                return response.status_code == 200
            except Exception as e:
                print(f"[CTC API Client] Error connecting to server: {e}")
                return False
        else:
            # Local mode
            data = self._read_local_json(self.ctc_data_file)
            
            # Ensure structure exists
            if "Dispatcher" not in data:
                data["Dispatcher"] = {}
            if "Trains" not in data["Dispatcher"]:
                data["Dispatcher"]["Trains"] = {}
            if train_name not in data["Dispatcher"]["Trains"]:
                data["Dispatcher"]["Trains"][train_name] = {}
            
            # Update train
            data["Dispatcher"]["Trains"][train_name].update(updates)
            
            return self._write_local_json(self.ctc_data_file, data)
    
    def dispatch_train(self, train_name: str, line: str, station: str, 
                      arrival_time: str, speed: int, authority: int) -> bool:
        """Dispatch a train with route and timing information.
        
        Args:
            train_name: Name of train (e.g., "Train 1")
            line: Line name (e.g., "Green Line")
            station: Destination station
            arrival_time: Arrival time (HH:MM format)
            speed: Suggested speed in mph
            authority: Authority in yards
            
        Returns:
            True if successful
        """
        updates = {
            "Line": line,
            "Station Destination": station,
            "Arrival Time": arrival_time,
            "Suggested Speed": speed,
            "Authority": authority,
            "State": "Dispatched"
        }
        
        # Update CTC data
        success = self.update_train(train_name, updates)
        
        # Also update track controller commands
        if success:
            self.send_track_controller_command(train_name, speed, authority, active=1)
        
        return success
    
    def get_track_controller_commands(self) -> Dict:
        """Get commands being sent to track controller.
        
        Returns:
            Dictionary with track controller commands
        """
        if self.is_remote:
            try:
                response = requests.get(
                    f"{self.server_url}/api/ctc/track_controller",
                    timeout=5
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"[CTC API Client] Error getting track controller commands: {response.status_code}")
                    return {}
            except Exception as e:
                print(f"[CTC API Client] Error connecting to server: {e}")
                return {}
        else:
            # Local mode
            return self._read_local_json(self.ctc_track_controller_file)
    
    def send_track_controller_command(self, train_name: str, speed: int, 
                                     authority: int, active: int = 1) -> bool:
        """Send command to track controller for a specific train.
        
        Args:
            train_name: Name of train (e.g., "Train 1")
            speed: Suggested speed in m/s
            authority: Authority in meters
            active: 1 if train is active, 0 otherwise
            
        Returns:
            True if successful
        """
        # Get current commands
        current_commands = self.get_track_controller_commands()
        
        # Ensure structure exists
        if "Trains" not in current_commands:
            current_commands["Trains"] = {}
        if train_name not in current_commands["Trains"]:
            current_commands["Trains"][train_name] = {}
        
        # Update train command
        current_commands["Trains"][train_name].update({
            "Active": active,
            "Suggested Speed": speed,
            "Suggested Authority": authority
        })
        
        # Send update
        if self.is_remote:
            try:
                response = requests.post(
                    f"{self.server_url}/api/ctc/track_controller",
                    json=current_commands,
                    timeout=5
                )
                return response.status_code == 200
            except Exception as e:
                print(f"[CTC API Client] Error connecting to server: {e}")
                return False
        else:
            # Local mode
            return self._write_local_json(self.ctc_track_controller_file, current_commands)
    
    def _merge_dicts(self, base: Dict, updates: Dict) -> None:
        """Recursively merge updates into base dictionary."""
        for key, value in updates.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._merge_dicts(base[key], value)
            else:
                base[key] = value
    
    def health_check(self) -> bool:
        """Check if server is reachable (remote mode only).
        
        Returns:
            True if server is reachable
        """
        if not self.is_remote:
            return True  # Local mode always "connected"
        
        try:
            response = requests.get(f"{self.server_url}/api/health", timeout=2)
            return response.status_code == 200
        except:
            return False


# Example usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test CTC API Client")
    parser.add_argument("--server", type=str, help="Server URL (e.g., http://192.168.1.100:5000)")
    args = parser.parse_args()
    
    # Create client
    client = CTCAPIClient(server_url=args.server)
    
    # Test connection
    if client.is_remote:
        if client.health_check():
            print("✓ Server connection successful")
        else:
            print("✗ Cannot connect to server")
            exit(1)
    
    # Test getting trains
    print("\n=== All Trains ===")
    trains = client.get_trains()
    print(json.dumps(trains, indent=2))
    
    # Test getting specific train
    print("\n=== Train 1 ===")
    train1 = client.get_train("Train 1")
    print(json.dumps(train1, indent=2))
    
    # Test updating train
    print("\n=== Updating Train 1 ===")
    success = client.update_train("Train 1", {
        "Line": "Green Line",
        "Suggested Speed": 25,
        "Authority": 500
    })
    print(f"Update successful: {'✓' if success else '✗'}")
    
    # Test getting track controller commands
    print("\n=== Track Controller Commands ===")
    commands = client.get_track_controller_commands()
    print(json.dumps(commands, indent=2))

