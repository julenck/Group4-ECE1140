

import json
import os
import time
#from .Green_Line_PLC_XandLup import process_states_green_xlup
#from .Green_Line_PLC_XandLdown import process_states_green_xldown
from Green_Line_PLC_XandLup import process_states_green_xlup
from Green_Line_PLC_XandLdown import process_states_green_xldown
import threading
import csv


class sw_wayside_controller:
    def __init__(self, vital,plc=""):
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
        self.active_plc: str = plc
        self.ctc_comm_file: str = "ctc_to_wayside.json"
        self.track_comm_file: str = "track_controller\\New_SW_Code\\track_to_wayside.json"
        self.block_status: list = []
        self.detected_faults: dict = {}
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
        
        # Define block ranges for each PLC
        if self.active_plc == "Green_Line_PLC_XandLup.py":
            self.managed_blocks = set(range(0, 73)) | set(range(144, 151))  # Blocks 0-72 and 144-150 (matches occ1+occ2 slice)
            print(f"DEBUG: Controller 1 (XandLup) managing blocks: 0-72 and 144-150 (total {len(self.managed_blocks)} blocks)")
        elif self.active_plc == "Green_Line_PLC_XandLdown.py":
            self.managed_blocks = set(range(70, 146))  # Blocks 70-145 (matches occ slice)
            print(f"DEBUG: Controller 2 (XandLdown) managing blocks: 70-145 (total {len(self.managed_blocks)} blocks)")
        else:
            self.managed_blocks = set(range(0, 152))  # All blocks if no specific PLC

        # Load track data from Excel file
        self.block_graph = {}  # Maps block number to {length, forward_next, reverse_next, bidirectional}
        self.block_distances = {}  # Maps block number to cumulative distance
        self.block_lengths = {}  # Maps block number to individual block length
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
                    
                    if block_num and block_num.strip():
                        try:
                            block_num = int(block_num)
                            length = float(length) if length else 0
                            cumulative_distance += length
                            
                            # Check if this block has a station
                            if has_station.strip() == '1':
                                self.station_blocks.add(block_num)
                            
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
                                'cumulative_distance': cumulative_distance
                            }
                            self.block_distances[block_num] = cumulative_distance
                            self.block_lengths[block_num] = length
                        except ValueError as ve:
                            continue
            
            print(f"Loaded {len(self.block_graph)} blocks from track_data.csv")
            print(f"Found {len(self.station_blocks)} station blocks: {sorted(self.station_blocks)}")
            
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

        for train in self.active_trains:
            if train not in self.cmd_trains and self.active_trains[train]["Active"]==1:
                train_pos = self.active_trains[train]["Train Position"]
                sug_auth = self.active_trains[train]["Suggested Authority"]
                
                # Always update last seen position for tracking
                current_last_pos = self.last_seen_position.get(train, 0)
                
                # Skip trains not in our managed section
                if train_pos not in self.managed_blocks and train_pos != 0:
                    # Update last seen position even if we're not managing it
                    self.last_seen_position[train] = train_pos
                    # print(f"DEBUG: {self.active_plc} skipping {train} at block {train_pos} (not in managed_blocks)")
                    continue
                
                if train_pos != 0:
                    # Check if this train was already dispatched/activated elsewhere
                    # Only activate if:
                    # 1. Train is at a station block (valid starting point), AND
                    # 2. Train was previously at position 0 (newly dispatched), not just entering from another block
                    
                    if train_pos not in self.station_blocks and len(self.station_blocks) > 0:
                        # Train is mid-track (not at a station), likely already being managed - skip to avoid authority reset
                        self.last_seen_position[train] = train_pos
                        continue
                    
                    # Even if at a station, check if it's a fresh dispatch or just passing through  
                    # If we just saw this train at a different position, it's in transit - don't reactivate
                    if current_last_pos != 0 and current_last_pos != train_pos:
                        # Train was already moving and entered this station - handoff scenario
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
                    
                    print(f"DEBUG: {self.active_plc} Adding {train} to cmd_trains - Position: {train_pos}, Active: {self.active_trains[train]['Active']}, cmd_trains keys: {list(self.cmd_trains.keys())}")
                    
                    self.cmd_trains[train] = {
                        "cmd auth": sug_auth,
                        "cmd speed": self.active_trains[train]["Suggested Speed"],
                        "pos": train_pos
                    }
                    
                    # Initialize per-train tracking from current position
                    train_pos = self.active_trains[train]["Train Position"]
                    
                    # Find the index in green_order, or create a new sequence from current position
                    if train_pos in self.green_order:
                        self.train_idx[train] = self.green_order.index(train_pos)
                    else:
                        # Train not in green_order, just use position as-is
                        print(f"Warning: Train {train} at block {train_pos} not in green_order, using position directly")
                        self.train_idx[train] = train_pos
                    
                    # Set starting position to current index for distance calculation
                    self.train_pos_start[train] = self.train_idx[train]
                    self.occupied_blocks[train_pos] = 1
                    self.train_auth_start[train] = sug_auth
                    
                    # Initialize cumulative distance tracker
                    # If starting from yard (block 0), start at 0; otherwise start at -block_length (already at end of station block)
                    if train_pos == 0:
                        self.cumulative_distance[train] = 0
                    else:
                        self.cumulative_distance[train] = -self.block_lengths.get(train_pos, 0)
                    
                    # Determine initial direction based on position
                    self.train_direction[train] = 'forward'  # Default to forward
                    self.last_seen_position[train] = train_pos
                    print(f"Train {train} activated at block {train_pos} (idx: {self.train_idx[train]}) with {self.train_auth_start[train]}m authority")
                else:
                    self.cmd_trains[train] = {
                        "cmd auth": self.active_trains[train]["Suggested Authority"],
                        "cmd speed": self.active_trains[train]["Suggested Speed"],
                        "pos": 0
                    }
                    # Initialize per-train tracking
                    self.train_idx[train] = 0
                    self.train_pos_start[train] = 0
                    self.train_auth_start[train] = self.active_trains[train]["Suggested Authority"]
                    self.train_direction[train] = 'forward'  # Default to forward

        ttr = []
        for cmd_train in self.cmd_trains:
            auth = self.cmd_trains[cmd_train]["cmd auth"]
            speed = self.cmd_trains[cmd_train]["cmd speed"]
            pos = self.cmd_trains[cmd_train]["pos"]
            
            # Check if CTC has updated the suggested authority (new authority dispatched)
            if cmd_train in self.active_trains:
                new_sug_auth = self.active_trains[cmd_train]["Suggested Authority"]
                # If suggested authority increased, reset tracking from current position
                if new_sug_auth > self.train_auth_start[cmd_train]:
                    print(f"Train {cmd_train}: Authority updated from {self.train_auth_start[cmd_train]}m to {new_sug_auth}m at block {pos}")
                    self.train_auth_start[cmd_train] = new_sug_auth
                    self.train_pos_start[cmd_train] = self.train_idx[cmd_train]
                    # Reset cumulative distance (train is at station, at end of current block)
                    self.cumulative_distance[cmd_train] = -self.block_lengths.get(pos, 0)
                    # Update cmd_trains with new authority
                    auth = new_sug_auth
                    self.cmd_trains[cmd_train]["cmd auth"] = auth
            
            auth = auth - speed
            
            # Check if authority exhausted BEFORE checking handoff
            if auth <= 0: 
                auth = 0
                print(f"Train {cmd_train}: Authority exhausted at block {pos}, deactivating train")
                
                #set train to inactive
                with self.file_lock:
                    with open(self.ctc_comm_file,'r') as f:
                        data = json.load(f)
                    with open(self.ctc_comm_file,'w') as f:
                        data["Trains"][cmd_train]["Active"] = 0
                        json.dump(data,f,indent=4)
                ttr.append(cmd_train)
                continue  # Skip rest of processing for this train
            
            # Check if train has left our managed section - hand off to other controller
            # Only hand off if train still has authority (not exhausted above)
            if pos not in self.managed_blocks and pos != 0:
                print(f"Train {cmd_train}: Leaving managed section at block {pos}, handing off to other controller")
                ttr.append(cmd_train)
                continue
            
            self.cmd_trains[cmd_train]["cmd auth"] = auth
            self.cmd_trains[cmd_train]["cmd speed"] = speed
            # Use per-train tracking
            sug_auth = self.train_auth_start[cmd_train]
            idx = self.train_idx[cmd_train]
            
            # Check if train has traveled far enough to move to next block
            if self.traveled_enough(sug_auth, auth, idx, cmd_train):
                # Only move to next block if we have enough remaining authority to enter it
                if auth > 0:
                    # Move to next block
                    new_pos = self.get_next_block(pos, idx, cmd_train)
                    
                    # Check if we reached end of track
                    if new_pos == -1:
                        auth = 0
                        print(f"Train {cmd_train}: Reached end of track at block {pos}")
                        with self.file_lock:
                            with open(self.ctc_comm_file,'r') as f:
                                data = json.load(f)
                            with open(self.ctc_comm_file,'w') as f:
                                data["Trains"][cmd_train]["Active"] = 0
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
                        print(f"Train {cmd_train}: Moved from {pos} to {new_pos}, cumulative={self.cumulative_distance[cmd_train]}m, traveled={sug_auth - auth}m, auth_remaining={auth}m")
                # else: stay at current block (at the station) when authority runs out


            with self.file_lock:
                with open(self.ctc_comm_file,'r') as f:
                    data = json.load(f)
                with open(self.ctc_comm_file,'w') as f:
                    data["Trains"][cmd_train]["Train Position"] = self.cmd_trains[cmd_train]["pos"]
                    json.dump(data,f,indent=4)

        # Clean up trains that have completed
        for tr in ttr:
            print(f"DEBUG: Removing {tr} from cmd_trains")
            if tr in self.cmd_trains:
                self.cmd_trains.pop(tr)
            if tr in self.train_idx:
                self.train_idx.pop(tr)
            if tr in self.train_pos_start:
                self.train_pos_start.pop(tr)
            if tr in self.train_auth_start:
                self.train_auth_start.pop(tr)
            if tr in self.train_direction:
                self.train_direction.pop(tr)

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
                print(f"Train {train_id}: Direction changed to {new_direction} at transition {from_block}->{to_block}")
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

    def load_inputs_ctc(self):
        with self.file_lock:
            with open(self.ctc_comm_file, 'r') as f:
                data = json.load(f)
                self.active_trains = data.get("Trains", {})
                self.closed_blocks = data.get("Block Closure", [])
                self.ctc_sugg_switches = data.get("Switch Suggestion", [])
            
            

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

            # Update values


            data["G-switches"] = self.switch_states
            data["G-lights"] = self.light_states
            data["G-gates"] = self.gate_states

            data["G-Occupancy"] = self.occupied_blocks

            # Handle up to 5 trains
            train_ids = ["Train 1", "Train 2", "Train 3", "Train 4", "Train 5"]
            cmd_auth = [0, 0, 0, 0, 0]
            cmd_speed = [0, 0, 0, 0, 0]
            
            for i, train_id in enumerate(train_ids):
                if train_id in self.cmd_trains:
                    cmd_auth[i] = self.cmd_trains[train_id]["cmd auth"]
                    cmd_speed[i] = self.cmd_trains[train_id]["cmd speed"]
            
            data["G-Commanded Authority"] = cmd_auth
            data["G-Commanded Speed"] = cmd_speed
                

            

            # Now rewrite cleanly (overwrite file)
            with open(self.track_comm_file, 'w') as f:
                json.dump(data, f, indent=4)

            

    def load_ctc_outputs(self):
        pass


        

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
