# track_controller_combined_HW_UI.py
import tkinter as tk
from track_controller_HW_UI import HWTrackControllerUI
from track_controller_HW_test_UI import TestUI

def main():
    main_ui = HWTrackControllerUI()  # single Tk root
    test_win = tk.Toplevel(main_ui)
    test_win.title("Wayside Controller Test UI")
    TestUI(test_win, controller=main_ui)
    main_ui.mainloop()

if __name__ == "__main__":
    main()