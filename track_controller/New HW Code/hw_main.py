# hw_main.py
# Main entry point for the Wayside Controller HW module.
# Oliver Kettelson-Belinkie, 2025

from __future__ import annotations
import tkinter as tk
from typing import List
from hw_wayside_controller import HW_Wayside_Controller
from hw_display import HW_Display
from hw_wayside_controller_ui import HW_Wayside_Controller_UI


def main() -> None:
    blocks: List[str] = ["A1", "A2", "A3", "A4", "A5"]

    root = tk.Tk()
    controller = HW_Wayside_Controller(blocks)
    display = HW_Display(root, available_blocks=blocks)
    ui = HW_Wayside_Controller_UI(controller, display)

    ui.update_display(emergency=False, speed_mph=0.0, authority_yards=0)

    # TODO: add a small timer/loop to read JSON/socket and call:
    # controller.apply_vital_inputs(blocks, incoming_dict); ui._push_to_display()

    root.mainloop()


if __name__ == "__main__":
    main()