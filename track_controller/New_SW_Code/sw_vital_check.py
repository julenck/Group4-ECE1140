

class sw_vital_check:
    def __init__(self):
        # Threshold for speed verification (in m/s)
        self.speed_threshold = 0.5
        # Threshold for authority verification (in meters)
        self.auth_threshold = 1.0

    def verify_switch_change(self, switch_idx: int, desired_state: int, switch_states: list):
        """
        Verify that a switch change was successful.
        
        Args:
            switch_idx: Index of the switch in the switch_states array
            desired_state: The desired state (0 or 1)
            switch_states: The current switch states array
            
        Returns:
            True if switch state matches desired state, False otherwise
        """
        if switch_idx < 0 or switch_idx >= len(switch_states):
            return False
        
        actual_state = switch_states[switch_idx]
        return self.check_switch(actual_state, desired_state)

    def check_switch(self, actual_state: int, desired_state: int):
        """
        Compare actual switch state with desired state.
        
        Returns:
            True if states match, False otherwise
        """
        return actual_state == desired_state

    def verify_file(self, filename: str):
        return True

    def check_file(self, filename: str):
        return True

    def verify_auth(self, train_id: str, desired_auth: float, cmd_trains: dict):
        """
        Verify that authority command was set correctly for a train.
        
        Args:
            train_id: Train identifier (e.g., "Train 1")
            desired_auth: The desired authority value in meters
            cmd_trains: Dictionary of commanded trains with their data
            
        Returns:
            True if authority is within threshold of desired value, False otherwise
        """
        if train_id not in cmd_trains:
            return False
        
        actual_auth = cmd_trains[train_id].get("cmd auth", 0)
        return self.check_auth(actual_auth, desired_auth)

    def check_auth(self, actual_auth: float, desired_auth: float):
        """
        Compare actual authority with desired authority using threshold.
        
        Returns:
            True if difference is within threshold, False otherwise
        """
        return abs(actual_auth - desired_auth) <= self.auth_threshold
    
    def verify_speed(self, train_id: str, desired_speed: float, cmd_trains: dict):
        """
        Verify that speed command was set correctly for a train.
        
        Args:
            train_id: Train identifier (e.g., "Train 1")
            desired_speed: The desired speed value in m/s
            cmd_trains: Dictionary of commanded trains with their data
            
        Returns:
            True if speed is within threshold of desired value, False otherwise
        """
        if train_id not in cmd_trains:
            return False
        
        actual_speed = cmd_trains[train_id].get("cmd speed", 0)
        return self.check_speed(actual_speed, desired_speed)
    
    def check_speed(self, actual_speed: float, desired_speed: float):
        """
        Compare actual speed with desired speed using threshold.
        
        Returns:
            True if difference is within threshold, False otherwise
        """
        return abs(actual_speed - desired_speed) <= self.speed_threshold
    
    def verify_close(self, block_status: list, block_id: int):
        return True
    
    def verify_status(self):
        return True
    
    def verify_states(self):
        return True
    
