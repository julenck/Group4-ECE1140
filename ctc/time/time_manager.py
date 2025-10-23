from datetime import datetime

class Time:
    # Manages simulation time and speed.

    def __init__(self):
        self.currentTime: datetime = datetime.now()
        self.simSpeed: int = 1
        self.running: bool = False

    def getCurrentTime(self) -> datetime:
        # Return the current simulation time.
        pass

    def setTime(self, t: datetime) -> None:
        # Set the current simulation time.
        pass

    def start(self) -> None:
        # Start advancing simulation time.
        pass

    def stop(self) -> None:
        # Pause or stop simulation time.
        pass

    def advance(self) -> None:
        # Advance simulation time according to speed.
        pass
