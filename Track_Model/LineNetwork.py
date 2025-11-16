"""
Line Network - Defines train paths and topology for Red and Green lines
Knows how trains move through the network and provides visualization info
"""

import pandas as pd
import re
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
import json
import random
import os


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
        self.red_line_trains = []
        self.green_line_trains = []
        self.total_ticket_sales = 0  # Cumulative ticket sales across all trains
        self.previous_train_motions = {}  # Track motion changes: {train_id: motion}

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

    def generate_random_passengers_boarding(self, train_id: int, station_name: str):
        """Generate random passengers boarding (0-200) and store in block manager."""
        passengers = random.randint(0, 200)

        if self.block_manager:
            self.block_manager.number_of_passengers_boarding(
                train_id, station_name, passengers
            )

    def generate_random_ticket_sales(self):
        """Generate random ticket sales (200-400), add to cumulative total, and store in block manager."""
        new_sales = random.randint(200, 400)
        self.total_ticket_sales += new_sales

        if self.block_manager:
            self.block_manager.number_of_ticket_sales(self.total_ticket_sales)

    def read_train_data_from_json(
        self, json_path: str = "track_model_Track_controller.json"
    ):
        """Read train control data from JSON file."""
        try:
            with open(json_path, "r") as f:
                data = json.load(f)

            # Determine prefix based on line
            prefix = self.line_name[0]  # "G" for Green, "R" for Red

            # Parse arrays from JSON
            switches = data.get(f"{prefix}-switches", [])
            gates = data.get(f"{prefix}-gates", [])
            lights = data.get(f"{prefix}-lights", [])

            # Get commanded speeds and authorities from G-Train or R-Train
            train_data = data.get(f"{prefix}-Train", {})
            commanded_speeds = train_data.get("commanded speed", [])
            commanded_authorities = train_data.get("commanded authority", [])

            # Create data dict with only switches, gates, lights
            data_dict = {
                "switches": switches,
                "gates": gates,
                "lights": lights,
            }

            # Write parsed data to block manager
            self.write_to_block_manager(data_dict)

            # Write to Train Model JSON
            self.write_to_train_model_json(commanded_speeds, commanded_authorities)

        except Exception as e:
            print(f"Error reading JSON: {e}")

    def write_to_train_model_json(self, commanded_speeds, commanded_authorities):
        # Read file
        with open("track_model_Train_Model.json", "r") as f:
            train_model_data = json.load(f)

        # Extract motion and store
        trains = []
        for i in range(len(commanded_speeds)):
            train_key = f"{self.line_name[0]}_train_{i + 1}"
            if train_key in train_model_data:
                motion = train_model_data[train_key]["motion"]["current motion"]
                trains.append({"train_id": i + 1, "motion": motion})

                # Write commanded speed/authority
                train_model_data[train_key]["block"]["commanded speed"] = (
                    commanded_speeds[i]
                )
                train_model_data[train_key]["block"]["commanded authority"] = (
                    commanded_authorities[i]
                )

        if self.block_manager:
            self.block_manager.trains = []
            for t in trains:
                self.block_manager.trains.append(
                    {
                        "train_id": t["train_id"],
                        "line": self.line_name,
                        "start": True if t["motion"] == "Moving" else False,
                    }
                )

        # Store based on line
        if self.line_name == "Green":
            self.green_line_trains = trains
        else:
            self.red_line_trains = trains

        # Write back
        with open("track_model_Train_Model.json", "w") as f:
            json.dump(train_model_data, f, indent=4)

    def write_to_block_manager(self, data: dict):
        """Parse raw JSON data and write to block manager."""
        if not self.block_manager:
            return

        # Extract raw arrays
        switches = data["switches"]
        gates = data["gates"]
        lights = data["lights"]

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
        )

    def process_switch_positions(self, switches: List[int]) -> Dict[int, int]:
        switch_positions = {}

        if self.line_name == "Green":
            branch_point_keys = sorted(
                self.branch_points.keys()
            )  # Get sorted branch points

            # First 2 switches → first 2 branch points
            for i in range(2):
                if i < len(branch_point_keys) and i < len(switches):
                    block_num = branch_point_keys[i]
                    switch_setting = switches[i]
                    targets = self.branch_points[block_num].targets
                    if 0 <= switch_setting < len(targets):
                        switch_positions[block_num] = targets[switch_setting]

            # Middle 2 switches → Yard (hard-coded 57 and 63)
            if switches[2] == 1:
                switch_positions[57] = 0  # 57 → Yard
            if switches[3] == 1:
                switch_positions[63] = 0  # 63 → Yard

            # Last 2 switches → last 2 branch points
            for i in range(2):
                idx = i + 2  # branch point index
                switch_idx = i + 4  # switches[4] and switches[5]
                if idx < len(branch_point_keys) and switch_idx < len(switches):
                    block_num = branch_point_keys[idx]
                    switch_setting = switches[switch_idx]
                    targets = self.branch_points[block_num].targets
                    if 0 <= switch_setting < len(targets):
                        switch_positions[block_num] = targets[switch_setting]

                # ADD RED LINE HANDLING HERE IF NEEDED
        elif self.line_name == "Red":
            # Add Red Line switch processing logic
            pass

        return switch_positions  # ← ADD THIS LINE

    def parse_traffic_lights(self, current_block: int, lights_array: List[int]) -> str:
        """
        Parse traffic light status for current block.
        Returns: "Super Green", "Green", "Yellow", or "Red"
        """
        # Hard-coded blocks with traffic lights
        if self.line_name == "Green":
            traffic_light_blocks = [0, 3, 7, 29, 58, 62, 76, 86, 100, 101, 150, 151]
        elif self.line_name == "Red":
            traffic_light_blocks = []  # TODO: Add Red line blocks when available

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

    def get_next_block(
        self, train_id: int, current: int, previous: Optional[int] = None
    ) -> int:
        # Read JSON to update everything
        self.read_train_data_from_json()

        # Find this train's motion
        trains = (
            self.green_line_trains
            if self.line_name == "Green"
            else self.red_line_trains
        )
        motion = None
        for train in trains:
            if train["train_id"] == train_id:
                motion = train["motion"]
                break

        # Check if motion changed from "Undispatched" to "Moving"
        previous_motion = self.previous_train_motions.get(train_id)
        if previous_motion == "Undispatched" and motion == "Moving":
            self.generate_random_ticket_sales()

        # Update previous motion
        self.previous_train_motions[train_id] = motion

        # Determine next_block based on motion
        next_block = current  # Default

        # If Undispatched, return Yard
        if motion == "Undispatched":
            next_block = 0

        # If Stopped, stay at current
        elif motion == "Stopped":
            next_block = current

        # If Moving or Braking, calculate next block
        else:
            # Get switch position for current block from block_manager
            switch_target = self.block_manager.get_switch_position(
                self.line_name, current
            )

            # If there's a branch target, go there
            if switch_target != "N/A" and isinstance(switch_target, int):
                next_block = switch_target
            else:
                # Otherwise, go sequentially (current + 1)
                next_block = current + 1

        # Check if next_block is a station and generate passengers boarding
        station_name = self.get_station_name(next_block)
        if station_name != "N/A":
            self.generate_random_passengers_boarding(train_id, station_name)

        # Update occupancy in block manager
        self.update_block_occupancy(next_block, current)
        self.write_beacon_data_to_train_model(next_block, train_id)

        # Write occupancy and failures back to Track Controller JSON
        self.write_occupancy_to_json()
        self.write_failures_to_json()

        return next_block

    def get_station_name(self, block_num: int) -> str:
        """Get station name for a given block number from static JSON."""
        try:
            with open("track_model_static.json", "r") as f:
                static_data = json.load(f)

            blocks = static_data.get(self.line_name, [])
            for block in blocks:
                if block.get("Block Number") == block_num:
                    return block.get("Station", "N/A")
        except Exception as e:
            print(f"Error reading station name: {e}")

        return "N/A"

    def write_beacon_data_to_train_model(self, next_block: int, train_id: int):
        """Write beacon data to Train Model JSON for a specific train."""
        try:
            # Read static track data
            with open("track_model_static.json", "r") as f:
                static_data = json.load(f)

            blocks = static_data.get(self.line_name, [])

            # Find next_block in the list
            block_data = None
            block_index = None
            for i, block in enumerate(blocks):
                if block.get("Block Number") == next_block:
                    block_data = block
                    block_index = i
                    break

            if not block_data:
                return

            # Extract beacon data
            speed_limit = block_data.get("Speed Limit (Km/Hr)", 0)
            side_door = block_data.get("Station Side", "N/A")
            current_station = block_data.get("Station", "N/A")

            # Get next station
            next_station = "N/A"
            if block_index is not None and block_index + 1 < len(blocks):
                next_station = blocks[block_index + 1].get("Station", "N/A")

            # Get passengers_boarding from block_manager
            passengers_boarding = 0
            if self.block_manager and current_station != "N/A":
                passengers_boarding = self.block_manager.get_passengers_boarding(
                    train_id, current_station
                )

            # Create beacon dict
            beacon = {
                "speed limit": speed_limit,
                "side_door": side_door,
                "current station": current_station,
                "next station": next_station,
                "passengers_boarding": passengers_boarding,
            }

            # Write to Train Model JSON
            with open("track_model_Train_Model.json", "r") as f:
                train_model_data = json.load(f)

            train_key = f"train_{train_id}"
            if train_key in train_model_data:
                train_model_data[train_key]["beacon"] = beacon

            with open("track_model_Train_Model.json", "w") as f:
                json.dump(train_model_data, f, indent=4)

        except Exception as e:
            print(f"Error writing beacon data to train model: {e}")

    def update_block_occupancy(
        self, current_block: int, previous_block: Optional[int] = None
    ):
        """Update occupancy in block manager when train moves."""
        if not self.block_manager:
            return
        # Clear all blocks first
        for block_id in self.block_manager.line_states.get(self.line_name, {}):
            self.block_manager.line_states[self.line_name][block_id][
                "occupancy"
            ] = False

        # Set current block as occupied
        for block_id in self.block_manager.line_states.get(self.line_name, {}):
            try:
                block_num_str = "".join(filter(str.isdigit, block_id))
                if block_num_str and int(block_num_str) == current_block:
                    self.block_manager.line_states[self.line_name][block_id][
                        "occupancy"
                    ] = True
                    break
            except (ValueError, AttributeError):
                continue

    def write_occupancy_to_json(
        self, json_path: str = "track_model_Track_controller.json"
    ):
        """Write occupancy data back to Track Controller JSON."""
        if not self.block_manager:
            return

        try:
            with open(json_path, "r") as f:
                data = json.load(f)

            prefix = self.line_name[0]

            occupancy_array = []
            blocks = sorted(
                self.block_manager.line_states.get(self.line_name, {}).keys()
            )

            for block_id in blocks:
                occupancy = self.block_manager.line_states[self.line_name][block_id][
                    "occupancy"
                ]
                occupancy_array.append(1 if occupancy else 0)

            data[f"{prefix}-Occupancy"] = occupancy_array

            with open(json_path, "w") as f:
                json.dump(data, f, indent=4)

        except Exception as e:
            print(f"Error writing occupancy to JSON: {e}")

    def write_failures_to_json(
        self, json_path: str = "track_model_Track_controller.json"
    ):
        """Write failure data back to Track Controller JSON."""
        if not self.block_manager:
            return

        try:
            with open(json_path, "r") as f:
                data = json.load(f)

            prefix = self.line_name[0]

            failures_array = []
            blocks = sorted(
                self.block_manager.line_states.get(self.line_name, {}).keys()
            )

            for block_id in blocks:
                failures = self.block_manager.line_states[self.line_name][block_id][
                    "failures"
                ]
                failures_array.append(1 if failures["power"] else 0)
                failures_array.append(1 if failures["circuit"] else 0)
                failures_array.append(1 if failures["broken"] else 0)

            data[f"{prefix}-Failures"] = failures_array

            with open(json_path, "w") as f:
                json.dump(data, f, indent=4)

        except Exception as e:
            print(f"Error writing failures to JSON: {e}")


