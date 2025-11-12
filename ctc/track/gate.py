class Gate:
    # Represents a crossing gate for roads intersecting the track.

    def __init__(self):
        self.line: str = ""
        self.section: str = ""
        self.number: int = 0
        self.status: str = ""
