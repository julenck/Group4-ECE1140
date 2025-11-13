

import json
import os
from Green_Line_PLC_XandLup import process_states_green_xlup
from Green_Line_PLC_XandLdown import process_states_green_xldown
import threading


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
        self.track_comm_file: str = "track_to_wayside.json"
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
                if self.active_trains[train]["Train Position"] != 0:
                    self.cmd_trains[train] = {
                    "cmd auth": self.active_trains[train]["Suggested Authority"],
                    "cmd speed": self.active_trains[train]["Suggested Speed"],
                    "pos": self.active_trains[train]["Train Position"]

                }
                    self.pos_start = self.active_trains[train]["Train Position"] 
                else:
                    self.cmd_trains[train] = {
                        "cmd auth": self.active_trains[train]["Suggested Authority"],
                        "cmd speed": self.active_trains[train]["Suggested Speed"],
                        "pos": 0
                    }
                    self.pos_start = 0
                
                

        ttr = []
        for cmd_train in self.cmd_trains:
            auth = self.cmd_trains[cmd_train]["cmd auth"]
            speed = self.cmd_trains[cmd_train]["cmd speed"]
            pos = self.cmd_trains[cmd_train]["pos"]
            
            
            auth = auth - speed
            
            if auth <= 0:
                auth = 0
                # Don't set Active to 0 here - let CTC manage the Active state
                # Only remove from cmd_trains to stop processing
                ttr.append(cmd_train)
            
            self.cmd_trains[cmd_train]["cmd auth"] = auth
            self.cmd_trains[cmd_train]["cmd speed"] = speed
            sug_auth = self.active_trains[cmd_train]["Suggested Authority"]


            if (self.traveled_enough(sug_auth, auth, self.idx)):
                self.cmd_trains[cmd_train]["pos"] = self.get_next_block(pos, self.idx)
                self.idx += 1


            with self.file_lock:
                with open(self.ctc_comm_file,'r') as f:
                    data = json.load(f)
                with open(self.ctc_comm_file,'w') as f:
                    data["Trains"][cmd_train]["Train Position"] = self.cmd_trains[cmd_train]["pos"]
                    json.dump(data,f,indent=4)

        for tr in ttr:
            self.cmd_trains.pop(tr)

        if self.running:
            threading.Timer(1.0, self.run_trains).start()


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
            traveled = sug_auth - cmd_auth + self.dist_to_EOB(self.green_order.index(self.pos_start))
        else:
            traveled = sug_auth - cmd_auth
        if traveled > self.dist_to_EOB(idx):
            return True
        else:
            return False

    def get_next_block(self, current_block: int, block_idx: int):

        self.occupied_blocks[current_block] = 0
        

        
        
        if current_block == 151:
            self.idx = 0
            return -1
        else:
            self.occupied_blocks[self.green_order[block_idx + 1]] = 1
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

            if self.cmd_trains != {}:
                for i in range (5):
                    try:
                        train_id = list(self.cmd_trains.keys())[i]
                        data["G-Commanded Authority"][i] = self.cmd_trains[train_id]["cmd auth"]
                        data["G-Commanded Speed"][i] = self.cmd_trains[train_id]["cmd speed"]
                    except IndexError:
                        data["G-Commanded Authority"][i] = 0
                        data["G-Commanded Speed"][i] = 0
            else:
                data["G-Commanded Authority"] = [0]*5
                data["G-Commanded Speed"] = [0]*5

            

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
