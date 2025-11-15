"""
Line Network - Defines train paths and topology for Red and Green lines
Knows how trains move through the network and provides visualization info
"""

import pandas as pd
import re
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
import json


def parse_branching_connections(value: str) -> List[Tuple[int, int]]:
    """Parse SWITCH (A-B; C-D) format into connection pairs."""
    text = str(value).upper().strip()
    if "SWITCH TO YARD" in text or "SWITCH FROM YARD" in text:
        return []
    if "SWITCH" not in text:
        return []

    m = re.search(r"\(([^)]+)\)", text)
    if not m:
        return []

    inside = m.group(1)
    connections = []

    parts = re.split(r"[;,]", inside)
    for part in parts:
        part = part.strip()
        conn_match = re.search(r"(\d+)\s*-\s*(\d+)", part)
        if conn_match:
            from_block = int(conn_match.group(1))
            to_block = int(conn_match.group(2))
            connections.append((from_block, to_block))

    return connections


@dataclass
class Path:
    """Represents a train path through the network."""

    name: str
    blocks: List[int]

    def __repr__(self):
        return f"Path({self.name}: {len(self.blocks)} blocks)"


@dataclass
class BranchPoint:
    """A point where track splits."""

    block: int
    targets: List[int]

    def __repr__(self):
        return f"BranchPoint(block={self.block}, targets={self.targets})"


