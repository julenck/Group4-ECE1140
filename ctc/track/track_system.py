from typing import List
from .block import Block
from .light import Light
from .gate import Gate
from .station import Station

class TrackSystem:
    # Handles the overall track system: blocks, switches, gates, and lights.

    def __init__(self):
        self.line: str = ""
        self.blocks: List[Block] = []
        self.lights: List[Light] = []
        self.gates: List[Gate] = []
        self.stations: List[Station] = []

    def updateBlockOccupancy(self) -> None:
        # Update which blocks are currently occupied.
        pass

    def updateBlockFailure(self) -> None:
        # Update block failure status.
        pass

    def updateBlockStatus(self) -> None:
        # Update block status (open/closed).
        pass

    def updateSwitchPosition(self) -> None:
        # Update the position of all switches.
        pass

    def updateGateStatus(self) -> None:
        # Update status of crossing gates.
        pass

    def updateStationStatus(self) -> None:
        # Update status of all stations.
        pass

    def updatePassengersEntering(self) -> None:
        # Update passenger counts entering at stations.
        pass

    def updatePassengersLeaving(self) -> None:
        # Update passenger counts leaving at stations.
        pass
