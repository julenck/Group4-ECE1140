

import json
import os
import time
#from .Green_Line_PLC_XandLup import process_states_green_xlup
#from .Green_Line_PLC_XandLdown import process_states_green_xldown
from track_controller.New_SW_Code.Green_Line_PLC_XandLup import process_states_green_xlup
from track_controller.New_SW_Code.Green_Line_PLC_XandLdown import process_states_green_xldown
import threading
import csv


class sw_wayside_controller:
    def __init__(self, vital, plc="", server_url=None, wayside_id=1):
    # Association
        self.vital = vital

    # Attributes
        self.light_result: bool = False
        self.switch_result: bool = False
        self.gate_result: bool = False
        self.plc_result: bool = False
        self.auth_result: bool = False
        self.speed_result: bool = False
        self.close_result: bool = False
        self.status_result: bool = False
        self.active_trains: dict = {}
        self.occupied_blocks: list = [0]*152
        self.light_states: list = [0]*24
        self.gate_states: list = [0,0]
        self.switch_states: list = [0]*6
        self.ctc_sugg_switches: list = [0]*6
        self.output_data: dict = {}
        # Extract just the filename from the plc path (in case full path is provided)
        self.active_plc: str = os.path.basename(plc) if '\\' in plc or '/' in plc else plc
        
        # Use absolute paths based on the project root
        # Get the directory where this file is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))  # Go up two levels to project root
        
        self.ctc_comm_file: str = os.path.join(project_root, "ctc_track_controller.json")
        self.track_comm_file: str = os.path.join(project_root, "track_controller", "New_SW_Code", "track_to_wayside.json")
        self.train_comm_file: str = os.path.join(project_root, "track_controller", "New_SW_Code", "wayside_to_train.json")
        
        self.block_status: list = []
        self.detected_faults: dict = {}
        
        # Phase 3: Initialize Wayside API client for REST API communication
        self.wayside_api = None
        self.wayside_id = wayside_id
        if server_url:
            try:
                import sys
                api_dir = os.path.join(project_root, "track_controller", "api")
                if api_dir not in sys.path:
                    sys.path.insert(0, api_dir)
                from wayside_api_client import WaysideAPIClient
                self.wayside_api = WaysideAPIClient(wayside_id=wayside_id, server_url=server_url)
                print(f"[Wayside {wayside_id}] Using REST API: {server_url}")
            except Exception as e:
                print(f"[Wayside {wayside_id}] Warning: Failed to initialize API client: {e}")
                print(f"[Wayside {wayside_id}] Falling back to file-based I/O")
                self.wayside_api = None
        else:
            print(f"[Wayside {wayside_id}] Using file-based I/O (no server_url)")
        self.input_faults: list = [0]*152*3
        self.blocks_with_switches: list = [13,28,57,63,77,85]
        self.blocks_with_lights: list = [0,3,7,29,58,62,76,86,100,101,150,151]
        self.blocks_with_gates: list = [19,108]
        self.running: bool = True
        self.file_lock = threading.Lock()
        self.cmd_trains: dict = {}
        # Per-train tracking dictionaries
        self.train_idx: dict = {}  # Track index for each train
        self.train_pos_start: dict = {}  # Starting position for each train
        self.train_auth_start: dict = {}  # Starting authority for each train
        self.train_direction: dict = {}  # Track direction for each train ('forward' or 'reverse')
        self.last_seen_position: dict = {}  # Track last known position to detect newly dispatched trains
        self.cumulative_distance: dict = {}  # Track actual distance traveled since last reset
        self.last_ctc_authority: dict = {}  # Track last authority value from CTC to detect new dispatches
        
        # Define block ranges for each PLC
        # managed_blocks: blocks this controller controls (for handoff decisions)
        # visible_blocks: blocks this controller can see/display (extends beyond handoff boundary)
        if self.active_plc == "Green_Line_PLC_XandLup.py":
            self.managed_blocks = set(range(0, 70)) | set(range(144, 151))  # Blocks 0-69 and 144-150 (control boundaries)
            self.visible_blocks = set(range(0, 74)) | set(range(144, 151))  # Can see 0-73 and 144-150
        elif self.active_plc == "Green_Line_PLC_XandLdown.py":
            self.managed_blocks = set(range(70, 144))  # Blocks 70-143 (control boundaries)
            self.visible_blocks = set(range(70, 144))  # Can see 66-143 (includes approach blocks for handoff detection)
        else:
            self.managed_blocks = set(range(0, 152))  # All blocks if no specific PLC
            self.visible_blocks = set(range(0, 152))

        # Load track data from Excel file
        self.block_graph = {}  # Maps block number to {length, forward_next, reverse_next, bidirectional, beacon data}
        self.block_distances = {}  # Maps block number to cumulative distance
        self.block_lengths = {}  # Maps block number to individual block length
        self.block_speed_limits = {}  # Maps block number to speed limit in m/s
        self.station_blocks = set()  # Set of blocks that have stations (valid start points)
        self._load_track_data()

        # Keep green_order for backward compatibility (default forward path)
        self.green_order = self._build_green_order()
        
        # Define direction transition points: (from_block, to_block, new_direction)
        self.direction_transitions = [
            (100, 85, 'reverse'),  # Going from 100 to 85 switches to reverse
            (77, 101, 'forward'),  # Going from 77 to 101 switches back to forward
            (1, 13, 'reverse'),    # Going from 1 to 13 switches to reverse
            (28, 29, 'forward')    # Exiting section F/28 switches back to forward
        ]

        # Initialize/clean wayside_to_train.json on startup
        self.initialize_train_comm_file()

        # Start PLC processing loop
        self.run_plc()
        self.run_trains()

    # Methods
    def _load_track_data(self):
        """Load track data from CSV file: section, block_num, bidirectional, length, forward_next, reverse_next"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            csv_path = os.path.join(current_dir, 'track_data.csv')
            
            cumulative_distance = 0
            row_count = 0
            
            with open(csv_path, 'r') as csvfile:
                reader = csv.reader(csvfile)
                
                for row in reader:
                    row_count += 1
                    
                    if len(row) < 6:
                        continue
                    
                    section = row[0]
                    block_num = row[1]
                    length = row[2]
                    bidirectional = row[3]
                    forward_next = row[4]
                    reverse_next = row[5]
                    has_station = row[6] if len(row) > 6 else '0'  # 7th column for station indicator
                    speed_limit_ms = row[8] if len(row) > 8 else '0'  # 9th column (index 8) for speed limit in m/s
                    
                    # Beacon data for forward direction (columns 10, 11, 12 -> indices 9, 10, 11)
                    forward_has_beacon = row[9] if len(row) > 9 else '0'
                    forward_current_station = row[10] if len(row) > 10 else ''
                    forward_next_station = row[11] if len(row) > 11 else ''
                    
                    # Beacon data for reverse direction (columns 13, 14, 15 -> indices 12, 13, 14)
                    reverse_has_beacon = row[12] if len(row) > 12 else '0'
                    reverse_current_station = row[13] if len(row) > 13 else ''
                    reverse_next_station = row[14] if len(row) > 14 else ''
                    
                    if block_num and block_num.strip():
                        try:
                            block_num = int(block_num)
                            length = float(length) if length else 0
                            cumulative_distance += length
                            
                            # Check if this block has a station
                            if has_station.strip() == '1':
                                self.station_blocks.add(block_num)
                            
                            # Parse speed limit (default to 0 if not provided)
                            try:
                                speed_limit = float(speed_limit_ms) if speed_limit_ms and speed_limit_ms.strip() else 0
                            except ValueError:
                                speed_limit = 0
                            self.block_speed_limits[block_num] = speed_limit
                            
                            # Convert next blocks to int or -1 if empty/none
                            if forward_next and forward_next.strip().lower() not in ['', 'none', '-1']:
                                forward_next = int(forward_next)
                            else:
                                forward_next = -1
                                
                            if reverse_next and reverse_next.strip().lower() not in ['', 'none', '-1']:
                                reverse_next = int(reverse_next)
                            else:
                                reverse_next = -1
                            
                            self.block_graph[block_num] = {
                                'length': length,
                                'forward_next': forward_next,
                                'reverse_next': reverse_next,
                                'bidirectional': bidirectional,
                                'cumulative_distance': cumulative_distance,
                                'forward_beacon': {
                                    'has_beacon': forward_has_beacon.strip() == '1',
                                    'current_station': forward_current_station.strip(),
                                    'next_station': forward_next_station.strip()
                                },
                                'reverse_beacon': {
                                    'has_beacon': reverse_has_beacon.strip() == '1',
                                    'current_station': reverse_current_station.strip(),
                                    'next_station': reverse_next_station.strip()
                                }
                            }
                            self.block_distances[block_num] = cumulative_distance
                            self.block_lengths[block_num] = length
                        except ValueError as ve:
                            continue
            
        except Exception as e:
            print(f"Error loading track data from CSV: {e}")
            print("Using hardcoded fallback values")
            self._load_fallback_data()
    
    def _load_fallback_data(self):
        """Fallback to hardcoded values if Excel loading fails"""
        # Simplified fallback - just enough to not crash
        hardcoded_order = [0,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,
                       85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,85,84,83,82,81,80,79,
                       78,77,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,
                       116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,
                       133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,
                       150,28,27,26,25,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10,9,8,
                       7,6,5,4,3,2,1,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,
                       29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,
                       50,51,52,53,54,55,56,57,151]
        
        for i, block in enumerate(hardcoded_order):
            next_block = hardcoded_order[i + 1] if i + 1 < len(hardcoded_order) else -1
            self.block_graph[block] = {
                'length': 100,
                'forward_next': next_block,
                'reverse_next': -1,
                'bidirectional': False,
                'cumulative_distance': (i + 1) * 100
            }
            self.block_distances[block] = (i + 1) * 100
    
    def _build_green_order(self):
        """Build the default forward path starting from block 0"""
        if not self.block_graph:
            return []
        
        order = []
        current = 0
        visited = set()
        
        while current != -1 and current not in visited:
            order.append(current)
            visited.add(current)
            if current in self.block_graph:
                current = self.block_graph[current]['forward_next']
            else:
                break
        
        return order

    def initialize_train_comm_file(self):
        """Initialize wayside_to_train.json with clean state on startup"""
        try:
            clean_data = {
                "Train 1": {"Commanded Speed": 0, "Commanded Authority": 0, "Beacon": {"Current Station": "", "Next Station": ""}, "Train Speed": 0},
                "Train 2": {"Commanded Speed": 0, "Commanded Authority": 0, "Beacon": {"Current Station": "", "Next Station": ""}, "Train Speed": 0},
                "Train 3": {"Commanded Speed": 0, "Commanded Authority": 0, "Beacon": {"Current Station": "", "Next Station": ""}, "Train Speed": 0},
                "Train 4": {"Commanded Speed": 0, "Commanded Authority": 0, "Beacon": {"Current Station": "", "Next Station": ""}, "Train Speed": 0},
                "Train 5": {"Commanded Speed": 0, "Commanded Authority": 0, "Beacon": {"Current Station": "", "Next Station": ""}, "Train Speed": 0}
            }
            with open(self.train_comm_file, 'w') as f:
                json.dump(clean_data, f, indent=4)
            print(f"[{self.active_plc}] Initialized wayside_to_train.json")
        except Exception as e:
            print(f"[{self.active_plc}] Warning: Could not initialize wayside_to_train.json: {e}")

    def stop(self):
        # Stop PLC processing loop
        self.running = False

    def run_plc(self):
        if not self.running:
            self.active_plc = ""
            return
        #call plc function
        if self.active_plc != "":
            #self.load_inputs_track()
            
            if self.active_plc == "Green_Line_PLC_XandLup.py":
                occ1 = self.occupied_blocks[0:73]
                occ2 = self.occupied_blocks[144:151]
                occ =occ1+occ2
                switches, signals, crossing = process_states_green_xlup(occ)
                self.switch_states[0]=switches[0]
                self.switch_states[1]=switches[1]
                self.switch_states[2]=switches[2]
                self.switch_states[3]=switches[3]
                self.light_states[0]=signals[0]
                self.light_states[1]=signals[1]
                self.light_states[2]=signals[2]
                self.light_states[3]=signals[3]
                self.light_states[4]=signals[4]
                self.light_states[5]=signals[5]
                self.light_states[6]=signals[6]
                self.light_states[7]=signals[7]
                self.light_states[8]=signals[8]
                self.light_states[9]=signals[9]
                self.light_states[10]=signals[10]
                self.light_states[11]=signals[11]
                self.light_states[20]=signals[12]
                self.light_states[21]=signals[13]
                self.light_states[22]=signals[14]
                self.light_states[23]=signals[15]
                self.gate_states[0]=crossing[0]

            elif self.active_plc == "Green_Line_PLC_XandLdown.py":
                occ = self.occupied_blocks[70:146]
                signals, switches, crossing = process_states_green_xldown(occ)
                self.switch_states[4]=switches[0]
                self.switch_states[5]=switches[1]
                self.light_states[12]=signals[0]
                self.light_states[13]=signals[1]
                self.light_states[14]=signals[2]
                self.light_states[15]=signals[3]
                self.light_states[16]=signals[4]
                self.light_states[17]=signals[5]
                self.light_states[18]=signals[6]
                self.light_states[19]=signals[7]
                self.gate_states[1] = crossing[0]
            #self.load_track_outputs()
            
            if self.running:
                threading.Timer(0.2, self.run_plc).start()


    def run_trains(self):      
        if not self.running:
            return
        
        self.load_inputs_ctc()
        
        # Load actual train speeds from train_data.json
        actual_train_speeds = self.load_train_speeds()

        # First pass: clear occupied blocks for trains that have left our visible range
        for train in self.active_trains:
            train_pos = self.active_trains[train]["Train Position"]
            # If train is outside our visible range and we have it marked as occupied somewhere, clear it
            if train_pos not in self.visible_blocks and train_pos != 0:
                # Check if we were tracking this train and need to clear its old position
                if train in self.last_seen_position:
                    last_pos = self.last_seen_position[train]
                    if last_pos in self.visible_blocks and 0 <= last_pos < len(self.occupied_blocks):
                        if self.occupied_blocks[last_pos] == 1:
                            self.occupied_blocks[last_pos] = 0

        for train in self.active_trains:
            if train not in self.cmd_trains and self.active_trains[train]["Active"]==1:
                train_pos = self.active_trains[train]["Train Position"]
                sug_auth = self.active_trains[train]["Suggested Authority"]
                
                # Always update last seen position for tracking
                current_last_pos = self.last_seen_position.get(train, 0)
                
                # Skip trains not in our managed section
                # Only Controller 1 (XandLup) manages yard (block 0) - ALL trains start from yard
                if train_pos == 0 and self.active_plc != "Green_Line_PLC_XandLup.py":
                    # Controller 2 should not pick up trains from yard
                    self.last_seen_position[train] = train_pos
                    continue
                
                # If train is at yard (block 0), ONLY Controller 1 should activate it
                # Controller 2 should never activate a train at block 0
                if train_pos == 0:
                    # Additional check: ensure we're Controller 1
                    if self.active_plc != "Green_Line_PLC_XandLup.py":
                        self.last_seen_position[train] = train_pos
                        continue
                
                if train_pos not in self.managed_blocks and train_pos != 0:
                    # Update last seen position even if we're not managing it
                    self.last_seen_position[train] = train_pos
                    continue
                    
                
                if train_pos != 0:
                    # Check if this is a handoff from another controller
                    # If train was outside our managed section and is now inside, pick it up
                    last_in_our_section = current_last_pos in self.managed_blocks or current_last_pos == 0
                    now_in_our_section = train_pos in self.managed_blocks
                    is_handoff = not last_in_our_section and now_in_our_section and current_last_pos != 0
                    
                    if not is_handoff:
                        # Not a handoff - apply normal activation rules
                        # Only activate if:
                        # 1. Fresh dispatch from station with authority increase
                        # 2. Train is at a station block (valid starting point)
                        
                        if train_pos not in self.station_blocks and len(self.station_blocks) > 0:
                            # Train is mid-track (not at a station), not a handoff - skip to avoid authority reset
                            self.last_seen_position[train] = train_pos
                            continue
                        
                        # Even if at a station, check if it's a fresh dispatch or just passing through  
                        # If we just saw this train at a different position, it's in transit - don't reactivate
                        if current_last_pos != 0 and current_last_pos != train_pos:
                            # Train was already moving and entered this station
                            # This is NOT a fresh dispatch, so skip to avoid reactivation
                            self.last_seen_position[train] = train_pos
                            continue
                        
                        # If train hasn't moved since we last saw it, check if authority has increased (new dispatch)
                        if current_last_pos == train_pos:
                            # Train is stationary at same position
                            # Check if this is a new dispatch by comparing authority
                            last_auth = self.train_auth_start.get(train, 0)
                            if sug_auth <= last_auth:
                                # Authority hasn't increased - train is just waiting, don't reactivate
                                continue
                            # Authority increased - this is a new dispatch, proceed with activation below
                    else:
                        # This is a handoff - take over the train
                        # Read current authority from the shared JSON file (written by previous controller)
                        try:
                            with open(self.train_comm_file, 'r') as f:
                                train_data = json.load(f)
                                current_auth = train_data.get(train, {}).get("Commanded Authority", sug_auth)
                                current_speed = train_data.get(train, {}).get("Commanded Speed", self.active_trains[train]["Suggested Speed"])
                        except:
                            # If file not found or error, use CTC values
                            current_auth = sug_auth
                            current_speed = self.active_trains[train]["Suggested Speed"]
                    
                    # Use handoff authority if this is a handoff, otherwise use suggested authority
                    if is_handoff:
                        auth_to_use = current_auth
                        speed_to_use = current_speed
                    else:
                        auth_to_use = sug_auth
                        speed_to_use = self.active_trains[train]["Suggested Speed"]
                    
                    self.cmd_trains[train] = {
                        "cmd auth": auth_to_use,
                        "cmd speed": speed_to_use,
                        "pos": train_pos
                    }
                    # Track CTC authority for reactivation detection
                    # Use the ACTUAL authority being used, not necessarily CTC's suggested value
                    # This ensures proper comparison when CTC gives authority for next leg
                    self.last_ctc_authority[train] = auth_to_use
                    
                    # Initialize per-train tracking from current position
                    train_pos = self.active_trains[train]["Train Position"]
                    
                    # Find the index in green_order, or create a new sequence from current position
                    if train_pos in self.green_order:
                        self.train_idx[train] = self.green_order.index(train_pos)
                    else:
                        # Train not in green_order, just use position as-is (happens on alternate routes)
                        self.train_idx[train] = train_pos
                    
                    # Set starting position to current index for distance calculation
                    self.train_pos_start[train] = self.train_idx[train]
                    self.occupied_blocks[train_pos] = 1
                    
                    # For handoff, we need to calculate how much authority was originally given
                    # traveled = original_auth - current_auth, so original_auth = traveled + current_auth
                    if is_handoff:
                        # Distance traveled = sug_auth (CTC original) - current_auth (remaining)
                        traveled_before_handoff = sug_auth - auth_to_use
                        # Train will calculate distance as: traveled_total = train_auth_start - cmd_auth
                        # We want: traveled_total = traveled_before_handoff + distance_in_new_controller
                        # So: train_auth_start - cmd_auth = traveled_before_handoff + (train_auth_start - cmd_auth_new)
                        # Set train_auth_start = sug_auth (CTC original)
                        self.train_auth_start[train] = sug_auth
                        # cumulative_distance should reflect distance already traveled
                        self.cumulative_distance[train] = traveled_before_handoff
                    else:
                        self.train_auth_start[train] = auth_to_use
                        # Initialize cumulative distance tracker
                        # If starting from yard (block 0), start at 0; otherwise start at -block_length (already at end of station block)
                        if train_pos == 0:
                            self.cumulative_distance[train] = 0
                        else:
                            # Determine initial direction based on which next block will be used
                            # First, check if we already have a direction stored for this train (preserve direction)
                            if train in self.train_direction and train in self.last_seen_position:
                                # Train was previously active, preserve its direction
                                initial_direction = self.train_direction[train]
                            elif train_pos in self.block_graph:
                                block_info = self.block_graph[train_pos]
                                # Check if we'll use forward_next or reverse_next based on track topology
                                initial_direction = 'forward'
                                
                                # Check if next block in forward direction exists and is valid
                                forward_next = block_info['forward_next']
                                reverse_next = block_info['reverse_next']
                                
                                # Simple heuristic: if forward_next is -1 or goes to lower numbered block, likely reverse
                                if forward_next == -1 and reverse_next != -1:
                                    initial_direction = 'reverse'
                                elif forward_next != -1 and reverse_next != -1:
                                    # Both directions available
                                    # Use authority amount as hint: very long authority (>2500m) suggests continuing around the loop
                                    if sug_auth > 2500:
                                        # Long journey - likely continuing in current direction
                                        # For blocks that can go both ways, check the reverse_next to determine direction
                                        # Block 77 reverse goes to 101 (higher), forward goes to 76 (lower)
                                        if reverse_next > train_pos:
                                            initial_direction = 'reverse'
                                        else:
                                            initial_direction = 'forward'
                                    else:
                                        # Short journey - default to forward
                                        initial_direction = 'forward'
                                
                                self.train_direction[train] = initial_direction
                            else:
                                self.train_direction[train] = 'forward'  # Default to forward if not in graph
                            
                            # Set cumulative_distance based on direction
                            if self.train_direction[train] == 'reverse':
                                # Reverse: train starts at beginning of station block (needs to travel full block length)
                                self.cumulative_distance[train] = 0
                            else:
                                # Forward: train at end of station block (negative cumulative to account for already traveled distance)
                                self.cumulative_distance[train] = -self.block_lengths.get(train_pos, 0)
                    
                    self.last_seen_position[train] = train_pos
                else:
                    # Train starting from yard (block 0)
                    self.cmd_trains[train] = {
                        "cmd auth": self.active_trains[train]["Suggested Authority"],
                        "cmd speed": self.active_trains[train]["Suggested Speed"],
                        "pos": 0
                    }
                    # Track CTC authority for reactivation detection
                    self.last_ctc_authority[train] = self.active_trains[train]["Suggested Authority"]
                    # Initialize per-train tracking
                    self.train_idx[train] = 0
                    self.train_pos_start[train] = 0
                    self.train_auth_start[train] = self.active_trains[train]["Suggested Authority"]
                    self.train_direction[train] = 'forward'  # Default to forward
                    self.cumulative_distance[train] = 0
                    self.last_seen_position[train] = 0
                    # Mark block 0 as occupied
                    self.occupied_blocks[0] = 1

        ttr = []
        
        for cmd_train in self.cmd_trains:
            # Check if CTC has set Active = 0 (train should stop at station for dwell time)
            if cmd_train in self.active_trains:
                is_active = self.active_trains[cmd_train].get("Active", 0)
                if is_active == 0:
                    # CTC deactivated train - set speed and authority to 0
                    self.cmd_trains[cmd_train]["cmd auth"] = 0
                    self.cmd_trains[cmd_train]["cmd speed"] = 0
                    # Reset last_ctc_authority so ANY new authority from CTC will trigger reactivation
                    self.last_ctc_authority[cmd_train] = 0
                    # Don't remove from cmd_trains yet - CTC will reactivate with new authority
                    # Continue to next train
                    continue
                elif is_active == 1 and self.cmd_trains[cmd_train]["cmd auth"] == 0:
                    # Check if CTC has provided NEW authority (not the same authority that ran out)
                    new_auth = self.active_trains[cmd_train]["Suggested Authority"]
                    last_auth = self.last_ctc_authority.get(cmd_train, 0)
                    
                    # Only reactivate if authority has INCREASED (CTC gave new authority after dwell)
                    if new_auth > last_auth:
                        new_speed = self.active_trains[cmd_train]["Suggested Speed"]
                        self.cmd_trains[cmd_train]["cmd auth"] = new_auth
                        self.cmd_trains[cmd_train]["cmd speed"] = new_speed
                        # Update train_auth_start for proper distance tracking
                        self.train_auth_start[cmd_train] = new_auth
                        self.last_ctc_authority[cmd_train] = new_auth
                        # Reset cumulative distance - train is at station (end of current block)
                        # Set to negative block length so train will move to next block immediately
                        pos = self.cmd_trains[cmd_train]["pos"]
                        self.cumulative_distance[cmd_train] = -self.block_lengths.get(pos, 0)
                        print(f"[Wayside] Reactivated {cmd_train} at block {pos} with auth={new_auth}m, speed={new_speed}m/s")
                    else:
                        # Authority hasn't increased - train is stuck waiting for CTC
                        # Keep auth at 0 and wait
                        continue
            
            auth = self.cmd_trains[cmd_train]["cmd auth"]
            speed = self.cmd_trains[cmd_train]["cmd speed"]
            pos = self.cmd_trains[cmd_train]["pos"]
            
            # Use actual train speed if available, otherwise fall back to commanded speed
            actual_speed = actual_train_speeds.get(cmd_train, speed)
            
            # Check if another controller has moved this train outside our visible range
            # This handles the case where Controller 2 takes over and moves the train
            if cmd_train in self.active_trains:
                ctc_pos = self.active_trains[cmd_train]["Train Position"]
                if ctc_pos not in self.visible_blocks and ctc_pos != 0:
                    # Train has been moved outside our range by another controller
                    # Clear our last known position before removing
                    if 0 <= pos < len(self.occupied_blocks):
                        self.occupied_blocks[pos] = 0
                    ttr.append(cmd_train)
                    continue
            
            # Get suggested speed from CTC and speed limit for current block
            sug_speed = self.active_trains[cmd_train]["Suggested Speed"] if cmd_train in self.active_trains else speed
            speed_limit = self.block_speed_limits.get(pos, 100)  # Default to 100 m/s if no limit
            
            # Calculate target speed based on authority remaining
            # When authority is low, reduce speed to help train stop
            DECEL_THRESHOLD = 150  # Start decelerating when less than 150m authority
            MIN_SPEED_THRESHOLD = 40  # Start dropping below 10 m/s at 40m authority
            MIN_SPEED = 10  # Don't go below 10 m/s until MIN_SPEED_THRESHOLD
            FINAL_MIN_SPEED = 1  # Final minimum speed before stopping
            ACCELERATION = 5  # m/s per second increase
            DECELERATION = 20  # m/s per second decrease
            
            if auth < MIN_SPEED_THRESHOLD:
                # Below 40m authority - decelerate from 10 m/s to 1 m/s (minimum)
                # Linear deceleration from 10 m/s at 40m to 1 m/s at 0m
                target_speed = FINAL_MIN_SPEED + (MIN_SPEED - FINAL_MIN_SPEED) * (auth / MIN_SPEED_THRESHOLD)
                target_speed = max(target_speed, FINAL_MIN_SPEED)  # Never go below 1 m/s
            elif auth < DECEL_THRESHOLD:
                # Between 150m and 40m - decelerate from full speed to 10 m/s
                decel_factor = (auth - MIN_SPEED_THRESHOLD) / (DECEL_THRESHOLD - MIN_SPEED_THRESHOLD)
                target_speed = MIN_SPEED + (sug_speed - MIN_SPEED) * decel_factor
            else:
                # Normal operation - accelerate toward suggested speed
                target_speed = sug_speed
            
            # Cap at speed limit
            target_speed = min(target_speed, speed_limit)
            
            # Gradually adjust commanded speed toward target
            if speed < target_speed:
                speed = min(speed + ACCELERATION, target_speed)
            elif speed > target_speed:
                speed = max(speed - DECELERATION, target_speed)
            
            # Round to 4 decimal places to avoid floating point precision issues
            speed = round(speed, 4)
            
            # Update commanded speed
            self.cmd_trains[cmd_train]["cmd speed"] = speed
            
            # Check if CTC has updated the suggested authority (new authority dispatched)
            if cmd_train in self.active_trains:
                new_sug_auth = self.active_trains[cmd_train]["Suggested Authority"]
                # If suggested authority increased, reset tracking from current position
                if new_sug_auth > self.train_auth_start[cmd_train]:
                    self.train_auth_start[cmd_train] = new_sug_auth
                    self.train_pos_start[cmd_train] = self.train_idx[cmd_train]
                    # Reset cumulative distance (train is at station, at end of current block)
                    self.cumulative_distance[cmd_train] = -self.block_lengths.get(pos, 0)
                    # Update cmd_trains with new authority
                    auth = new_sug_auth
                    self.cmd_trains[cmd_train]["cmd auth"] = auth
            
            # Reduce authority based on actual train speed (distance traveled per second)
            auth = auth - actual_speed
            
            # Check if authority exhausted BEFORE checking handoff
            if auth <= 0: 
                auth = 0
                self.cmd_trains[cmd_train]["cmd auth"] = 0  # Update to 0 before removing
                self.cmd_trains[cmd_train]["cmd speed"] = 0  # Stop the train
                final_pos = self.cmd_trains[cmd_train]["pos"]  # Get final position from cmd_trains

                # Update position AND set Active=0 in CTC JSON (track controller manages Active based on authority)
                # CTC will detect Active=0 and provide new authority after dwell time
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        with self.file_lock:
                            with open(self.ctc_comm_file,'r') as f:
                                data = json.load(f)
                            # Update position AND set Active=0 when authority is exhausted
                            data["Trains"][cmd_train]["Train Position"] = final_pos
                            data["Trains"][cmd_train]["Active"] = 0
                            print(f"[Wayside] {cmd_train} authority exhausted at position {final_pos}, set Active=0")
                            with open(self.ctc_comm_file,'w') as f:
                                json.dump(data,f,indent=4)
                        break
                    except (json.JSONDecodeError, IOError) as e:
                        if retry < max_retries - 1:
                            time.sleep(0.01)
                        else:
                            print(f"Warning: Failed to update position for {cmd_train} after {max_retries} attempts: {e}")
                # DON'T remove from cmd_trains - keep it so we can handle reactivation
                # Just continue to next train (train will sit with auth=0 until CTC reactivates)
                continue
            
            self.cmd_trains[cmd_train]["cmd auth"] = auth
            self.cmd_trains[cmd_train]["cmd speed"] = speed
            
            # Use per-train tracking
            sug_auth = self.train_auth_start[cmd_train]
            idx = self.train_idx[cmd_train]
            
            # Check if train has traveled far enough to move to next block
            is_reverse = self.train_direction.get(cmd_train, 'forward') == 'reverse'
            
            # For reverse direction, use different threshold logic
            if is_reverse:
                # Reverse: Move to next block when within 2m (to ensure we show at station block)
                # Calculate how close we are to completing the current block
                cumulative = self.cumulative_distance.get(cmd_train, 0)
                current_block_length = self.block_lengths.get(pos, 100)
                traveled = sug_auth - auth
                remaining_in_block = (cumulative + current_block_length) - traveled
                
                should_move = traveled > cumulative and remaining_in_block <= 2
            else:
                # Forward: Use normal traveled_enough logic
                should_move = self.traveled_enough(sug_auth, auth, idx, cmd_train)
            
            if should_move:
                # For forward direction, use 2m threshold to prevent overshooting
                # For reverse direction, threshold already applied above
                if is_reverse or auth > 2:
                    # Move to next block
                    new_pos = self.get_next_block(pos, idx, cmd_train)
                    
                    # Check if we reached end of track
                    if new_pos == -1:
                        auth = 0
                        with self.file_lock:
                            with open(self.ctc_comm_file,'r') as f:
                                data = json.load(f)
                            # Update Active AND preserve position
                            data["Trains"][cmd_train]["Active"] = 0
                            data["Trains"][cmd_train]["Train Position"] = pos
                            with open(self.ctc_comm_file,'w') as f:
                                json.dump(data,f,indent=4)
                        ttr.append(cmd_train)
                    else:
                        # Successfully moved to new block
                        self.cmd_trains[cmd_train]["pos"] = new_pos
                        self.train_idx[cmd_train] += 1
                        
                        # After moving, add the old block's length to cumulative distance
                        if cmd_train not in self.cumulative_distance:
                            self.cumulative_distance[cmd_train] = 0
                        self.cumulative_distance[cmd_train] += self.block_lengths.get(pos, 100)
                        
                        # Write the new position to CTC immediately, even if it's outside managed section
                        # This ensures the other controller can see the train at the boundary
                        max_retries = 3
                        for retry in range(max_retries):
                            try:
                                with self.file_lock:
                                    with open(self.ctc_comm_file,'r') as f:
                                        data = json.load(f)
                                    data["Trains"][cmd_train]["Train Position"] = new_pos
                                    with open(self.ctc_comm_file,'w') as f:
                                        json.dump(data,f,indent=4)
                                break
                            except (json.JSONDecodeError, IOError) as e:
                                if retry < max_retries - 1:
                                    time.sleep(0.01)
                                else:
                                    print(f"Warning: Failed to write position for {cmd_train} after {max_retries} attempts: {e}")
                        
                        # Check if train moved outside visible range - remove completely
                        if new_pos not in self.visible_blocks and new_pos != 0:
                            if not hasattr(self, 'trains_to_handoff'):
                                self.trains_to_handoff = []
                            self.trains_to_handoff.append(cmd_train)
                            continue  # Skip further processing
                        # Check if train moved into handoff zone (outside managed but still visible)
                        elif new_pos not in self.managed_blocks and new_pos != 0:
                            # Continue tracking but don't write position to CTC (other controller will do that)
                            pass
                # else: stay at current block (at the station) when authority runs out

            # Only write train position back to CTC if train is in our managed section
            train_current_pos = self.cmd_trains[cmd_train]["pos"]
            if train_current_pos in self.managed_blocks or (train_current_pos == 0 and self.active_plc == "Green_Line_PLC_XandLup.py"):
                # Retry logic to handle concurrent file access from multiple controllers
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        with self.file_lock:
                            # Read and write in same critical section to avoid race condition
                            with open(self.ctc_comm_file,'r') as f:
                                data = json.load(f)
                            # Update ONLY this train's position, keep everything else from fresh read
                            data["Trains"][cmd_train]["Train Position"] = self.cmd_trains[cmd_train]["pos"]
                            with open(self.ctc_comm_file,'w') as f:
                                json.dump(data,f,indent=4)
                        break  # Success, exit retry loop
                    except (json.JSONDecodeError, IOError) as e:
                        if retry < max_retries - 1:
                            time.sleep(0.01)  # Wait 10ms before retrying
                        else:
                            print(f"Warning: Failed to update train position for {cmd_train} after {max_retries} attempts: {e}")

        # Write commanded speed/authority to train communication file BEFORE cleanup
        # This ensures trains with exhausted authority write 0 to the file
        # Pass ttr list so we know which trains are being removed (but not handed off yet)
        self.load_train_outputs(ttr)
        
        # Now add handoff trains to ttr for cleanup
        # Only remove trains that are truly outside our visible range
        if hasattr(self, 'trains_to_handoff'):
            for train in self.trains_to_handoff:
                # Double-check train is actually outside visible range before removing
                if train in self.cmd_trains:
                    train_pos = self.cmd_trains[train]["pos"]
                    if train_pos not in self.visible_blocks and train_pos != 0:
                        if train not in ttr:
                            ttr.append(train)
                else:
                    # Train already removed
                    if train not in ttr:
                        ttr.append(train)
            self.trains_to_handoff = []  # Clear for next iteration

        # Clean up trains that have completed
        for tr in ttr:
            if tr in self.cmd_trains:
                self.cmd_trains.pop(tr)
            if tr in self.train_idx:
                self.train_idx.pop(tr)
            if tr in self.train_pos_start:
                self.train_pos_start.pop(tr)
            if tr in self.train_auth_start:
                self.train_auth_start.pop(tr)
            # Don't remove train_direction - preserve it for reactivation
            # if tr in self.train_direction:
            #     self.train_direction.pop(tr)

        if self.running:
            threading.Timer(1.0, self.run_trains).start()


    def dist_to_EOB(self, idx: int) -> float:
        """Get the length of the block at the given index in green_order"""
        if 0 <= idx < len(self.green_order):
            block_num = self.green_order[idx]
            return self.block_lengths.get(block_num, 0)
        return 0

    def traveled_enough(self, sug_auth: int, cmd_auth: int, idx: int, train_id: str) -> bool:
        """Check if train has traveled far enough to move to the next block"""
        # Calculate distance traveled since activation/reset
        traveled = sug_auth - cmd_auth
        
        # Get cumulative distance that needs to be traveled to complete current block
        cumulative = self.cumulative_distance.get(train_id, 0)
        
        # Get current block length
        if train_id in self.cmd_trains:
            current_block = self.cmd_trains[train_id]["pos"]
            current_block_length = self.block_lengths.get(current_block, 100)
        else:
            current_block_length = 100
        
        # Total distance needed to complete current block
        distance_needed = cumulative + current_block_length
        
        # Move to next block only if traveled distance EXCEEDS distance needed
        return traveled > distance_needed

    def get_next_block_preview(self, current_block: int, train_id: str):
        """Preview what the next block would be without moving the train"""
        if current_block not in self.block_graph:
            return -1
        
        block_info = self.block_graph[current_block]
        direction = self.train_direction.get(train_id, 'forward')
        
        # Get next block based on direction
        if direction == 'forward':
            next_block = block_info['forward_next']
        else:  # reverse
            next_block = block_info['reverse_next']
        
        return next_block if next_block != -1 else -1

    def get_next_block(self, current_block: int, block_idx: int, train_id: str):
        """Get next block based on current block and train direction"""
        self.occupied_blocks[current_block] = 0
        
        if current_block not in self.block_graph:
            # Fallback to green_order if block not in graph
            if current_block == 151:
                self.train_idx[train_id] = 0
                return -1
            else:
                if block_idx + 1 < len(self.green_order):
                    next_block = self.green_order[block_idx + 1]
                    self.occupied_blocks[next_block] = 1
                    return next_block
                return -1
        
        # Use block_graph to determine next block based on direction
        direction = self.train_direction.get(train_id, 'forward')
        block_info = self.block_graph[current_block]
        
        if direction == 'forward':
            next_block = block_info['forward_next']
        else:
            next_block = block_info['reverse_next']
        
        # Check for direction transition points
        for from_block, to_block, new_direction in self.direction_transitions:
            if current_block == from_block and next_block == to_block:
                self.train_direction[train_id] = new_direction
                break
        
        if next_block == -1:
            # End of line, reset or switch direction if bidirectional
            if block_info['bidirectional']:
                self.train_direction[train_id] = 'reverse' if direction == 'forward' else 'forward'
            self.train_idx[train_id] = 0
            return -1
        
        self.occupied_blocks[next_block] = 1
        return next_block


    def override_light(self, block_id: int, state: int):
        if block_id in self.blocks_with_lights:
            self.light_states[self.blocks_with_lights.index(block_id)] = state

    def override_gate(self, block_id: int, state: int):
        pass

    def override_switch(self, block_id: int, state: int):
        pass

    def load_plc(self, filename: str):
        #see if file exists and is python file
        if os.path.isfile(filename) and filename.endswith(".py"):
            self.active_plc = self.change_plc(True, filename)
        else:
            self.active_plc = self.change_plc(False, self.active_plc)
        
        return self.active_plc

    def change_plc(self, result: bool, filename: str):
        if result:
            return filename
        else:
            return self.active_plc

    def load_train_speeds(self):
        """Load actual train speeds (via API or from Train_Model/train_data.json)"""
        train_speeds = {}
        
        # Phase 3: Use API client if available, otherwise file I/O
        if self.wayside_api:
            try:
                api_speeds = self.wayside_api.get_train_speeds()
                if api_speeds:
                    # API returns speeds in mph with train names as keys
                    # Convert to m/s (multiply by 0.44704)
                    for train_name, velocity_mph in api_speeds.items():
                        train_speeds[train_name] = velocity_mph * 0.44704
                    return train_speeds
                # else fall through to file I/O
            except Exception as e:
                print(f"[Wayside {self.wayside_id}] API load_train_speeds failed: {e}, falling back to file I/O")
        
        # Legacy file I/O (fallback or when API not available)
        try:
            # Path to train_data.json
            current_dir = os.path.dirname(os.path.abspath(__file__))
            train_data_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'Train_Model', 'train_data.json')
            
            if os.path.exists(train_data_path):
                with open(train_data_path, 'r') as f:
                    train_data = json.load(f)
                    
                # Read speeds for each train
                for i in range(1, 6):
                    train_key = f"train_{i}"
                    train_name = f"Train {i}"
                    
                    if train_key in train_data:
                        outputs = train_data[train_key].get("outputs", {})
                        # Convert mph to m/s (multiply by 0.44704)
                        velocity_mph = outputs.get("velocity_mph", 0.0)
                        velocity_ms = velocity_mph * 0.44704
                        train_speeds[train_name] = velocity_ms
        except Exception as e:
            pass  # Silently fail, will use commanded speed as fallback
        
        return train_speeds
    
    def load_inputs_ctc(self):
        # Phase 3: Use API client if available, otherwise file I/O
        if self.wayside_api:
            try:
                ctc_commands = self.wayside_api.get_ctc_commands()
                if ctc_commands:
                    # API returns data in expected format
                    trains = ctc_commands.get("Trains", {})
                    self.active_trains = trains
                    self.closed_blocks = ctc_commands.get("Block Closure", [])
                    self.ctc_sugg_switches = ctc_commands.get("Switch Suggestion", [])
                    return
                # else fall through to file I/O
            except Exception as e:
                print(f"[Wayside {self.wayside_id}] API load_inputs_ctc failed: {e}, falling back to file I/O")
        
        # Legacy file I/O (fallback or when API not available)
        max_retries = 3
        for retry in range(max_retries):
            try:
                with self.file_lock:
                    with open(self.ctc_comm_file, 'r') as f:
                        data = json.load(f)
                        # Ensure trains section exists and contains expected keys
                        trains = data.get("Trains", {})
                        for tname, tinfo in list(trains.items()):
                            if not isinstance(tinfo, dict):
                                trains[tname] = {}
                                tinfo = trains[tname]
                            # Set defaults for keys the controller expects
                            tinfo.setdefault("Train Position", 0)
                            tinfo.setdefault("Train State", "")
                            tinfo.setdefault("Active", 0)
                            tinfo.setdefault("Suggested Authority", 0)
                            tinfo.setdefault("Suggested Speed", 0)
                        # Update in-memory structures
                        data["Trains"] = trains
                        self.active_trains = trains
                        self.closed_blocks = data.get("Block Closure", [])
                        self.ctc_sugg_switches = data.get("Switch Suggestion", [])
                break  # Success
            except (json.JSONDecodeError, IOError) as e:
                if retry < max_retries - 1:
                    time.sleep(0.01)
                else:
                    print(f"Warning: Failed to load CTC inputs after {max_retries} attempts: {e}")
            
            

    def load_inputs_track(self):
        #read track to wayside json file
        with self.file_lock:
            with open(self.track_comm_file, 'r') as f:
                data = json.load(f)
                #self.occupied_blocks = data.get("G-Occupancy", [0]*152)
                self.input_faults = data.get("G-Failures", [0]*152*3)
        
     
    def load_track_outputs(self):
        with self.file_lock:
            with open(self.track_comm_file, 'r') as f:
                data = json.load(f)

            # Update only the switches, lights, and gates managed by this controller
            if self.active_plc == "Green_Line_PLC_XandLup.py":
                # Controller 1: switches 0-3, lights 0-11 & 20-23, gate 0
                for i in range(4):
                    data["G-switches"][i] = self.switch_states[i]
                for i in range(12):
                    data["G-lights"][i] = self.light_states[i]
                for i in range(20, 24):
                    data["G-lights"][i] = self.light_states[i]
                data["G-gates"][0] = self.gate_states[0]
                
                # Controller 1: Update occupancy for blocks 0-69 and 144-150 only
                for i in range(0, 70):
                    data["G-Occupancy"][i] = self.occupied_blocks[i]
                for i in range(144, 151):
                    data["G-Occupancy"][i] = self.occupied_blocks[i]
                
            elif self.active_plc == "Green_Line_PLC_XandLdown.py":
                # Controller 2: switches 4-5, lights 12-19, gate 1
                for i in range(4, 6):
                    data["G-switches"][i] = self.switch_states[i]
                for i in range(12, 20):
                    data["G-lights"][i] = self.light_states[i]
                data["G-gates"][1] = self.gate_states[1]
                
                # Controller 2: Update occupancy for blocks 70-143 only
                for i in range(70, 144):
                    data["G-Occupancy"][i] = self.occupied_blocks[i]

            # Handle up to 5 trains - each controller updates only its managed trains
            train_ids = ["Train 1", "Train 2", "Train 3", "Train 4", "Train 5"]
            
            for i, train_id in enumerate(train_ids):
                if train_id in self.cmd_trains:
                    data["G-Commanded Authority"][i] = self.cmd_trains[train_id]["cmd auth"]
                    data["G-Commanded Speed"][i] = self.cmd_trains[train_id]["cmd speed"]
                

            

            # Now rewrite cleanly (overwrite file)
            with open(self.track_comm_file, 'w') as f:
                json.dump(data, f, indent=4)

            

    def load_ctc_outputs(self):
        pass

    def load_train_outputs(self, trains_to_remove=[]):
        """Write commanded speed and authority directly to train communication file"""
        # Don't use file_lock here since both controllers need to write independently
        try:
            with open(self.train_comm_file, 'r') as f:
                data = json.load(f)
        except:
            # If file doesn't exist or is corrupted, create fresh structure
            data = {
                "Train 1": {"Commanded Speed": 0, "Commanded Authority": 0, "Beacon": {"Current Station": "", "Next Station": ""}, "Train Speed": 0},
                "Train 2": {"Commanded Speed": 0, "Commanded Authority": 0, "Beacon": {"Current Station": "", "Next Station": ""}, "Train Speed": 0},
                "Train 3": {"Commanded Speed": 0, "Commanded Authority": 0, "Beacon": {"Current Station": "", "Next Station": ""}, "Train Speed": 0},
                "Train 4": {"Commanded Speed": 0, "Commanded Authority": 0, "Beacon": {"Current Station": "", "Next Station": ""}, "Train Speed": 0},
                "Train 5": {"Commanded Speed": 0, "Commanded Authority": 0, "Beacon": {"Current Station": "", "Next Station": ""}, "Train Speed": 0}
            }
        
        # Load actual train speeds to write to output file
        actual_train_speeds = self.load_train_speeds()

        # Update commanded speed and authority only for trains in our managed blocks
        train_ids = ["Train 1", "Train 2", "Train 3", "Train 4", "Train 5"]
        
        for train_id in train_ids:
            # If train is being removed by THIS controller, write 0
            if train_id in trains_to_remove:
                data[train_id]["Commanded Speed"] = 0
                data[train_id]["Commanded Authority"] = 0
                data[train_id]["Train Speed"] = 0
            elif train_id in self.cmd_trains:
                # Only update if train is in our managed section
                train_pos = self.cmd_trains[train_id]["pos"]
                # Controller 2 should NEVER write outputs for trains at block 0 (yard)
                if train_pos == 0 and self.active_plc != "Green_Line_PLC_XandLup.py":
                    continue  # Skip - Controller 1 handles yard
                if train_pos in self.managed_blocks or (train_pos == 0 and self.active_plc == "Green_Line_PLC_XandLup.py"):
                    # Convert m/s to mph (multiply by 2.23694)
                    cmd_speed_mph = self.cmd_trains[train_id]["cmd speed"] * 2.23694
                    # Convert meters to yards (multiply by 1.09361)
                    cmd_auth_yds = self.cmd_trains[train_id]["cmd auth"] * 1.09361
                    
                    data[train_id]["Commanded Speed"] = cmd_speed_mph
                    data[train_id]["Commanded Authority"] = cmd_auth_yds
                    # Write actual train speed from train_data.json (also convert to mph)
                    data[train_id]["Train Speed"] = actual_train_speeds.get(train_id, 0) * 2.23694
                    
                    # Update beacon data based on train direction and current block
                    if train_pos in self.block_graph:
                        train_direction = self.train_direction.get(train_id, 'forward')
                        block_data = self.block_graph[train_pos]
                        
                        if train_direction == 'forward' and block_data['forward_beacon']['has_beacon']:
                            data[train_id]["Beacon"]["Current Station"] = block_data['forward_beacon']['current_station']
                            data[train_id]["Beacon"]["Next Station"] = block_data['forward_beacon']['next_station']
                        elif train_direction == 'reverse' and block_data['reverse_beacon']['has_beacon']:
                            data[train_id]["Beacon"]["Current Station"] = block_data['reverse_beacon']['current_station']
                            data[train_id]["Beacon"]["Next Station"] = block_data['reverse_beacon']['next_station']
                        # If no beacon at current block, keep existing beacon data (don't clear it)

                        # Update train status back to CTC for real-time position tracking
                        if self.wayside_api:
                            try:
                                self.wayside_api.update_train_status(
                                    train_name=train_id,
                                    position=int(train_pos),
                                    state="moving" if actual_train_speeds.get(train_id, 0) > 0 else "stopped",
                                    active=1 if train_id in self.cmd_trains else 0
                                )
                            except Exception as e:
                                print(f"[SW Wayside {self.wayside_id}] CTC update failed: {e}")

                # else: don't update - other controller is managing this train

        with open(self.train_comm_file, 'w') as f:
            json.dump(data, f, indent=4)


        

    def get_block_data(self, block_id: int):
        
        if block_id in self.blocks_with_switches:
            switch_state = self.switch_states[self.blocks_with_switches.index(block_id)]
        else:
            switch_state = "N/A"
        if block_id in self.blocks_with_lights:
            light_state0 = self.light_states[(self.blocks_with_lights.index(block_id))*2]
            light_state1 = self.light_states[(self.blocks_with_lights.index(block_id))*2+1]
            light_state = f"{light_state0}{light_state1}"
         
        else:
            light_state = "N/A"
        if block_id in self.blocks_with_gates:
            gate_state = self.gate_states[self.blocks_with_gates.index(block_id)]
        else:
            gate_state = "N/A"

        if self.occupied_blocks[block_id] == 1:
            occupied = True
        else:
            occupied = False
        
        if self.input_faults[block_id*3] == 1:
            failure = 1
        elif self.input_faults[block_id*3+1] == 1:
            failure = 2
        elif self.input_faults[block_id*3+2] == 1:
            failure = 3
        else:
            failure = 0
        desired = {
            "block_id": block_id,
            "occupied": occupied,
            "switch_state": switch_state,
            "light_state": light_state,
            "gate_state": gate_state,
            "Failure": failure
        }
        return desired

    def get_active_trains(self):
        return self.cmd_trains
    def get_start_plc(self):
        return self.active_plc

    def confirm_auth(self):
        pass

    def confirm_speed(self):
        pass

    def confirm_closure(self):
        pass
    
    def confirm_states(self):
        pass

    def update_block_status(self):
        pass    

    def confirm_status(self):
        pass
