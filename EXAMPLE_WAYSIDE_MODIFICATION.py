"""
EXAMPLE: How to Modify sw_wayside_controller.py to Use API Client

This file shows the specific changes needed to integrate the API client.
Copy these patterns into your actual sw_wayside_controller.py file.
"""

# ═══════════════════════════════════════════════════════════════════════
# STEP 1: Add imports at the top of the file
# ═══════════════════════════════════════════════════════════════════════

# OLD IMPORTS (keep these):
import json
import os
import time
from track_controller.New_SW_Code.Green_Line_PLC_XandLup import process_states_green_xlup
from track_controller.New_SW_Code.Green_Line_PLC_XandLdown import process_states_green_xldown
import threading
import csv

# NEW IMPORTS (add these):
import sys
# Add parent directory to path for API client import
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from track_controller.api.wayside_api_client import WaysideAPIClient


# ═══════════════════════════════════════════════════════════════════════
# STEP 2: Modify __init__ method
# ═══════════════════════════════════════════════════════════════════════

class sw_wayside_controller:
    def __init__(self, vital, plc="", server_url=None, wayside_id=1):
        """
        Initialize wayside controller.
        
        Args:
            vital: Vital check object
            plc: PLC program file path
            server_url: Optional URL of REST API server (e.g., "http://192.168.1.100:5000")
                       If None, uses local file mode
            wayside_id: ID of this wayside controller (1 or 2)
        """
        # Association
        self.vital = vital
        
        # NEW: Initialize API client instead of direct file access
        self.api_client = WaysideAPIClient(server_url=server_url, wayside_id=wayside_id)
        self.is_remote = (server_url is not None)
        
        # Attributes (existing code continues...)
        self.light_result: bool = False
        self.switch_result: bool = False
        # ... rest of your attributes ...
        
        # OLD FILE PATHS (can remove these if using API client):
        # self.ctc_comm_file: str = "ctc_track_controller.json"
        # self.track_comm_file: str = "track_controller\\New_SW_Code\\track_to_wayside.json"
        # self.train_comm_file: str = "track_controller\\New_SW_Code\\wayside_to_train.json"
        
        # ... rest of your init code ...


# ═══════════════════════════════════════════════════════════════════════
# STEP 3: Replace file READ operations with API client calls
# ═══════════════════════════════════════════════════════════════════════

def read_ctc_commands(self):
    """Read commands from CTC."""
    
    # OLD CODE (direct file access):
    """
    try:
        with self.file_lock:
            if os.path.exists(self.ctc_comm_file):
                with open(self.ctc_comm_file, 'r') as f:
                    ctc_data = json.load(f)
                    return ctc_data
    except Exception as e:
        print(f"Error reading CTC file: {e}")
    return {}
    """
    
    # NEW CODE (API client):
    try:
        ctc_data = self.api_client.get_ctc_commands()
        return ctc_data if ctc_data else {}
    except Exception as e:
        print(f"Error getting CTC commands: {e}")
        return {}


