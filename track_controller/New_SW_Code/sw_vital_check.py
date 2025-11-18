

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

    def verify_auth(self, all_trains: dict, train_id: int, auth: int):
        return True

    def check_auth(self, current_auth: int, desired_auth: int):
        return True
    
    def verify_speed(self, all_trains: dict, train_id: int, speed: int):
        return True
    
    def check_speed(self, current_speed: int, desired_speed: int):
        return True
    
    def verify_close(self, block_status: list, block_id: int):
        return True
    
    def verify_status(self):
        return True
    
    def verify_states(self):
        return True
    
