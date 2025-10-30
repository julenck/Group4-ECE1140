

import json
import os

class sw_wayside_controller:
    def __init__(self, vital):
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
        self.occupied_blocks: list = [0]*150
        self.light_states: list = [0]*24
        self.gate_states: list = [0,0]
        self.switch_states: list = [0]*6
        self.output_data: dict = {}
        self.active_plc: str = ""
        self.input_output_filename: str = ""
        self.block_status: list = []
        self.detected_faults: dict = {}
        self.input_faults: dict = {}

    # Methods
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
        
        example = {
            "block_id": block_id,
            "occupied": False,
            "switch_state": 0,
            "light_state": "GREEN",
            "gate_state": 0,
            "Failure:": 0
        }
        return example

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
