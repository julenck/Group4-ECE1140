

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
        self.ctc_comm_file: str = "C:\Users\CRK118\Desktop\Trains\Group4-ECE1140\ctc_track_controller.json"#"ctc_to_wayside.json"
        self.track_comm_file: str = "track_to_wayside.json"
        self.block_status: list = []
        self.detected_faults: dict = {}
        self.input_faults: list = []
        self.blocks_with_switches: list = [13,28,57,63,77,85]
        self.blocks_with_lights: list = [0,3,7,29,58,62,76,86,100,101,150,151]
        self.blocks_with_gates: list = [19,108]
        self.running: bool = True
        self.file_lock = threading.Lock()
        self.cmd_trains: dict = {}



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
                threading.Timer(0.2, self.run_plc).start()


    def run_trains(self):      
        if not self.running:
            return
        
        self.load_inputs_ctc()

        for train in self.active_trains:
            if train not in self.cmd_trains and self.active_trains[train]["Active"]==1:
                self.cmd_trains[train] = {
                    "cmd auth": self.active_trains[train]["Suggested Authority"],
                    "cmd speed": self.active_trains[train]["Suggested Speed"],
                    "pos": 0
                }

        ttr = []
        for cmd_train in self.cmd_trains:
            auth = self.cmd_trains[cmd_train]["cmd auth"]
            speed = self.cmd_trains[cmd_train]["cmd speed"]
            pos = self.cmd_trains[cmd_train]["pos"]
            auth = auth - speed
            if auth <= 0:
                auth = 0
                with self.file_lock:
                    with open(self.ctc_comm_file, 'r') as f:
                        data = json.load(f)
                    data["Trains"][cmd_train]["Active"] = 0
                    with open(self.ctc_comm_file, 'w') as f:
                        json.dump(data, f, indent=4)

                ttr.append(cmd_train)
            
            self.cmd_trains[cmd_train]["cmd auth"] = auth
            self.cmd_trains[cmd_train]["cmd speed"] = speed
            self.cmd_trains[cmd_train]["pos"] = pos + 1

        for tr in ttr:
            self.cmd_trains.pop(tr)

        if self.running:
            threading.Timer(1.0, self.run_trains).start()






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
                self.occupied_blocks = data.get("G-Occupancy", [0]*152)
                self.input_faults = data.get("G-Failures", [0]*152*3)
        
     
    def load_track_outputs(self):
        with self.file_lock:
            with open(self.track_comm_file, 'r') as f:
                data = json.load(f)

            # Update values


            data["G-switches"] = self.switch_states
            data["G-lights"] = self.light_states
            data["G-gates"] = self.gate_states

            if self.cmd_trains != {}:
                data["G-Trains"] = self.cmd_trains
            else:
                data["G-Trains"] = {}

            

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
