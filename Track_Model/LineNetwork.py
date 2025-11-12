"""
Line Network - Defines train paths and topology for Red and Green lines
Knows how trains move through the network and provides visualization info
"""

import pandas as pd
import re
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass


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

    def __init__(self, line_name: str):
        self.line_name = line_name
        self.connections: Dict[int, List[int]] = {}  # block -> list of connected blocks
        self.branch_points: Dict[int, BranchPoint] = {}
        self.additional_connections: List[Tuple[int, int]] = (
            []
        )  # non-sequential to draw
        self.skip_connections: List[Tuple[int, int]] = []  # exceptions not to draw

    def get_next_block(
        self,
        current: int,
        previous: Optional[int] = None,
        switch_positions: Dict[int, int] = None,
    ) -> Optional[int]:
        """Get next block given current position, previous block, and switch states."""
        if current not in self.connections:
            return None

        available = list(self.connections[current])

        # Remove previous block (can't reverse immediately)
        if previous is not None and previous in available:
            available.remove(previous)

        if not available:
            return None

        # If at branch point and switch position given
        if switch_positions and current in switch_positions:
            target = switch_positions[current]
            if target in available:
                return target

        # Default to sequential (prefer current+1, else current-1)
        if current + 1 in available:
            return current + 1
        elif current - 1 in available:
            return current - 1
        else:
            # Pick first available
            return available[0]

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

        # Step 3: Apply line-specific rules
        if self.line_name == "Red Line":
            self._build_red_line()
        elif self.line_name == "Green Line":
            self._build_green_line()

        print(f"✓ Built connection graph with {len(self.network.connections)} blocks")
        print(f"✓ Found {len(self.network.branch_points)} branch points")
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
        print(f"✓ Sequential foundation: {len(self.all_blocks)} blocks")

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
    builder.print_connection_graph()


if __name__ == "__main__":
    main()
