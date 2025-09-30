#!/usr/bin/env python3
"""
Combined Track Controller UI Launcher
Runs both the Test UI and Main Software UI together
"""

import tkinter as tk
from track_controller_SW_UI import SWTrackControllerUI
from track_controller_test_UI import TestUI

def main():
    """Launch both UIs in separate toplevel windows"""
    print("Starting Track Controller Combined UI...")
    print("- Main Software UI and Test UI will open")
    print("- Use the Test UI to simulate inputs")
    print("- The Main UI will automatically update when you run simulations")
    
    # Create the main root window (hidden)
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    # Create the main software UI as a toplevel window
    main_ui = SWTrackControllerUI()
    main_ui.title("Track Controller Software Module")
    main_ui.geometry("1200x700+100+100")
    
    # Create the test UI as a toplevel window
    test_root = tk.Toplevel(root)
    test_root.title("Wayside Controller Test UI")
    test_root.geometry("900x600+1350+100")
    
    test_ui = TestUI(test_root)
    
    # Make sure both windows stay on top
    main_ui.lift()
    test_root.lift()
    
    # Start the main loop
    root.mainloop()

if __name__ == "__main__":
    main()