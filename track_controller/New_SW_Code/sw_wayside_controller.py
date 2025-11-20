

import json
import os
import sys
import time
from .Green_Line_PLC_XandLup import process_states_green_xlup
from .Green_Line_PLC_XandLdown import process_states_green_xldown
import threading

# Add parent directories for time_controller
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)
if grandparent_dir not in sys.path:
    sys.path.append(grandparent_dir)

from time_controller import get_time_controller


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
        
        # Get time controller for synchronized updates
        self.time_controller = get_time_controller()
        
        self.active_trains: dict = {}
        self.occupied_blocks: list = [0]*152
        self.light_states: list = [0]*24
        self.gate_states: list = [0,0]
        self.switch_states: list = [0]*6
        self.ctc_sugg_switches: list = [0]*6
        self.output_data: dict = {}
        self.active_plc: str = plc
        self.ctc_comm_file: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ctc_track_controller.json")
        self.track_comm_file: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Track_Model", "track_model_Track_controller.json")
        self.block_status: list = []
        self.detected_faults: dict = {}
        self.input_faults: list = [0]*152*3
        self.blocks_with_switches: list = [13,28,57,63,77,85]
        self.blocks_with_lights: list = [0,3,7,29,58,62,76,86,100,101,150,151]
        self.blocks_with_gates: list = [19,108]
        self.running: bool = True
        self.file_lock = threading.Lock()
        self.cmd_trains: dict = {}
        self.idx = 0
        self.pos_start = 0
        self.auth_start = 0


        self.green_order = [0,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,
                       85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,85,84,83,82,81,80,79,
                       78,77,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,
                       116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,
                       133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,
                       150,28,27,26,25,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10,9,8,
                       7,6,5,4,3,2,1,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,
                       29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,
                       50,51,52,53,54,55,56,57,151]



        # Start PLC processing loop
        self.run_plc()
        self.run_trains()

    # Methods
    def stop(self):
        # Stop PLC processing loop
        self.running = False

    def run_plc(self):
        if not self.running:
            self.active_plc = ""
            return
        #call plc function
        if self.active_plc != "":
            # Load occupancy from track model
            self.load_inputs_track()
            
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
            self.load_track_outputs()
            
            if self.running:
                # Get synchronized interval and cap for PLC updates
                interval_s = self.time_controller.get_update_interval_ms() / 1000.0
                interval_s = max(0.1, min(interval_s, 1.0))  # Cap between 0.1s and 1.0s
                threading.Timer(interval_s, self.run_plc).start()


    def run_trains(self):      
        if not self.running:
            return
        
        self.load_inputs_ctc()

        for train in self.active_trains:
            if train not in self.cmd_trains and self.active_trains[train]["Active"]==1:
                if self.active_trains[train]["Train Position"] != 0:
                    train_pos = self.active_trains[train]["Train Position"]
                    # Find the index of this position in green_order
                    try:
                        pos_idx = self.green_order.index(train_pos)
                    except ValueError:
                        pos_idx = 0  # Default to yard if position not found
                    
                    self.cmd_trains[train] = {
                        "cmd auth": self.active_trains[train]["Suggested Authority"],
                        "cmd speed": self.active_trains[train]["Suggested Speed"],
                        "pos": train_pos,
                        "idx": pos_idx,  # Store index per train
                        "pos_start": pos_idx,  # Store starting position index per train
                        "auth_start": self.active_trains[train]["Suggested Authority"],
                        "last_update_time": time.time(),  # Track last update for time-based movement
                        "distance_traveled_ft": 0.0  # Accumulated distance in feet
                    }
                    print(f"[Wayside] Added {train} to cmd_trains: pos={train_pos}, idx={pos_idx}, auth={self.active_trains[train]['Suggested Authority']}, speed={self.active_trains[train]['Suggested Speed']}")
                    self.idx = pos_idx
                    self.pos_start = pos_idx
                    self.auth_start = self.active_trains[train]["Suggested Authority"]
                    
                    # Write initial position to track model so it knows where train starts
                    self.write_initial_train_position_to_track(train, train_pos)
                else:
                    self.cmd_trains[train] = {
                        "cmd auth": self.active_trains[train]["Suggested Authority"],
                        "cmd speed": self.active_trains[train]["Suggested Speed"],
                        "pos": 0,
                        "idx": 0,  # Store index per train
                        "pos_start": 0,  # Store starting position index per train
                        "auth_start": self.active_trains[train]["Suggested Authority"],
                        "last_update_time": time.time(),
                        "distance_traveled_ft": 0.0
                    }
                    self.idx = 0
                    self.pos_start = 0
                    self.auth_start = self.active_trains[train]["Suggested Authority"]
            elif train in self.cmd_trains and self.active_trains[train]["Active"] == 1:
                # Update authority and speed if CTC has sent new values
                new_auth = self.active_trains[train]["Suggested Authority"]
                new_speed = self.active_trains[train]["Suggested Speed"]
                current_auth = self.cmd_trains[train]["cmd auth"]
                auth_start = self.cmd_trains[train]["auth_start"]
                
                # If CTC sent new authority (different from what we started with), update it
                if new_auth != auth_start and new_auth > current_auth:
                    print(f"[Wayside] {train} received new authority: {new_auth} (current: {current_auth}, started: {auth_start})")
                    self.cmd_trains[train]["cmd auth"] = new_auth
                    self.cmd_trains[train]["auth_start"] = new_auth
                    self.cmd_trains[train]["pos_start"] = self.cmd_trains[train]["idx"]  # Reset starting position
                
                # Always update speed
                self.cmd_trains[train]["cmd speed"] = new_speed
                
                

        ttr = []
        for cmd_train in self.cmd_trains:
            auth = self.cmd_trains[cmd_train]["cmd auth"]
            speed = self.cmd_trains[cmd_train]["cmd speed"]
            pos = self.cmd_trains[cmd_train]["pos"]
            
            print(f"[Wayside] {cmd_train}: pos={pos}, auth={auth}, speed={speed}")
            
            # Update position based on time and speed
            current_time = time.time()
            last_update = self.cmd_trains[cmd_train]["last_update_time"]
            elapsed_time_hours = (current_time - last_update) / 3600.0  # Convert seconds to hours
            
            # Calculate distance traveled: distance = speed (mph) * time (hours) * 5280 (ft/mile)
            if speed > 0 and auth > 0:
                distance_traveled_ft = speed * elapsed_time_hours * 5280.0
                self.cmd_trains[cmd_train]["distance_traveled_ft"] += distance_traveled_ft
                
                # Get current block length
                current_idx = self.cmd_trains[cmd_train]["idx"]
                block_length_ft = self.get_block_length(current_idx)
                
                # If we've traveled past the current block, move to next
                if self.cmd_trains[cmd_train]["distance_traveled_ft"] >= block_length_ft:
                    if current_idx < len(self.green_order) - 1:
                        # Move to next block
                        new_idx = current_idx + 1
                        new_pos = self.green_order[new_idx]
                        self.cmd_trains[cmd_train]["idx"] = new_idx
                        self.cmd_trains[cmd_train]["pos"] = new_pos
                        self.cmd_trains[cmd_train]["distance_traveled_ft"] = 0.0  # Reset distance for new block
                        print(f"[Wayside] {cmd_train} advanced to block {new_pos}")
                        
                        # Update position in track model JSON
                        self.update_train_position_in_track(cmd_train, new_pos)
            
            self.cmd_trains[cmd_train]["last_update_time"] = current_time
            
            auth = auth - speed
            
            if auth <= 0:
                auth = 0
                print(f"[Wayside] {cmd_train} authority depleted, train will stop until CTC sends new authority")
                # Don't set train inactive - let it wait for CTC to send new authority
            
            self.cmd_trains[cmd_train]["cmd auth"] = auth
            self.cmd_trains[cmd_train]["cmd speed"] = speed
            
            # Position is now updated by track model based on commanded speed/authority
            # We just send the position we receive from track model to CTC

            with self.file_lock:
                try:
                    with open(self.ctc_comm_file,'r') as f:
                        data = json.load(f)
                    with open(self.ctc_comm_file,'w') as f:
                        data["Trains"][cmd_train]["Train Position"] = self.cmd_trains[cmd_train]["pos"]
                        json.dump(data,f,indent=4)
                except (json.JSONDecodeError, FileNotFoundError):
                    pass

        for tr in ttr:
            self.cmd_trains.pop(tr)

        if self.running:
            # Get synchronized interval
            interval_s = self.time_controller.get_update_interval_ms() / 1000.0
            threading.Timer(interval_s, self.run_trains).start()


    def dist_to_EOB(self, idx: int) -> int:
        #distance to end of block based on index in green order
        block_dist = [100, 200, 300, 500, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 
        1700, 2000, 2300, 2600, 2900, 3200, 3500, 3800, 4100, 4400, 4500, 4586.6, 
        4686.6, 4761.6, 4836.6, 4911.6, 4986.6, 5061.6, 5136.6, 5211.6, 5286.6, 
        5361.6, 5436.6, 5511.6, 5586.6, 5886.6, 6186.6, 6486.6, 6786.6, 7086.6, 
        7386.6, 7686.6, 7986.6, 8286.6, 8361.6, 8396.6, 8496.6, 8596.6, 8676.6, 
        8776.6, 8876.6, 8966.6, 9066.6, 9166.6, 9266.6, 9366.6, 9466.6, 9566.6, 
        9728.6, 9828.6, 9928.6, 9978.6, 10028.6, 10068.6, 10118.6, 10168.6, 
        10218.6, 10268.6, 10318.6, 10368.6, 10418.6, 10468.6, 10518.6, 10568.6, 
        10618.6, 10668.6, 10718.6, 10768.6, 10818.6, 10868.6, 10918.6, 10968.6, 
        11018.6, 11068.6, 11118.6, 11168.6, 11218.6, 11268.6, 11318.6, 11368.6, 
        11418.6, 11468.6, 11652.6, 11692.6, 11727.6, 11777.6, 11827.6, 11927.6, 
        12127.6, 12427.6, 12727.6, 13027.6, 13327.6, 13477.6, 13627.6, 13777.6, 
        13927.6, 14077.6, 14227.6, 14377.6, 14527.6, 14627.6, 14727.6, 14827.6, 
        14927.6, 15027.6, 15127.6, 15227.6, 15327.6, 15427.6, 15527.6, 15627.6, 
        15727.6, 15877.6, 16027.6, 16177.6, 16327.6, 16477.6, 16627.6, 16777.6, 
        16927.6, 17227.6, 17527.6, 17827.6, 18127.6, 18327.6, 18427.6, 18477.6, 
        18527.6, 18577.6, 18627.6, 18677.6, 18727.6, 18777.6, 18827.6, 18877.6, 
        18927.6, 18977.6, 19027.6, 19077.6, 19127.6, 19177.6, 19227.6, 19277.6, 
        19327.6, 19377.6, 19427.6, 19477.6, 19527.6, 19577.6, 19627.6, 19677.6, 
        19727.6, 19777.6, 19827.6, 19877.6, 19927.6, 19977.6, 20077.6]

        return block_dist[idx]

    def traveled_enough(self, sug_auth: int, cmd_auth: int, idx: int) -> bool:
        if self.pos_start != 0:
            traveled = sug_auth - cmd_auth + self.dist_to_EOB(self.pos_start)
        else:
            traveled = sug_auth - cmd_auth
        if traveled > self.dist_to_EOB(idx):
            return True
        else:
            return False
    
    def traveled_enough_per_train(self, sug_auth: int, cmd_auth: int, idx: int, pos_start: int) -> bool:
        """Check if train has traveled enough to move to next block."""
        if pos_start != 0:
            traveled = sug_auth - cmd_auth + self.dist_to_EOB(pos_start)
        else:
            traveled = sug_auth - cmd_auth
        
        dist_to_eob = self.dist_to_EOB(idx)
        result = traveled >= dist_to_eob  # Changed from > to >= to handle exact match
        
        print(f"[Wayside traveled_enough] sug_auth={sug_auth}, cmd_auth={cmd_auth}, idx={idx}, pos_start={pos_start}")
        print(f"[Wayside traveled_enough] traveled={traveled}, dist_to_EOB={dist_to_eob}, result={result}")
        
        return result

    def get_next_block(self, current_block: int, block_idx: int):
        # Don't modify occupancy here - track model manages it based on train position
        
        if current_block == 151:
            self.idx = 0
            return -1
        else:
            return self.green_order[block_idx + 1]


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
            try:
                with open(self.ctc_comm_file, 'r') as f:
                    data = json.load(f)
                    self.active_trains = data.get("Trains", {})
                    self.closed_blocks = data.get("Block Closure", [])
                    self.ctc_sugg_switches = data.get("Switch Suggestion", [])
            except (json.JSONDecodeError, FileNotFoundError):
                return
            
            

    def load_inputs_track(self):
        #read track to wayside json file
        with self.file_lock:
            try:
                with open(self.track_comm_file, 'r') as f:
                    data = json.load(f)
                    self.occupied_blocks = data.get("G-Occupancy", [0]*152)
                    self.input_faults = data.get("G-Failures", [0]*152*3)
                    
                    # Read train positions from track model
                    # Track model generates positions based on commanded speed/authority
                    train_positions = data.get("G-Train Positions", [0,0,0,0,0])
                    
                    # Update positions for trains in cmd_trains
                    for i, train_name in enumerate(["Train 1", "Train 2", "Train 3", "Train 4", "Train 5"]):
                        if train_name in self.cmd_trains and i < len(train_positions):
                            new_pos = train_positions[i]
                            if new_pos > 0 and new_pos != self.cmd_trains[train_name]["pos"]:
                                # Update position and index
                                try:
                                    new_idx = self.green_order.index(new_pos)
                                    old_pos = self.cmd_trains[train_name]["pos"]
                                    self.cmd_trains[train_name]["pos"] = new_pos
                                    self.cmd_trains[train_name]["idx"] = new_idx
                                    print(f"[Wayside] Track Model moved {train_name} from block {old_pos} to {new_pos}")
                                except ValueError:
                                    pass  # Position not in green_order
                    
            except (json.JSONDecodeError, FileNotFoundError):
                # If file is empty or corrupted, skip this update cycle
                return
        
     
    def load_track_outputs(self):
        with self.file_lock:
            try:
                with open(self.track_comm_file, 'r') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                # If file is empty or corrupted, skip this update cycle
                return

            # Update switch, light, and gate states
            data["G-switches"] = self.switch_states
            data["G-lights"] = self.light_states
            data["G-gates"] = self.gate_states

            # Don't overwrite occupancy - track model manages it based on train positions

            # for i in range (5):
                #     try:
                #         train_id = list(self.cmd_trains.keys())[i]
                #         data["G-Commanded Authority"][i] = self.cmd_trains[train_id]["cmd auth"]
                #         data["G-Commanded Speed"][i] = self.cmd_trains[train_id]["cmd speed"]
                #     except IndexError:
                #         data["G-Commanded Authority"][i] = 0
                #         data["G-Commanded Speed"][i] = 0   
            if "Train 1" in self.cmd_trains:
                a = self.cmd_trains["Train 1"]["cmd auth"]
                b = self.cmd_trains["Train 1"]["cmd speed"]
                data["G-Commanded Authority"] = [a,0,0,0,0]
                data["G-Commanded Speed"] = [b,0,0,0,0]
            else:
                data["G-Commanded Authority"] = [0,0,0,0,0]
                data["G-Commanded Speed"] = [0,0,0,0,0]
                

            

            # Now rewrite cleanly (overwrite file)
            with open(self.track_comm_file, 'w') as f:
                json.dump(data, f, indent=4)

            

    def load_ctc_outputs(self):
        pass

    def get_block_length(self, idx: int) -> float:
        """Get the length of a block in feet based on its index in green_order."""
        # Block lengths in feet (based on dist_to_EOB cumulative distances)
        block_lengths = [100, 100, 100, 200, 200, 100, 100, 100, 100, 100, 100, 100, 100, 100, 
                        300, 300, 300, 300, 300, 300, 300, 300, 300, 100, 86.6, 
                        100, 75, 75, 75, 75, 75, 75, 75, 75, 
                        75, 75, 75, 75, 300, 300, 300, 300, 300, 
                        300, 300, 300, 300, 75, 35, 100, 100, 80, 
                        100, 100, 90, 100, 100, 100, 100, 100, 100, 
                        162, 100, 100, 50, 50, 40, 50, 50, 
                        50, 50, 50, 50, 50, 50, 50, 
                        50, 50, 50, 50, 50, 50, 50, 
                        50, 50, 50, 50, 50, 50, 50, 
                        50, 50, 184, 40, 35, 50, 50, 100, 
                        200, 300, 300, 300, 300, 150, 150, 150, 
                        150, 150, 150, 150, 150, 100, 100, 100, 
                        100, 100, 100, 100, 100, 100, 100, 100, 
                        100, 150, 150, 150, 150, 150, 150, 150, 
                        150, 300, 300, 300, 300, 200, 100, 50, 
                        50, 50, 50, 50, 50, 50, 50, 
                        50, 50, 50, 50, 50, 50, 50, 
                        50, 50, 50, 50, 50, 50, 50, 
                        50, 50, 50, 50, 50, 50, 50, 
                        50, 50, 50, 100]
        
        if 0 <= idx < len(block_lengths):
            return block_lengths[idx]
        return 100.0  # Default to 100 ft if index out of range
    
    def update_train_position_in_track(self, train_name: str, position: int):
        """Update train position in track model JSON."""
        with self.file_lock:
            try:
                with open(self.track_comm_file, 'r') as f:
                    data = json.load(f)
                
                # Update position for this train
                train_num = int(train_name.split()[-1]) - 1  # "Train 1" -> 0
                if "G-Train Positions" in data and 0 <= train_num < len(data["G-Train Positions"]):
                    data["G-Train Positions"][train_num] = position
                    print(f"[Wayside] Updated {train_name} position in track model: {position}")
                
                with open(self.track_comm_file, 'w') as f:
                    json.dump(data, f, indent=4)
                    
            except (json.JSONDecodeError, FileNotFoundError):
                pass

    def write_initial_train_position_to_track(self, train_name: str, position: int):
        """Write initial train position to track model JSON so it knows where to start."""
        with self.file_lock:
            try:
                with open(self.track_comm_file, 'r') as f:
                    data = json.load(f)
                
                # Initialize positions array if it doesn't exist
                if "G-Train Positions" not in data:
                    data["G-Train Positions"] = [0, 0, 0, 0, 0]
                
                # Set position for this train (Train 1 = index 0, etc.)
                train_num = int(train_name.split()[-1]) - 1  # "Train 1" -> 0
                if 0 <= train_num < len(data["G-Train Positions"]):
                    data["G-Train Positions"][train_num] = position
                    print(f"[Wayside] Initialized {train_name} position in track model: {position}")
                
                with open(self.track_comm_file, 'w') as f:
                    json.dump(data, f, indent=4)
                    
            except (json.JSONDecodeError, FileNotFoundError):
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

        # Check bounds before accessing occupied_blocks and input_faults
        if 0 <= block_id < len(self.occupied_blocks):
            occupied = self.occupied_blocks[block_id] == 1
        else:
            occupied = False
        
        # Check bounds for faults (need 3 slots per block)
        if 0 <= block_id * 3 + 2 < len(self.input_faults):
            if self.input_faults[block_id*3] == 1:
                failure = 1
            elif self.input_faults[block_id*3+1] == 1:
                failure = 2
            elif self.input_faults[block_id*3+2] == 1:
                failure = 3
            else:
                failure = 0
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
