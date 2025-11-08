

import json
import os
from Green_Line_PLC_XandLup import process_states_green_xlup
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
        self.output_data: dict = {}
        self.active_plc: str = plc
        self.ctc_comm_file: str = "ctc_to_wayside.json"
        self.track_comm_file: str = "track_to_wayside.json"
        self.block_status: list = []
        self.detected_faults: dict = {}
        self.input_faults: dict = {}
        self.blocks_with_switches: list = [13,28,57,63,77,85]
        self.blocks_with_lights: list = [0,3,7,29,58,62,76,86,100,101,150,151]
        self.blocks_with_gates: list = [19,108]



        # Start PLC processing loop
        self.run_plc()

    # Methods

    def run_plc(self):
        #call plc function
        if self.active_plc != "":
            self.load_inputs_track()
            if self.active_plc == "Green_Line_PLC_XandLup.py":
                switches, signals, crossing = process_states_green_xlup(self.occupied_blocks)
                self.switch_states[0:3] = switches
                self.light_states[0:11]=signals[0:11]
                self.light_states[20:23]=signals[12:15]
                self.gate_states[0]=crossing[0]
            threading.Timer(0.2, self.run_plc).start()
            
    def override_light(self, block_id: int, state: int):
        pass

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
        pass

    def load_inputs_track(self):
        pass
     
    def load_track_outputs(self):
        pass

    def load_ctc_outputs(self):
        pass

    def get_block_data(self, block_id: int):
        
        if block_id in self.blocks_with_switches:
            switch_state = self.switch_states[self.blocks_with_switches.index(block_id)]
        else:
            switch_state = "N/A"
        if block_id in self.blocks_with_lights:
            light_state = self.light_states[self.blocks_with_lights.index(block_id)]
        else:
            light_state = "N/A"
        if block_id in self.blocks_with_gates:
            gate_state = self.gate_states[self.blocks_with_gates.index(block_id)]
        else:
            gate_state = "N/A"
        desired = {
            "block_id": block_id,
            "occupied": False,
            "switch_state": switch_state,
            "light_state": light_state,
            "gate_state": gate_state,
            "Failure:": 0
        }
        return desired

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
