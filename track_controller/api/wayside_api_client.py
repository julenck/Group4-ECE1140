"""Wayside Controller API Client

This client allows Track Controllers (Wayside) to communicate with the central
REST API server instead of using direct file I/O.

Usage:
    # Local mode (direct file access - for testing)
    api = WaysideAPIClient()
    
    # Remote mode (REST API - for Raspberry Pi)
    api = WaysideAPIClient(server_url="http://192.168.1.100:5000", wayside_id=1)

Author: Based on train_controller_api_client.py
"""

import requests
import json
import os
from typing import Dict, Optional

class WaysideAPIClient:
    """Client for Wayside Controller to communicate with REST API server."""
    
    def __init__(self, server_url: Optional[str] = None, wayside_id: int = 1):
        """Initialize API client.
        
        Args:
            server_url: URL of REST API server (e.g., "http://192.168.1.100:5000")
                       If None, uses local file mode
            wayside_id: ID of this wayside controller (1 or 2)
        """
        self.server_url = server_url
        self.wayside_id = wayside_id
        self.is_remote = server_url is not None
        
        # File paths for local mode
        if not self.is_remote:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.ctc_track_file = os.path.join(base_dir, "ctc_track_controller.json")
            self.track_to_wayside_file = os.path.join(base_dir, "track_controller", "New_SW_Code", "track_to_wayside.json")
            self.wayside_to_train_file = os.path.join(base_dir, "track_controller", "New_SW_Code", "wayside_to_train.json")
        
        print(f"[Wayside API Client] Mode: {'Remote' if self.is_remote else 'Local'}")
        if self.is_remote:
            print(f"[Wayside API Client] Server: {self.server_url}")
            print(f"[Wayside API Client] Wayside ID: {self.wayside_id}")
    
    def _read_local_json(self, filepath: str) -> Dict:
        """Read JSON file in local mode."""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[Wayside API Client] Error reading {filepath}: {e}")
        return {}
    
    def _write_local_json(self, filepath: str, data: Dict) -> bool:
        """Write JSON file in local mode."""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"[Wayside API Client] Error writing {filepath}: {e}")
            return False
    
    def get_ctc_commands(self) -> Dict:
        """Get commands from CTC.
        
        Returns:
            Dictionary with CTC commands for trains (authority, speed, etc.)
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
                    print(f"[Wayside API Client] Error getting CTC commands: {response.status_code}")
                    return {}
            except Exception as e:
                print(f"[Wayside API Client] Error connecting to server: {e}")
                return {}
        else:
            # Local mode: read from file
            return self._read_local_json(self.ctc_track_file)
    
    def get_track_data(self) -> Dict:
        """Get track model data (occupancy, failures, etc.).
        
        Returns:
            Dictionary with track block states
        """
        if self.is_remote:
            try:
                response = requests.get(
                    f"{self.server_url}/api/track_model/state",
                    timeout=5
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"[Wayside API Client] Error getting track data: {response.status_code}")
                    return {}
            except Exception as e:
                print(f"[Wayside API Client] Error connecting to server: {e}")
                return {}
        else:
            # Local mode: read from file
            return self._read_local_json(self.track_to_wayside_file)
    
    def get_wayside_state(self) -> Dict:
        """Get complete wayside state (CTC + Track data combined).
        
        Returns:
            Dictionary with combined state from CTC and Track Model
        """
        if self.is_remote:
            try:
                response = requests.get(
                    f"{self.server_url}/api/wayside/{self.wayside_id}/state",
                    timeout=5
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"[Wayside API Client] Error getting wayside state: {response.status_code}")
                    return {}
            except Exception as e:
                print(f"[Wayside API Client] Error connecting to server: {e}")
                return {}
        else:
            # Local mode: combine CTC and track data
            return {
                "ctc_commands": self.get_ctc_commands(),
                "track_data": self.get_track_data()
            }
    
    def send_train_commands(self, commands: Dict) -> bool:
        """Send commands to trains (authority, speed limits, etc.).
        
        Args:
            commands: Dictionary with train commands
            
        Returns:
            True if successful, False otherwise
        """
        if self.is_remote:
            try:
                response = requests.post(
                    f"{self.server_url}/api/wayside/train_commands",
                    json=commands,
                    timeout=5
                )
                if response.status_code == 200:
                    return True
                else:
                    print(f"[Wayside API Client] Error sending train commands: {response.status_code}")
                    return False
            except Exception as e:
                print(f"[Wayside API Client] Error connecting to server: {e}")
                return False
        else:
            # Local mode: write to file
            return self._write_local_json(self.wayside_to_train_file, commands)
    
    def update_train_command(self, train_id: int, authority: float = None, speed: float = None) -> bool:
        """Update command for a specific train.
        
        Args:
            train_id: Train ID
            authority: Authority in meters (optional)
            speed: Speed limit in m/s (optional)
            
        Returns:
            True if successful
        """
        # Get current commands
        if self.is_remote:
            try:
                response = requests.get(f"{self.server_url}/api/wayside/train_commands", timeout=5)
                current_commands = response.json() if response.status_code == 200 else {}
            except:
                current_commands = {}
        else:
            current_commands = self._read_local_json(self.wayside_to_train_file)
        
        # Ensure structure exists
        if str(train_id) not in current_commands:
            current_commands[str(train_id)] = {}
        
        # Update fields
        if authority is not None:
            current_commands[str(train_id)]["authority"] = authority
        if speed is not None:
            current_commands[str(train_id)]["speed_limit"] = speed
        
        # Send updated commands
        return self.send_train_commands(current_commands)
    
    def health_check(self) -> bool:
        """Check if server is reachable (remote mode only).
        
        Returns:
            True if server is reachable, False otherwise
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
    
    parser = argparse.ArgumentParser(description="Test Wayside API Client")
    parser.add_argument("--server", type=str, help="Server URL (e.g., http://192.168.1.100:5000)")
    parser.add_argument("--wayside-id", type=int, default=1, help="Wayside controller ID")
    args = parser.parse_args()
    
    # Create client
    client = WaysideAPIClient(server_url=args.server, wayside_id=args.wayside_id)
    
    # Test connection
    if client.is_remote:
        if client.health_check():
            print("✓ Server connection successful")
        else:
            print("✗ Cannot connect to server")
            exit(1)
    
    # Test getting CTC commands
    print("\n=== CTC Commands ===")
    ctc_commands = client.get_ctc_commands()
    print(json.dumps(ctc_commands, indent=2))
    
    # Test getting track data
    print("\n=== Track Data ===")
    track_data = client.get_track_data()
    print(json.dumps(track_data, indent=2)[:200] + "...")
    
    # Test sending train command
    print("\n=== Sending Train Command ===")
    success = client.update_train_command(train_id=1, authority=1000.0, speed=15.0)
    print(f"Command sent: {'✓' if success else '✗'}")

