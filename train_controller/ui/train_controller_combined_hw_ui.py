"""Train Controller Combined UI.

This module provides a combined interface that launches both the Driver UI
and the Test UI simultaneously for testing purposes.

Author: Julen Coca-Knorr
"""

import tkinter as tk
from tkinter import ttk
import os
import sys
import threading

# Add parent directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Import UIs and API
from train_controller_hw_ui import hw_train_controller_ui
from train_controller_test_ui import train_controller_test_ui

def run_driver_ui():
    """Run the driver interface in its own thread."""
    driver_ui = hw_train_controller_ui()
    driver_ui.mainloop()

def run_test_ui():
    """Run the test interface in its own thread."""
    test_ui = train_controller_test_ui()
    test_ui.mainloop()

def main():
    """Launch both UIs in separate threads."""
    # Create and start thread for driver UI
    driver_thread = threading.Thread(target=run_driver_ui)
    driver_thread.daemon = True  # Thread will close when main program exits
    driver_thread.start()
    
    # Create and start thread for test UI
    test_thread = threading.Thread(target=run_test_ui)
    test_thread.daemon = True  # Thread will close when main program exits
    test_thread.start()
    
    # Create a simple root window to keep the program running
    root = tk.Tk()
    root.title("Train Controller UI Manager")
    root.geometry("300x150")
    
    # Add some information text
    info_text = """Train Controller UIs Running
    
Driver UI and Test UI are now active.
Close this window to exit both UIs."""
    
    label = ttk.Label(root, text=info_text, justify=tk.CENTER)
    label.pack(expand=True, padx=10, pady=10)
    
    # Start the main loop
    root.mainloop()

if __name__ == "__main__":
    main()