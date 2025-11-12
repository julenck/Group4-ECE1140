import json
import os


class DynamicBlockManager:
    def __init__(self, line_name, static_data):
        self.line_name = line_name
        self.static_data = static_data
        self.json_path = "track_model_Track_Controller.json"

        # Internal state per block
        self.block_states = {}

        # Initialize state for each block
        for block_data in static_data:
            block_id = (
                f"{block_data['Section']}{int(float(block_data['Block Number']))}"
            )
            self.block_states[block_id] = {
                "temperature": 72,
                "failures": {"power": False, "circuit": False, "broken": False},
                "occupancy": False,
                "raw_light": 0,
                "raw_gate": "N/A",
                "switch_position": "N/A",
            }

    def poll_inputs(self):
        """Read JSON inputs once and update storage. Called by Main UI every 500ms."""
        if not os.path.exists(self.json_path):
            return

        try:
            with open(self.json_path, "r") as f:
                data = json.load(f)

            inputs = data.get("Inputs", {})
            prefix = self.line_name[0]  # "G" or "R"

            # Read input arrays
            switches = inputs.get(f"{prefix}-switches", [])
            gates = inputs.get(f"{prefix}-gates", [])
            lights = inputs.get(f"{prefix}-lights", [])
            occupancy = inputs.get(f"{prefix}-Occupancy", [])

            # Update each block's state from arrays
            for block_id, state in self.block_states.items():
                block_idx = self._get_block_index(block_id)
                if block_idx is None:
                    continue

                # Update occupancy (1-to-1 mapping: block index → occupancy index)
                if block_idx < len(occupancy):
                    state["occupancy"] = occupancy[block_idx] == 1

                # Update light (TODO: need mapping - not all blocks have lights)
                if block_idx < len(lights):
                    state["raw_light"] = lights[block_idx]

                # Update gate (TODO: need mapping - only some blocks have gates)
                state["raw_gate"] = "N/A"

                # Update switch (TODO: need mapping - only branch blocks have switches)
                state["switch_position"] = "N/A"

        except Exception as e:
            print(f"Error loading data: {e}")

    def get_block_dynamic_data(self, block_id):
        """Get all dynamic data for a block from storage."""
        if block_id not in self.block_states:
            return None

        state = self.block_states[block_id]
        failures = state["failures"]

        # Calculate traffic light with failure logic
        traffic_light = self._calculate_traffic_light(block_id, state)

        # Calculate gate with failure logic
        gate_status = self._calculate_gate(block_id, state)

        # Calculate heating
        temp = state["temperature"]
        heating_on = temp < 32

        return {
            "temperature": temp,
            "heating_on": heating_on,
            "failures": failures,
            "occupancy": state.get("occupancy", False),
            "traffic_light": traffic_light,
            "gate": gate_status,
            "switch_position": state.get("switch_position", "N/A"),
            "commanded_speed": "N/A",  # TODO: per-train, not per-block
            "commanded_authority": "N/A",  # TODO: per-train, not per-block
        }

    def _calculate_traffic_light(self, block_id, state):
        """Apply failure logic to determine effective traffic light."""
        failures = state["failures"]
        raw_light = state.get("raw_light", 0)

        # Convert array value to color (0=Red, 1=Green, 2=Yellow)
        light_map = {0: "Red", 1: "Green", 2: "Yellow"}
        light_input = light_map.get(raw_light, "N/A")

        if failures["power"]:
            return "OFF"

        if failures["circuit"]:
            # TODO: Need authority to determine Green vs Red
            return "Green"

        if failures["broken"]:
            return "Red"

        return light_input

    def _calculate_gate(self, block_id, state):
        """Apply failure + crossing logic to determine gate status."""
        failures = state["failures"]

        # Check if this block has a crossing from static data
        has_crossing = False
        for block_data in self.static_data:
            bid = f"{block_data['Section']}{int(float(block_data['Block Number']))}"
            if bid == block_id:
                has_crossing = block_data.get("Crossing") == "Yes"
                break

        if not has_crossing:
            return "N/A"

        # Apply failure logic
        if failures["power"]:
            return "Closed"

        if failures["circuit"]:
            return "Open"

        if failures["broken"]:
            return "Closed"

        # Otherwise use raw input (TODO: read from gates array when we have mapping)
        return "Open"

    def set_temperature(self, selected_block, temp):
        """Set temperature for a block in storage - INTERNAL ONLY."""
        if selected_block not in self.block_states:
            return

        self.block_states[selected_block]["temperature"] = temp

    def set_failures(self, selected_block, power, circuit, broken):
        """Set failures for a block in storage and write to JSON Outputs."""
        if selected_block not in self.block_states:
            return

        # Update internal state
        self.block_states[selected_block]["failures"] = {
            "power": power,
            "circuit": circuit,
            "broken": broken,
        }

        # Write to JSON
        if not os.path.exists(self.json_path):
            return
        try:
            with open(self.json_path, "r") as f:
                data = json.load(f)

            # Ensure structure exists
            if "Outputs" not in data:
                data["Outputs"] = {}

            prefix = self.line_name[0]  # "G" or "R"
            failures_key = f"{prefix}-Failures"

            if failures_key not in data["Outputs"]:
                num_blocks = len(self.block_states)
                data["Outputs"][failures_key] = [0] * (num_blocks * 3)

            # Find block index
            block_index = self._get_block_index(selected_block)
            if block_index is None:
                return

            # Update the 3 values for this block
            base_idx = block_index * 3
            data["Outputs"][failures_key][base_idx] = 1 if power else 0
            data["Outputs"][failures_key][base_idx + 1] = 1 if circuit else 0
            data["Outputs"][failures_key][base_idx + 2] = 1 if broken else 0

            with open(self.json_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error writing failures: {e}")

    def _get_block_index(self, block_id):
        """Get sequential index of block (A1=0, A2=1, etc.)."""
        sorted_blocks = sorted(self.block_states.keys())
        try:
            return sorted_blocks.index(block_id)
        except ValueError:
            return None
