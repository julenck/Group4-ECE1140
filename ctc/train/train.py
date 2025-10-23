class Train:
    # Represents an individual train 

    def __init__(self):
        self.id: int = 0
        self.line: str = ""
        self.blockSection: int = 0
        self.numPassengers: int = 0
        self.speed: float = 0.0
        self.authority: float = 0.0
        self.destination: str = ""
        self.arrivalTime: int = 0
