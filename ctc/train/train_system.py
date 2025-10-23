from typing import List
from .train import Train

class TrainSystem:
    # Manages all active trains in the system.

    def __init__(self):
        self.activeTrains: List[Train] = []

    def newTrain(self) -> None:
        # Add a new train to the system.
        pass

    def removeTrain(self) -> None:
        # Remove a train from the system.
        pass

    def updateOccupancy(self) -> None:
        # Update track occupancy based on train positions.
        pass

    def updateSpeed(self) -> None:
        # Update suggested speed 
        pass

    def updateAuthority(self) -> None:
        # Update suggested authortiy 
        pass

    def updateDestination(self) -> None:
        # Update train destination info.
        pass

    def updateArrivalTime(self) -> None:
        # Update each train's expected arrival time.
        pass
