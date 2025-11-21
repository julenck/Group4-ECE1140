class DynamicBlockManager:
    def __init__(self):
        self.line_states = {"Green": {}, "Red": {}}
        self.passengers_boarding = 0
        self.total_ticket_sales = 0
        self.trains = []

    def initialize_blocks(self, line_name, block_ids):
        """Create empty storage for blocks."""
        for block_id in block_ids:
            self.line_states[line_name][block_id] = {
                "failures": {"power": False, "circuit": False, "broken": False},
                "occupancy": True,
                "light": 0,
                "gate": "N/A",
                "switch_position": "N/A",
                "direction": "N/A",
            }

    def write_inputs(self, line_name, switches, gates, lights):
        """Write arrays from JSON to storage."""
        if line_name not in self.line_states or not self.line_states[line_name]:
            return
        blocks = self.line_states[line_name].keys()

        for idx, block_id in enumerate(blocks):

            if idx < len(lights):
                self.line_states[line_name][block_id]["light"] = lights[idx]

            # Extract numeric block number
            block_num = int("".join(filter(str.isdigit, block_id)))

            if block_num in switches:
                self.line_states[line_name][block_id]["gate"] = switches[block_num]

            if block_num in gates:
                self.line_states[line_name][block_id]["switch_position"] = gates[
                    block_num
                ]

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
        light_map = {0: "Super Green", 1: "Green", 2: "Yellow", 3: "Red"}

        return {
            "occupancy": state["occupancy"],
            "traffic_light": light_map.get(state["light"], "ON"),
            "gate": state["gate"],
            "failures": state["failures"],
            "switch_position": state["switch_position"],
            "direction": state["direction"],
        }

    def get_switch_position(self, line_name, block):
        # If the caller gives a number, convert it to the actual stored key
        if isinstance(block, int):
            for block_id in self.line_states[line_name]:
                # Extract only digits from stored block_id
                digits = "".join(filter(str.isdigit, str(block_id)))
                if digits and int(digits) == block:
                    block = block_id
                    break

        # If still not found, return None
        if block in self.line_states[line_name]:
            return None

        return self.line_states[line_name][block]["switch_position"]
