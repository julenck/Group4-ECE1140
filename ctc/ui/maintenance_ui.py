from typing import Optional
from track.block import Block
from track.switch import Switch

class MaintenanceUI:
    # UI for performing maintenance tasks such as closing blocks or switching tracks.

    def __init__(self):
        self.selectedLine: str = ""
        self.selectedSwitch: str = ""
        self.selectedBlock: Optional[Block] = None

    def getInfoForLine(self) -> str:
        # Return diagnostic or status information for a line.
        pass

    def getSwitchToMove(self) -> Switch:
        # Return the switch selected for movement.
        pass

    def getBlockToClose(self) -> Block:
        # Return the block selected to be closed for maintenance.
        pass
