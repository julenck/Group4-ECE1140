

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
        self.active_trains: dict = {}
        self.occupied_blocks: list = []
        self.light_states: list = []
        self.gate_states: list = []
        self.switch_states: list = []
        self.output_data: dict = {}
        self.active_plc: str = ""
        self.input_output_filename: str = ""

    # Methods
    def override_light(self, block_id: int, state: int):
        pass

    def override_gate(self, block_id: int, state: int):
        pass

    def override_switch(self, block_id: int, state: int):
        pass

    def load_plc(self, filename: str):
        pass

    def change_plc(self, result: bool, filename: str):
        pass

    def load_inputs(self):
        pass

    def generate_outputs(self, inputs: dict):
        pass

    def get_block_data(self, block_id: int):
        pass
