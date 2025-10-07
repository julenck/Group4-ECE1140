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
emergency_button = Button(18, pull_up=False)
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
        self.after(500, self.update_display)
        emergency_button.when_pressed = self.trigger_emergency

    def trigger_emergency(self):
        
        self.emergency_active = not self.emergency_active

        if self.emergency_active:

            emergency_led.on()
            buzzer.on()
            self.emergencyStatusLabel.config(text="Emergency: ACTIVE", foreground="red")
        else:
            emergency_led.off()
            buzzer.off()
            self.emergencyStatusLabel.config(text="Emergency: OFF", foreground="green")

    def update_display(self):
       
        plc_rules = []
        commanded_speed = 0
        commanded_authority = 0

        # Load inputs file if present (now includes block_occupancies and destination and optional emergency flag)
        if os.path.exists("WaysideInputs_testUI.json"):
            try:
                with open("WaysideInputs_testUI.json", "r") as file:
                    waysideInputs = json.load(file)
            except Exception:
                waysideInputs = {}
        else:
            waysideInputs = {}

        suggestedSpeed = waysideInputs.get("suggested_speed", 0)
        self.suggestedSpeedLabel.config(text="Suggested Speed: " + str(suggestedSpeed) + " mph")

        suggestedAuthority = waysideInputs.get("suggested_authority", 0)
        self.suggestedAuthorityLabel.config(text="Suggested Authority: " + str(suggestedAuthority) + " ft")

        # If test UI set an emergency flag, honor it here
        if "emergency" in waysideInputs:
            desired_emergency = bool(waysideInputs.get("emergency", False))
            if desired_emergency != self.emergency_active:
                # update hardware indicators to match input
                self.emergency_active = desired_emergency
                if self.emergency_active:
                    emergency_led.on()
                    buzzer.on()
                    self.emergencyStatusLabel.config(text="Emergency: ACTIVE", foreground="red")
                else:
                    emergency_led.off()
                    buzzer.off()
                    self.emergencyStatusLabel.config(text="Emergency: OFF", foreground="green")

        # Read block occupancies and destination for PLC logic
        block_occupancies = waysideInputs.get("block_occupancies", [])
        destination = waysideInputs.get("destination", 0)

        # Use plc_parser to compute switches/lights/crossings and commanded values
        try:
            waysideOutputs = plc_parser.parse_plc_data(
                self.file_path_var.get(), block_occupancies, destination, suggestedSpeed, suggestedAuthority
            )
        except Exception:
            # fall back to minimal outputs if parser fails
            waysideOutputs = {
                "switches": {},
                "lights": {},
                "crossings": {},
                "commanded_speed": max(0, suggestedSpeed),
                "commanded_authority": max(0, suggestedAuthority),
            }

        # Ensure emergency is included in outputs
        waysideOutputs["emergency"] = self.emergency_active

        # Write outputs file (HW uses WaysideOutputs_testUI.json)
        try:
            with open("WaysideOutputs_testUI.json", "w") as file:
                json.dump(waysideOutputs, file, indent=4)
        except Exception:
            pass

        # Update displayed values
        self.commandedSpeedLabel.config(text="Commanded Speed: " + str(waysideOutputs.get("commanded_speed", "N/A")) + " mph")
        self.commandedAuthorityLabel.config(text="Commanded Authority: " + str(waysideOutputs.get("commanded_authority", "N/A")) + " ft")
        self.emergencyStatusLabel.config(
            text="Emergency: " + ("ACTIVE" if waysideOutputs.get("emergency") else "OFF"),
            foreground=("red" if waysideOutputs.get("emergency") else "green")
        )

        # update gate and light labels
        gate_states = waysideOutputs.get("crossings", {})
        gate_states_str = ", ".join(f"Crossing {k}:{v}" for k, v in gate_states.items())
        self.gateStateLabel.config(text="Gate States: " + (gate_states_str if gate_states_str else "N/A"))

        light_states = waysideOutputs.get("lights", {})
        light_states_str = ", ".join(f"Light {k}:{v}" for k, v in light_states.items())
        self.lightStateLabel.config(text="Light States: " + (light_states_str if light_states_str else "N/A"))

        self.WaysideInputs = waysideInputs

        # schedule next poll
        self.after(500, self.update_display)

if __name__ == "__main__":
    app = HWTrackControllerUI()
    app.mainloop()