class LineNetworkBuilder:
    """Builds network for Red and Green lines."""

    def __init__(self, df: pd.DataFrame, line_name: str):
        self.df = df
        self.line_name = line_name
        self.network = LineNetwork(line_name)
        self.all_blocks = []
        self.switch_data = {}

    def build(self) -> LineNetwork:
        """Build the network."""

        self._parse_blocks()
        self._parse_switches()
        self._parse_crossings()

        if self.line_name == "Red Line":
            self._build_red_line()
        elif self.line_name == "Green Line":
            self._build_green_line()

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

    def _parse_switches(self):
        """Parse switches from the 'Infrastructure' column."""
        for idx, row in self.df.iterrows():
            infra_text = str(row.get("Infrastructure", "")).upper()
            block_num = row.get("Block Number")

            if block_num != "N/A" and str(block_num) != "nan":
                block_num = int(block_num)
                branch_conns = parse_branching_connections(infra_text)

                if branch_conns:
                    from collections import Counter

                    all_blocks = []

                    for from_b, to_b in branch_conns:
                        all_blocks.append(from_b)
                        all_blocks.append(to_b)

                    block_counts = Counter(all_blocks)
                    branch_point = None

                    for block, count in block_counts.items():
                        if count > 1:
                            branch_point = block
                            break

                    if branch_point:
                        unique_blocks = sorted(list(set(all_blocks)))
                        self.switch_data[branch_point] = unique_blocks

    def _build_red_line(self):
        """Build Red Line with hard-coded rules."""
        forbidden = {(66, 67), (67, 66), (71, 72), (72, 71)}

        for block in self.all_blocks:
            self.network.connections[block] = []

        for block in self.all_blocks:
            if block - 1 in self.all_blocks:
                if (block - 1, block) not in forbidden:
                    self.network.connections[block].append(block - 1)

            if block + 1 in self.all_blocks:
                if (block, block + 1) not in forbidden:
                    self.network.connections[block].append(block + 1)

        for block in self.switch_data:
            branch_targets = []
            for target in self.switch_data[block]:
                if target != block and abs(target - block) > 1:
                    if (block, target) not in forbidden and (
                        target,
                        block,
                    ) not in forbidden:
                        if target not in self.network.connections[block]:
                            self.network.connections[block].append(target)
                        if block not in self.network.connections[target]:
                            self.network.connections[target].append(block)

                        branch_targets.append(target)

                        conn = (min(block, target), max(block, target))
                        if conn not in self.network.additional_connections:
                            self.network.additional_connections.append(conn)

            if branch_targets:
                self.network.branch_points[block] = BranchPoint(
                    block=block, targets=branch_targets
                )

        self.network.skip_connections = [(66, 67), (71, 72)]

    def _build_green_line(self):
        """Build Green Line with hard-coded rules."""
        forbidden = {(100, 101)}

        for block in self.all_blocks:
            self.network.connections[block] = []

        for block in self.all_blocks:
            if block - 1 in self.all_blocks:
                if (block - 1, block) not in forbidden:
                    self.network.connections[block].append(block - 1)

            if block + 1 in self.all_blocks:
                if (block, block + 1) not in forbidden:
                    self.network.connections[block].append(block + 1)

        for block in self.switch_data:
            branch_targets = []
            for target in self.switch_data[block]:
                if target != block and abs(target - block) > 1:
                    if (block, target) not in forbidden and (
                        target,
                        block,
                    ) not in forbidden:
                        if target not in self.network.connections[block]:
                            self.network.connections[block].append(target)
                        if block not in self.network.connections[target]:
                            self.network.connections[target].append(block)

                        branch_targets.append(target)

                        conn = (min(block, target), max(block, target))
                        if conn not in self.network.additional_connections:
                            self.network.additional_connections.append(conn)

            if branch_targets:
                self.network.branch_points[block] = BranchPoint(
                    block=block, targets=branch_targets
                )

        self.network.skip_connections = [(100, 101)]
