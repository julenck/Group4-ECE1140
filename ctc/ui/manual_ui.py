from typing import Optional
from time.time_manager import Time
from train.train import Train

class ManualUI:
    # UI for manually controlling and dispatching trains.

    def __init__(self):
        self.selectedTrain: Optional[Train] = None
        self.selectedLine: str = ""
        self.selectedDest: str = ""
        self.selectedArrivalTime: Time = Time()

    def getTrain(self) -> int:
        # Get the currently selected train's ID.
        pass

    def getLine(self) -> str:
        # Get selected line.
        pass

    def getDest(self) -> str:
        # Get selected destination.
        pass

    def getArrivalTime(self) -> int:
        # Get selected arrival time.
        pass