class LineNetwork:
    """Network for a specific line (Red or Green)."""

    def __init__(self, line_name: str, block_manager=None):
        self.line_name = line_name.replace(" Line", "")
        self.connections: Dict[int, List[int]] = {}  # block -> list of connected blocks
        self.branch_points: Dict[int, BranchPoint] = {}
        self.block_manager = block_manager
        self.additional_connections: List[Tuple[int, int]] = (
            []
        )  # non-sequential to draw
        self.skip_connections: List[Tuple[int, int]] = []  # exceptions not to draw
        self.all_blocks = []
        self.crossing_blocks = []

    def get_red_line_visualizer_info(
        self,
    ) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """Return (additional_connections, skip_connections) for red line."""
        return (self.additional_connections, self.skip_connections)

    def get_green_line_visualizer_info(
        self,
    ) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """Return (additional_connections, skip_connections) for green line."""
        return (self.additional_connections, self.skip_connections)

    def __repr__(self):
        return f"LineNetwork({self.line_name}: {len(self.connections)} blocks)"

    def read_train_data_from_json(
        self, json_path: str = "track_model_Track_controller.json"
    ):
        """Read ALL train control data from JSON file."""
        try:
            with open(json_path, "r") as f:
                data = json.load(f)

            # Determine prefix based on line
            prefix = self.line_name[0]  # "G" for Green, "R" for Red

            # Parse arrays from JSON
            switches = data.get(f"{prefix}-switches", [])
            gates = data.get(f"{prefix}-gates", [])
            lights = data.get(f"{prefix}-lights", [])
            commanded_speeds = data.get(f"{prefix}-commanded-speed", [])
            commanded_authorities = data.get(f"{prefix}-commanded-authority", [])
            occupancy = data.get(f"{prefix}-Occupancy", [])
            failures = data.get(f"{prefix}-Failures", [])

            data_dict = {
                "switches": switches,
                "gates": gates,
                "lights": lights,
                "commanded_speeds": commanded_speeds,
                "commanded_authorities": commanded_authorities,
                "occupancy": occupancy,
                "failures": failures,
            }

            # Write parsed data to block manager
            self.write_to_block_manager(data_dict)

            # Find occupied block and write to Train Model JSON
            commanded_speed_value = 0
            commanded_authority_value = 0

            for idx, occ in enumerate(occupancy):
                if occ == 1:  # Block is occupied
                    if idx < len(commanded_speeds):
                        commanded_speed_value = commanded_speeds[idx]
                    if idx < len(commanded_authorities):
                        commanded_authority_value = commanded_authorities[idx]
                    break  # Assuming only one train, stop at first occupied block

            # Write to Train Model JSON
            train_model_data = {
                "block": {
                    "commanded speed": commanded_speed_value,
                    "commanded authority": commanded_authority_value,
                },
                "beacon": {
                    "speed limit": 0,
                    "side_door": "N/A",
                    "current station": "N/A",
                    "next station": "N/A",
                    "passengers_boarding": 0,
                    "passengers_onboard": 0,
                },
            }

            with open("track_model_Train_Model.json", "w") as f:
                json.dump(train_model_data, f, indent=4)

            return data_dict

        except Exception as e:
            print(f"Error reading JSON: {e}")
            return None

    def check_failures(self, failures: List[int], current_block: int) -> bool:
        """Check if any failures prevent movement at current block."""
        if current_block not in self.all_blocks:
            return True

        block_idx = self.all_blocks.index(current_block)
        failure_idx = block_idx * 3

        if failure_idx + 2 < len(failures):
            power_fail = failures[failure_idx] == 1
            circuit_fail = failures[failure_idx + 1] == 1
            broken_fail = failures[failure_idx + 2] == 1

            if any([power_fail, circuit_fail, broken_fail]):
                print(f"[TRAIN] Stopped at block {current_block} due to failures")
                return False
        return True

    def write_to_block_manager(self, data: dict):
        """Parse raw JSON data and write to block manager."""
        if not self.block_manager:
            return

        # Extract raw arrays
        switches = data["switches"]
        gates = data["gates"]
        lights = data["lights"]
        failures = data["failures"]

        # Parse switches using existing method
        switch_positions = self.process_switch_positions(switches)

        # Parse gates: map crossing_blocks to gate array
        gate_statuses = {}
        for i, block_num in enumerate(self.crossing_blocks):
            if i < len(gates):
                gate_statuses[block_num] = "Open" if gates[i] == 0 else "Closed"

        # Parse traffic lights for ALL blocks using existing method
        parsed_lights = []
        for block_num in self.all_blocks:
            light_status = self.parse_traffic_lights(block_num, lights)
            # Convert to int: Super Green=0, Green=1, Yellow=2, Red=3
            if light_status == "Super Green":
                parsed_lights.append(0)
            elif light_status == "Green":
                parsed_lights.append(1)
            elif light_status == "Yellow":
                parsed_lights.append(2)
            elif light_status == "Red":
                parsed_lights.append(3)

        # Write to block manager
        self.block_manager.write_inputs(
            self.line_name,
            switch_positions,
            gate_statuses,
            parsed_lights,
            failures,
        )

    def check_gates(self, gates: List[int], current_block: int) -> bool:
        """Check if gate is closed at current block's crossing."""
        if current_block in self.crossing_blocks:
            crossing_index = self.crossing_blocks.index(current_block)
            if crossing_index < len(gates) and gates[crossing_index] == 1:
                print(f"[TRAIN] Stopped at block {current_block} due to closed gate")
                return False
        return True

    def process_switch_positions(self, switches: List[int]) -> Dict[int, int]:
        """Convert switch array to block->target mapping based on branch points."""
        switch_positions = {}
        for block_num, branch_point in self.branch_points.items():
            branch_index = list(self.branch_points.keys()).index(block_num)
            if branch_index < len(switches):
                switch_setting = switches[branch_index]
                targets = branch_point.targets
                if 0 <= switch_setting < len(targets):
                    switch_positions[block_num] = targets[switch_setting]
        return switch_positions

    def parse_traffic_lights(self, current_block: int, lights_array: List[int]) -> str:
        """
        Parse traffic light status for current block.
        Returns: "Super Green", "Green", "Yellow", or "Red"
        """
        # Hard-coded blocks with traffic lights
        traffic_light_blocks = [0, 3, 7, 29, 58, 62, 76, 86, 100, 101, 150, 151]

        # If current block doesn't have a traffic light, return Super Green
        if current_block not in traffic_light_blocks:
            return "Super Green"

        # Find which traffic light index this is (0-11)
        traffic_light_index = traffic_light_blocks.index(current_block)

        # Calculate bit position (2 bits per light)
        bit_index = traffic_light_index * 2

        # Read 2 bits
        if bit_index + 1 < len(lights_array):
            bit1 = lights_array[bit_index]
            bit2 = lights_array[bit_index + 1]

            # Decode: 00=Super Green, 01=Green, 10=Yellow, 11=Red
            if bit1 == 0 and bit2 == 0:
                return "Super Green"
            elif bit1 == 0 and bit2 == 1:
                return "Green"
            elif bit1 == 1 and bit2 == 0:
                return "Yellow"
            elif bit1 == 1 and bit2 == 1:
                return "Red"

        # Default to Super Green if parsing fails
        return "Super Green"

    def control_train_movement(
        self,
        current_block: int,
        json_path: str = "track_model_Track_controller.json",
    ) -> Dict:
        """Main control function - reads JSON and determines if train can move."""

        # Read all data from JSON
        train_data = self.read_train_data_from_json(json_path)
        if not train_data:
            return None

        # Extract data
        switches = train_data["switches"]
        gates = train_data["gates"]
        lights = train_data["lights"]
        commanded_speeds = train_data["commanded_speeds"]
        commanded_authorities = train_data["commanded_authorities"]
        occupancy = train_data["occupancy"]
        failures = train_data["failures"]

        # Process switch positions
        switch_positions = self.process_switch_positions(switches)

        # Check failures
        can_move_failures = self.check_failures(failures, current_block)

        # Check gates at current block
        can_move_gates = self.check_gates(gates, current_block)

        # Parse traffic light for current block
        light_status = self.parse_traffic_lights(current_block, lights)

        # Determine can_move and speed_factor based on light status
        if light_status == "Red":
            can_move_lights = False
            speed_factor = 0.0
            print(f"[TRAIN] Stopped at block {current_block} due to red light")
        elif light_status == "Yellow":
            can_move_lights = True
            speed_factor = 0.5
            print(f"[TRAIN] Slowing at block {current_block} due to yellow light")
        elif light_status == "Green":
            can_move_lights = True
            speed_factor = 0.75
        else:  # Super Green
            can_move_lights = True
            speed_factor = 1.0

        # Final decision
        can_move = can_move_failures and can_move_gates and can_move_lights

        return {
            "can_move": can_move,
            "speed_factor": speed_factor,
            "switch_positions": switch_positions,
            "occupancy": occupancy,
            "commanded_speeds": commanded_speeds,
            "commanded_authorities": commanded_authorities,
        }

    def get_next_block(self, current: int, previous: Optional[int] = None) -> int:
        # Special case: if previous equals current, stay put
        if previous == current:
            return current

        # Special case: if at block 57 coming from 56, stay at 57
        if current == 57 and previous == 56:
            return current

        # Special case: starting from yard
        if current == 0 and previous is None:
            next_block = 57
            self.update_block_occupancy(next_block, current)
            return next_block

        # Get control data
        control_data = self.control_train_movement(current)
        if not control_data:
            return current

        can_move = control_data["can_move"]
        switch_positions = control_data["switch_positions"]

        # If can't move, stay at current block
        if not can_move:
            return current

        # Determine if we're going forward or backward
        going_forward = previous is None or previous < current

        # Only use switch if going forward
        if going_forward and switch_positions and current in switch_positions:
            target = switch_positions[current]
            if target == 0:
                self.update_block_occupancy(target, current)
                return target
            if current in self.connections and target in self.connections[current]:
                self.update_block_occupancy(target, current)
                return target

        # Get available connections
        if current not in self.connections:
            return current

        available = list(self.connections[current])

        # Remove previous block
        if previous is not None and previous in available:
            available.remove(previous)

        if not available:
            # Dead end - reverse
            if previous is not None:
                self.update_block_occupancy(previous, current)
                return previous
            return current

        # Prefer forward if going forward, backward if going backward
        if going_forward and current + 1 in available:
            next_block = current + 1
            self.update_block_occupancy(next_block, current)
            return next_block
        elif not going_forward and current - 1 in available:
            next_block = current - 1
            self.update_block_occupancy(next_block, current)
            return next_block
        elif current + 1 in available:
            next_block = current + 1
            self.update_block_occupancy(next_block, current)
            return next_block
        elif current - 1 in available:
            next_block = current - 1
            self.update_block_occupancy(next_block, current)
            return next_block
        else:
            next_block = available[0]
            self.update_block_occupancy(next_block, current)
            return next_block

    def update_block_occupancy(
        self, current_block: int, previous_block: Optional[int] = None
    ):
        """Update occupancy in block manager when train moves."""
        if not self.block_manager:
            return

        print(
            f"[OCCUPANCY] Updating: current={current_block}, previous={previous_block}"
        )
        print(
            f"[OCCUPANCY] Available blocks: {list(self.block_manager.line_states.get(self.line_name, {}).keys())}"
        )

        # Clear all blocks first
        for block_id in self.block_manager.line_states.get(self.line_name, {}):
            self.block_manager.line_states[self.line_name][block_id][
                "occupancy"
            ] = False

        # Set current block as occupied
        # Find the block_id that matches current_block number
        for block_id in self.block_manager.line_states.get(self.line_name, {}):
            # block_id format is like "A1", "B23", etc.
            # Extract the number part and compare
            try:
                # Get number from block_id (everything after the first character which is the section letter)
                block_num_str = "".join(filter(str.isdigit, block_id))
                if block_num_str and int(block_num_str) == current_block:
                    self.block_manager.line_states[self.line_name][block_id][
                        "occupancy"
                    ] = True
                    print(
                        f"[OCCUPANCY] Set block {block_id} (block #{current_block}) as occupied"
                    )
                    break
            except (ValueError, AttributeError):
                continue


