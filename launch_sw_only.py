#!/usr/bin/env python3
"""Launch SW Wayside Controller only"""
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from track_controller.New_SW_Code import sw_wayside_controller, sw_vital_check
from track_controller.New_SW_Code.sw_wayside_controller_ui import sw_wayside_controller_ui

print("🔧 Launching SW Wayside (Blocks 0-69)...")

vital = sw_vital_check.sw_vital_check()
controller = sw_wayside_controller.sw_wayside_controller(vital, 'Green_Line_PLC_XandLup.py')
ui = sw_wayside_controller_ui(controller)
ui.title('SW Wayside - Blocks 0-69')
ui.geometry("1200x800")
ui.mainloop()
