class Block:
    # Represents a block on the track

    def __init__(self):
        self.line: str = ""
        self.section: str = ""
        self.number: int = 0
        self.failure: str = ""
        self.status: str = ""
