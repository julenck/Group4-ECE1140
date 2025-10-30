from schedule.schedule import Schedule
from track.track_system import TrackSystem
from train.train_system import TrainSystem
from track.block import Block
from track.station import Station
from track.gate import Gate

class CTC:
    # CTC main controller 

    def __init__(self):
        self.schedule: Schedule = Schedule()
        self.mode: str = ""
        self.throughput: int = 0
        self.trackSystem: TrackSystem = TrackSystem()
        self.trainSystem: TrainSystem = TrainSystem()

    def parseSchedule(self) -> None:
        # Parse and load train schedules.
        pass

    def dispatchManual(self) -> None:
        # Manually dispatch a train.
        pass

    def calculateAuthority(self) -> None:
        # Compute authority for trains.
        pass

    def calculateSpeed(self) -> None:
        # Calculate suggested speed 
        pass

    def getLineInfo(self) -> None:
        # Return information about a track line. 
        pass

    def getGateInfo(self) -> Gate:
        # Return gate information.
        pass

    def getStationInfo(self) -> Station:
        # Return station information.
        pass

    def updateThroughput(self) -> None:
        # Recalculate total system throughput.
        pass

    def updateActiveTrainsTable(self) -> None:
        # Update UI table with active trains.
        pass

    def updateStatusTable(self) -> None:
        # Update status information in the UI.
        pass

    def getBlockInfo(self) -> Block:
        # Return information about a specific block.
        pass

    def updateUI(self) -> None:
        # Send latest updates to the UI.
        pass