class LineNetworkBuilder:
    """Builds network for Red and Green lines."""

    def __init__(self, df: pd.DataFrame, line_name: str):
        self.df = df
        self.line_name = line_name
        self.network = LineNetwork(line_name)
        self.all_blocks = []
        self.switch_data = {}  # block -> list of all connections

    def build(self) -> LineNetwork:
        """Build the network."""
        print(f"\n=== Building {self.line_name} Network ===")

        # Step 1: Sequential foundation
        self._parse_blocks()

        # Step 2: Parse switches for branch points
        self._parse_switches()

        # Step 3: Parse crossings
        self._parse_crossings()

        # Step 4: Apply line-specific rules
        if self.line_name == "Red Line":
            self._build_red_line()
        elif self.line_name == "Green Line":
            self._build_green_line()

        print(f"✓ Built connection graph with {len(self.network.connections)} blocks")
        print(f"✓ Found {len(self.network.branch_points)} branch points")
        print(f"✓ Found {len(self.network.crossing_blocks)} crossing blocks")
        print("=== Build Complete ===\n")

        return self.network

    def _parse_blocks(self):
        """Get all blocks sequentially."""
        for idx, row in self.df.iterrows():
            block_num = row.get("Block Number", "N/A")
            if block_num != "N/A" and str(block_num) != "nan":
                try:
                    self.all_blocks.append(int(block_num))
                except:
                    pass
        self.all_blocks = sorted(set(self.all_blocks))
        self.network.all_blocks = self.all_blocks
        print(f"✓ Sequential foundation: {len(self.all_blocks)} blocks")

    def extract_crossing(self, value):
        """Extract crossing information from infrastructure text."""
        text = str(value).upper()
        if "RAILWAY CROSSING" in text:
            return "Yes"
        return "No"

    def _parse_crossings(self):
        """Parse crossing blocks from the 'Infrastructure' column."""
        crossing_blocks = []
        for idx, row in self.df.iterrows():
            infra_text = row.get("Infrastructure", "")
            block_num = row.get("Block Number")

            if block_num != "N/A" and str(block_num) != "nan":
                if self.extract_crossing(infra_text) == "Yes":
                    try:
                        crossing_blocks.append(int(block_num))
                    except:
                        pass

        self.network.crossing_blocks = sorted(crossing_blocks)
        print(f"✓ Parsed {len(self.network.crossing_blocks)} crossing blocks")

    def _parse_switches(self):
        """Parse switches from the 'Infrastructure' column."""
        for idx, row in self.df.iterrows():
            infra_text = str(row.get("Infrastructure", "")).upper()
            block_num = row.get("Block Number")

            if block_num != "N/A" and str(block_num) != "nan":
                block_num = int(block_num)
                branch_conns = parse_branching_connections(infra_text)

                if branch_conns:
                    # Collect all blocks and count occurrences
                    from collections import Counter

                    all_blocks = []

                    for from_b, to_b in branch_conns:
                        all_blocks.append(from_b)
                        all_blocks.append(to_b)

                    # The branch point is the block that appears MORE THAN ONCE
                    block_counts = Counter(all_blocks)
                    branch_point = None

                    for block, count in block_counts.items():
                        if count > 1:
                            branch_point = block
                            break

                    if branch_point:
                        # Get all unique blocks involved
                        unique_blocks = sorted(list(set(all_blocks)))
                        self.switch_data[branch_point] = unique_blocks

        print(f"✓ Parsed {len(self.switch_data)} switches")
        for b, targets in self.switch_data.items():
            print(f"Block {b} → {targets}")

    def _build_red_line(self):
        """Build Red Line with hard-coded rules."""
        # Hard-coded Red Line exceptions
        forbidden = {(66, 67), (67, 66), (71, 72), (72, 71)}

        # Initialize all blocks first
        for block in self.all_blocks:
            self.network.connections[block] = []

        # Add sequential connections (bidirectional)
        for block in self.all_blocks:
            if block - 1 in self.all_blocks:
                if (block - 1, block) not in forbidden:
                    self.network.connections[block].append(block - 1)

            if block + 1 in self.all_blocks:
                if (block, block + 1) not in forbidden:
                    self.network.connections[block].append(block + 1)

        # Add branch connections (bidirectional)
        for block in self.switch_data:
            branch_targets = []
            for target in self.switch_data[block]:
                if target != block and abs(target - block) > 1:
                    # Non-sequential connection
                    if (block, target) not in forbidden and (
                        target,
                        block,
                    ) not in forbidden:
                        # Add bidirectional
                        if target not in self.network.connections[block]:
                            self.network.connections[block].append(target)
                        if block not in self.network.connections[target]:
                            self.network.connections[target].append(block)

                        branch_targets.append(target)

                        # Add to additional_connections for visualizer (once)
                        conn = (min(block, target), max(block, target))
                        if conn not in self.network.additional_connections:
                            self.network.additional_connections.append(conn)

            # Store branch point
            if branch_targets:
                self.network.branch_points[block] = BranchPoint(
                    block=block, targets=branch_targets
                )

        # Store skip connections for visualizer
        self.network.skip_connections = [(66, 67), (71, 72)]

        print(f"  Red Line: {len(self.network.connections)} blocks connected")
        print(f"  Branch points: {list(self.network.branch_points.keys())}")
        print(f"  Additional connections: {self.network.additional_connections}")
        print(f"  Skip connections: {self.network.skip_connections}")

    def _build_green_line(self):
        """Build Green Line with hard-coded rules."""
        # Hard-coded green Line exceptions
        forbidden = {(100, 101)}

        # Initialize all blocks first
        for block in self.all_blocks:
            self.network.connections[block] = []

        # Add sequential connections (bidirectional)
        for block in self.all_blocks:
            if block - 1 in self.all_blocks:
                if (block - 1, block) not in forbidden:
                    self.network.connections[block].append(block - 1)

            if block + 1 in self.all_blocks:
                if (block, block + 1) not in forbidden:
                    self.network.connections[block].append(block + 1)

        # Add branch connections (bidirectional)
        for block in self.switch_data:
            branch_targets = []
            for target in self.switch_data[block]:
                if target != block and abs(target - block) > 1:
                    # Non-sequential connection
                    if (block, target) not in forbidden and (
                        target,
                        block,
                    ) not in forbidden:
                        # Add bidirectional
                        if target not in self.network.connections[block]:
                            self.network.connections[block].append(target)
                        if block not in self.network.connections[target]:
                            self.network.connections[target].append(block)

                        branch_targets.append(target)

                        # Add to additional_connections for visualizer (once)
                        conn = (min(block, target), max(block, target))
                        if conn not in self.network.additional_connections:
                            self.network.additional_connections.append(conn)

            # Store branch point
            if branch_targets:
                self.network.branch_points[block] = BranchPoint(
                    block=block, targets=branch_targets
                )

        # Store skip connections for visualizer
        self.network.skip_connections = [(100, 101)]

        print(f"  Line: {len(self.network.connections)} blocks connected")
        print(f"  Branch points: {list(self.network.branch_points.keys())}")
        print(f"  Additional connections: {self.network.additional_connections}")
        print(f"  Skip connections: {self.network.skip_connections}")

    def print_connection_graph(self):
        """Print the full connection graph for debugging."""
        print("\n=== CONNECTION GRAPH ===")
        for block in sorted(self.network.connections.keys()):
            neighbors = sorted(self.network.connections[block])
            is_branch = "BRANCH" if block in self.network.branch_points else ""
            print(f"Block {block:3d} → {neighbors} {is_branch}")
        print("=" * 40 + "\n")


def main():
    """Test the network by loading data from an Excel file."""
    excel_file_path = "Track Layout & Vehicle Data vF5.xlsx"

    try:
        df = pd.read_excel(excel_file_path, sheet_name="Green Line")
        print(f"✓ Data loaded successfully from {excel_file_path}")

    except FileNotFoundError:
        print(f"❌ Error: Excel file not found at '{excel_file_path}'.")

    builder = LineNetworkBuilder(df, "Green Line")
    network = builder.build()

    # Print connection graph
    # builder.print_connection_graph()

    # Print path info
    current = 1
    previous = None
    for i in range(200):
        next_block = network.get_next_block(current, previous)
        print(f"Step {i}: Block {current} → {next_block}")
        if next_block == current:
            print("Train stopped")
            break
        previous = current
        current = next_block


if __name__ == "__main__":
    main()
