#!/usr/bin/env python3
"""Launch HW Wayside Controller only"""
import sys
import os
import tkinter as tk

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'track_controller', 'hw_wayside'))

from track_controller.hw_wayside.hw_wayside_controller import HW_Wayside_Controller
from track_controller.hw_wayside.hw_wayside_controller_ui import HW_Wayside_Controller_UI
from track_controller.hw_wayside.hw_display import HW_Display

print("⚙️  Launching HW Wayside (Blocks 70-143)...")

controller = HW_Wayside_Controller('B', list(range(70, 144)))
controller.load_plc('Green_Line_PLC_XandLdown.py')
controller.start_trains(period_s=1.0)

root = tk.Tk()
root.geometry("1200x800")
ui = HW_Wayside_Controller_UI(root, controller, "HW Wayside - Blocks 70-143")
ui.pack(fill='both', expand=True)
root.mainloop()
