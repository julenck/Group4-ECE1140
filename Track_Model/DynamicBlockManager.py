class DynamicBlockManager:
    def __init__(self):
        self.line_states = {"Green": {}, "Red": {}}
        self.passengers_boarding_data = {}
        self.total_ticket_sales = 0
        self.trains = []

    def initialize_blocks(self, line_name, block_ids):
        """Create empty storage for blocks."""
        for block_id in block_ids:
            self.line_states[line_name][block_id] = {
                "temperature": 72,
                "failures": {"power": False, "circuit": False, "broken": False},
                "occupancy": False,
                "light": 0,
                "gate": "N/A",
                "switch_position": "N/A",
            }

    def write_inputs(self, line_name, switches, gates, lights):
        """Write arrays from JSON to storage."""
        if line_name not in self.line_states or not self.line_states[line_name]:
            return

        blocks = sorted(self.line_states[line_name].keys())

        for idx, block_id in enumerate(blocks):

            if idx < len(lights):
                self.line_states[line_name][block_id]["light"] = lights[idx]

            if block_id in gates:
                self.line_states[line_name][block_id]["gate"] = gates[block_id]

            if block_id in switches:
                self.line_states[line_name][block_id]["switch_position"] = switches[
                    block_id
                ]

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
        light_map = {0: "Super Green", 1: "Green", 2: "Yellow", 3: "Red"}

        return {
            "temperature": state["temperature"],
            "occupancy": state["occupancy"],
            "traffic_light": light_map.get(state["light"], "OFF"),
            "gate": state["gate"],
            "failures": state["failures"],
            "switch_position": state["switch_position"],
        }

    def get_switch_position(self, line_name, block_id):
        """Get switch position for specific block."""
        if block_id not in self.line_states[line_name]:
            return "N/A"
        return self.line_states[line_name][block_id]["switch_position"]

    def number_of_passengers_boarding(
        self, train_id: int, station_name: str, value: int
    ):
        """Store passengers boarding for a specific train at a station."""
        if train_id not in self.passengers_boarding_data:
            self.passengers_boarding_data[train_id] = {}
        self.passengers_boarding_data[train_id][station_name] = value

    def number_of_ticket_sales(self, total_value: int):
        """Store cumulative ticket sales."""
        self.total_ticket_sales = total_value

    def get_passengers_boarding(self, train_id: int, station_name: str) -> int:
        """Retrieve passengers boarding for a specific train at a station."""
        if train_id in self.passengers_boarding_data:
            return self.passengers_boarding_data[train_id].get(station_name, 0)
        return 0
