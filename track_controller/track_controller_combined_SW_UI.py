
"""
Combined Track Controller UI Launcher
Runs both the Test UI and Main Software UI together
"""
  # main
import tkinter as tk
from track_controller_SW_UI import SWTrackControllerUI
from track_controller_SW_test_UI import TestUI

def main():
    # Create the main software UI (this creates the single Tk root)
    main_ui = SWTrackControllerUI()
    main_ui.title("Track Controller Software Module")
    main_ui.geometry("1200x700")

    # Create the test UI as a Toplevel child of the main UI (same Tk)
    test_root = tk.Toplevel(main_ui)
    test_root.title("Wayside Controller Test UI")
    test_root.geometry("700x400")
    test_ui = TestUI(test_root)

    main_ui.lift()
    test_root.lift()

    # Start the mainloop on the single Tk instance
    main_ui.mainloop()

if __name__ == "__main__":
    main()
