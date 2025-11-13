class DynamicBlockManager:
    def __init__(self):
        self.line_states = {"Green": {}, "Red": {}}

    def initialize_blocks(self, line_name, block_ids):
        """Create empty storage for blocks."""
        for block_id in block_ids:
            self.line_states[line_name][block_id] = {
                "temperature": 72,
                "failures": {"power": False, "circuit": False, "broken": False},
                "occupancy": False,
                "commanded_speed": 0,
                "commanded_authority": 0,
                "light": 0,
                "gate": "N/A",
                "switch_position": "N/A",
            }

    def write_inputs(self, line_name, switches, gates, lights, occupancy, failures):
        """Write arrays from JSON to storage."""
        if line_name not in self.line_states or not self.line_states[line_name]:
            return

        blocks = sorted(self.line_states[line_name].keys())

        for idx, block_id in enumerate(blocks):
            if idx < len(occupancy):
                self.line_states[line_name][block_id]["occupancy"] = occupancy[idx] == 1

            if idx < len(lights):
                self.line_states[line_name][block_id]["light"] = lights[idx]

            if idx < len(gates):
                self.line_states[line_name][block_id]["gate"] = gates[idx]

            if idx < len(switches):
                self.line_states[line_name][block_id]["switch_position"] = switches[idx]

            failure_idx = idx * 3
            if failure_idx + 2 < len(failures):
                self.line_states[line_name][block_id]["failures"]["power"] = (
                    failures[failure_idx] == 1
                )
                self.line_states[line_name][block_id]["failures"]["circuit"] = (
                    failures[failure_idx + 1] == 1
                )
                self.line_states[line_name][block_id]["failures"]["broken"] = (
                    failures[failure_idx + 2] == 1
                )

    def update_temperature(self, line_name, block_id, temperature):
        """Write temperature."""
        self.line_states[line_name][block_id]["temperature"] = temperature

    def update_failures(self, line_name, block_id, power, circuit, broken):
        """Write failures."""
        self.line_states[line_name][block_id]["failures"]["power"] = power
        self.line_states[line_name][block_id]["failures"]["circuit"] = circuit
        self.line_states[line_name][block_id]["failures"]["broken"] = broken

    def get_block_dynamic_data(self, line_name, block_id):
        """Read data."""
        if block_id not in self.line_states[line_name]:
            return None

        state = self.line_states[line_name][block_id]
        light_map = {0: "Red", 1: "Green"}

        return {
            "temperature": state["temperature"],
            "occupancy": state["occupancy"],
            "commanded_authority": state["commanded_authority"],
            "commanded_speed": state["commanded_speed"],
            "traffic_light": light_map.get(state["light"], "OFF"),
            "gate": state["gate"],
            "failures": state["failures"],
            "switch_position": state["switch_position"],
        }