def read_track_data(self):
    """Read track model data (occupancy, failures, etc.)."""
    
    # OLD CODE:
    """
    try:
        with self.file_lock:
            if os.path.exists(self.track_comm_file):
                with open(self.track_comm_file, 'r') as f:
                    track_data = json.load(f)
                    return track_data
    except Exception as e:
        print(f"Error reading track file: {e}")
    return {}
    """
    
    # NEW CODE:
    try:
        track_data = self.api_client.get_track_data()
        return track_data if track_data else {}
    except Exception as e:
        print(f"Error getting track data: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════════════
# STEP 4: Replace file WRITE operations with API client calls
# ═══════════════════════════════════════════════════════════════════════

def send_train_commands(self, commands):
    """Send commands to trains (authority, speed, etc.)."""
    
    # OLD CODE:
    """
    try:
        with self.file_lock:
            with open(self.train_comm_file, 'w') as f:
                json.dump(commands, f, indent=4)
            return True
    except Exception as e:
        print(f"Error writing train commands: {e}")
        return False
    """
    
    # NEW CODE:
    try:
        success = self.api_client.send_train_commands(commands)
        return success
    except Exception as e:
        print(f"Error sending train commands: {e}")
        return False


def update_single_train_command(self, train_id, authority=None, speed=None):
    """Update command for a specific train."""
    
    # OLD CODE (read entire file, modify, write back):
    """
    try:
        with self.file_lock:
            # Read current commands
            commands = {}
            if os.path.exists(self.train_comm_file):
                with open(self.train_comm_file, 'r') as f:
                    commands = json.load(f)
            
            # Update train
            if str(train_id) not in commands:
                commands[str(train_id)] = {}
            
            if authority is not None:
                commands[str(train_id)]["authority"] = authority
            if speed is not None:
                commands[str(train_id)]["speed_limit"] = speed
            
            # Write back
            with open(self.train_comm_file, 'w') as f:
                json.dump(commands, f, indent=4)
            return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    """
    
    # NEW CODE (much simpler!):
    try:
        return self.api_client.update_train_command(train_id, authority, speed)
    except Exception as e:
        print(f"Error updating train command: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════
# STEP 5: Find and replace ALL file I/O patterns
# ═══════════════════════════════════════════════════════════════════════

# Search your code for these patterns and replace:

# PATTERN 1: Reading CTC commands
# OLD: json.load(open(self.ctc_comm_file))
# NEW: self.api_client.get_ctc_commands()

# PATTERN 2: Reading track data  
# OLD: json.load(open(self.track_comm_file))
# NEW: self.api_client.get_track_data()

# PATTERN 3: Writing train commands
# OLD: json.dump(data, open(self.train_comm_file, 'w'))
# NEW: self.api_client.send_train_commands(data)

# PATTERN 4: File existence checks (no longer needed!)
# OLD: if os.path.exists(self.ctc_comm_file):
# NEW: Just call the API - it returns {} if no data


# ═══════════════════════════════════════════════════════════════════════
# STEP 6: Example of a complete method using API client
# ═══════════════════════════════════════════════════════════════════════

def run_plc(self):
    """Main PLC processing loop - COMPLETE EXAMPLE"""
    
    def plc_thread():
        while self.running:
            try:
                # 1. Get CTC commands via API
                ctc_data = self.api_client.get_ctc_commands()
                trains = ctc_data.get("Trains", {})
                
                # 2. Get track data via API
                track_data = self.api_client.get_track_data()
                
                # 3. Process PLC logic (your existing code)
                if self.active_plc == "Green_Line_PLC_XandLup.py":
                    output = process_states_green_xlup(
                        trains, 
                        track_data,
                        self.switch_states,
                        self.light_states
                    )
                elif self.active_plc == "Green_Line_PLC_XandLdown.py":
                    output = process_states_green_xldown(
                        trains,
                        track_data, 
                        self.switch_states,
                        self.light_states
                    )
                
                # 4. Send commands to trains via API
                if output:
                    self.api_client.send_train_commands(output)
                
                # 5. Update internal state
                self.light_states = output.get("lights", self.light_states)
                self.switch_states = output.get("switches", self.switch_states)
                
            except Exception as e:
                print(f"[PLC] Error in processing loop: {e}")
            
            time.sleep(0.1)  # 100ms update rate
    
    # Start thread
    thread = threading.Thread(target=plc_thread, daemon=True)
    thread.start()


# ═══════════════════════════════════════════════════════════════════════
# STEP 7: Benefits of this approach
# ═══════════════════════════════════════════════════════════════════════

"""
✅ BENEFITS:

1. Works in LOCAL mode (no server):
   controller = sw_wayside_controller(vital, plc)
   Uses direct file I/O for testing

2. Works in REMOTE mode (with server):
   controller = sw_wayside_controller(vital, plc, server_url="http://192.168.1.100:5000")
   Uses REST API for Raspberry Pi deployment

3. Same code for both modes:
   No #ifdef or duplicate code
   API client handles the difference

4. Easier to debug:
   Server logs show all requests
   Can test with curl commands

5. More reliable:
   Thread-safe file access
   No race conditions
   Single source of truth

6. Scales easily:
   Add more Raspberry Pis by just passing different wayside_id
   No code changes needed
"""


# ═══════════════════════════════════════════════════════════════════════
# STEP 8: How to test your changes
# ═══════════════════════════════════════════════════════════════════════

"""
TESTING PROCEDURE:

1. Test LOCAL mode first (no changes to workflow):
   python sw_wayside_controller_ui.py
   Should work exactly as before

2. Start the server:
   python start_unified_server.py
   Note the IP address

3. Test REMOTE mode (new functionality):
   python sw_wayside_controller_ui.py --server http://localhost:5000
   Should work identically to local mode
   
4. Verify server logs show connections:
   [Server] Wayside state updated
   [Server] Train commands updated

5. Test on Raspberry Pi:
   python sw_wayside_controller_ui.py --server http://192.168.1.100:5000 --wayside-id 1
   Should connect to main computer's server
"""


# ═══════════════════════════════════════════════════════════════════════
# STEP 9: Common mistakes to avoid
# ═══════════════════════════════════════════════════════════════════════

"""
❌ MISTAKES TO AVOID:

1. Don't mix file I/O and API calls:
   BAD:  Sometimes use files, sometimes use API
   GOOD: Always use api_client methods
   
2. Don't forget error handling:
   BAD:  data = self.api_client.get_ctc_commands()
   GOOD: data = self.api_client.get_ctc_commands() or {}
   
3. Don't hard-code server URL:
   BAD:  server_url = "http://192.168.1.100:5000"
   GOOD: Pass via command line argument
   
4. Don't remove file_lock entirely:
   Keep it for any local variables that threads share
   
5. Don't forget to test both modes:
   Test local mode AND remote mode before deploying
"""

# ═══════════════════════════════════════════════════════════════════════
# END OF EXAMPLE
# ═══════════════════════════════════════════════════════════════════════

