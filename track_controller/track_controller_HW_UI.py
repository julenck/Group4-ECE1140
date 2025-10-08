# Track Controller Hardware UI

import tkinter as tk
from tkinter import ttk
import json
import os
from gpiozero import LED, Button, Buzzer
from time import sleep
import plc_parser

# GPIO setup
emergency_led = LED(17)
emergency_button = Button(18, pull_up=True)
buzzer = Buzzer(22)

# LCD setup (I2C, using freenove or iRasptek LCD library)

from RPLCD.i2c import CharLCD
lcd = CharLCD('PCF8574', 0x27)  # 0x27 typical address

WindowWidth = 800
WindowHeight = 480

class HWTrackControllerUI(tk.Tk):

    def __init__(self):

        super().__init__()
        self.title("Track Controller Hardware Module")
        self.geometry(f"{WindowWidth}x{WindowHeight}")

        # Emergency status variable
        self.emergency_active = False

        # PLC file path var (match SW UI)
        self.file_path_var = tk.StringVar(value="blue_line_plc.json")

        # GUI labels for inputs (match SW UI names used in update_display)
        self.suggestedSpeedLabel = ttk.Label(self, text="Suggested Speed: N/A")
        self.suggestedSpeedLabel.pack(pady=5)

        self.suggestedAuthorityLabel = ttk.Label(self, text="Suggested Authority: N/A")
        self.suggestedAuthorityLabel.pack(pady=5)

        # GUI label for hardware state
        self.commandedSpeedLabel = ttk.Label(self, text="Commanded Speed: N/A")
        self.commandedSpeedLabel.pack(pady=10)

        self.commandedAuthorityLabel = ttk.Label(self, text="Commanded Authority: N/A")
        self.commandedAuthorityLabel.pack(pady=10)

        self.emergencyStatusLabel = ttk.Label(self, text="Emergency: OFF", foreground="green")
        self.emergencyStatusLabel.pack(pady=20)

        # Add gate and light labels so HW UI shows those statuses
        self.gateStateLabel = ttk.Label(self, text="Gate States: N/A")
        self.gateStateLabel.pack(pady=5)

        self.lightStateLabel = ttk.Label(self, text="Light States: N/A")
        self.lightStateLabel.pack(pady=5)

        # Ensure WaysideInputs placeholder exists
        self.WaysideInputs = {}

        # Periodic update loop
        emergency_button.when_pressed = self.trigger_emergency
        self.after(500, self.update_display)

    def trigger_emergency(self):
        
        """Toggle emergency state immediately when button pressed."""
        self.emergency_active = not self.emergency_active

        # Update hardware indicators
        emergency_led.value = self.emergency_active
        buzzer.value = self.emergency_active

        # Update label
        self.emergencyStatusLabel.config(

            text=f"Emergency: {'ACTIVE' if self.emergency_active else 'OFF'}",
            foreground='red' if self.emergency_active else 'green'
        )

    def update_display(self):
       
        waysideInputs = {}
        try:
            if os.path.exists("WaysideInputs_testUI.json"):
                with open("WaysideInputs_testUI.json", "r") as file:
                    waysideInputs = json.load(file)
        except Exception:
            pass

        # Suggested values
        suggestedSpeed = waysideInputs.get("suggested_speed", 0)
        suggestedAuthority = waysideInputs.get("suggested_authority", 0)
        self.suggestedSpeedLabel.config(text=f"Suggested Speed: {suggestedSpeed} mph")
        self.suggestedAuthorityLabel.config(text=f"Suggested Authority: {suggestedAuthority} ft")

        # If test UI sets emergency, sync it
        if "emergency" in waysideInputs:
            desired_emergency = bool(waysideInputs.get("emergency", False))
            if desired_emergency != self.emergency_active:
                self.toggle_emergency()  # will update LED/buzzer/label

        block_occupancies = waysideInputs.get("block_occupancies", [])
        destination = waysideInputs.get("destination", 0)

        # Compute PLC outputs
        try:
            waysideOutputs = plc_parser.parse_plc_data(
                self.file_path_var.get(),
                block_occupancies,
                destination,
                suggestedSpeed,
                suggestedAuthority
            )
        except Exception:
            waysideOutputs = {
                "switches": {},
                "lights": {},
                "crossings": {},
                "commanded_speed": suggestedSpeed,
                "commanded_authority": suggestedAuthority,
            }

        # Ensure emergency is included
        waysideOutputs["emergency"] = self.emergency_active

        # Write outputs
        try:
            with open("WaysideOutputs_testUI.json", "w") as file:
                json.dump(waysideOutputs, file, indent=4)
        except Exception:
            pass

        # Update GUI with commanded values
        self.commandedSpeedLabel.config(text=f"Commanded Speed: {waysideOutputs.get('commanded_speed', 'N/A')} mph")
        self.commandedAuthorityLabel.config(text=f"Commanded Authority: {waysideOutputs.get('commanded_authority', 'N/A')} ft")
        self.emergencyStatusLabel.config(
            text=f"Emergency: {'ACTIVE' if waysideOutputs.get('emergency') else 'OFF'}",
            foreground='red' if waysideOutputs.get('emergency') else 'green'
        )

        # Update gate and light labels
        gate_states = waysideOutputs.get("crossings", {})
        self.gateStateLabel.config(
            text="Gate States: " + (", ".join(f"{k}: {v}" for k, v in gate_states.items()) or "N/A")
        )
        light_states = waysideOutputs.get("lights", {})
        self.lightStateLabel.config(
            text="Light States: " + (", ".join(f"{k}: {v}" for k, v in light_states.items()) or "N/A")
        )

        # Save inputs
        self.WaysideInputs = waysideInputs

        # Schedule next update
        self.after(500, self.update_display)

if __name__ == "__main__":
    app = HWTrackControllerUI()
    app.mainloop()