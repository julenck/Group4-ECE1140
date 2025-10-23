from typing import List, Optional
from time.time_manager import Time
from train.train import Train

class ScheduledTrain:
    # Represents a train entry in a schedule.

    def __init__(self):
        self.id: int = 0
        self.line: str = ""
        self.destStation: str = ""
        self.departureTime: Time = Time()
        self.arrivalTime: Time = Time()


class Schedule:
    # Represents the full schedule of all trains.

    def __init__(self):
        self.scheduledTrains: List[ScheduledTrain] = []
        self.nextTrain: Optional[Train] = None
        self.nextDepartureTime: int = 0
