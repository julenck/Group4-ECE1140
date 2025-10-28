

class sw_vital_check:
    def __init__(self):
        pass

    def verify_light_change(self, curr_state: list, block_id: int, desired_state: int):
        return True

    def check_light(self, state1: int, state2: int):
        return True

    def verify_switch_change(self, curr_state: list, block_id: int, desired_state: int):
        return True

    def check_switch(self, state1: int, state2: int):
        return True

    def verify_gate_change(self, curr_state: list, block_id: int, desired_state: int):
        return True

    def check_gate(self, state1: int, state2: int):
        return True

    def verify_file(self, filename: str):
        return True

    def check_file(self, filename: str):
        return True