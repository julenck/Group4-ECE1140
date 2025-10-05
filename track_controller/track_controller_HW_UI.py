# Track Controller Hardware UI
# Based on SWTrackControllerUI, simplified for Raspberry Pi hardware
# Author: Connor Kariotis + Hardware Adaptation

import tkinter as tk
from tkinter import ttk
import json
import os
from gpiozero import LED, Button, Buzzer
from time import sleep

# GPIO setup
emergency_led = LED(17)
emergency_button = Button(18, pull_up=False)
buzzer = Buzzer(22)

# LCD setup (I2C, using freenove or iRasptek LCD library)
from RPLCD.i2c import CharLCD
lcd = CharLCD('PCF8574', 0x27)  # 0x27 typical address; run `i2cdetect -y 1` to confirm

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

        # Ensure WaysideInputs placeholder exists
        self.WaysideInputs = {}

        # Periodic update loop
        self.after(500, self.update_display)
        emergency_button.when_pressed = self.trigger_emergency

    def trigger_emergency(self):
        """Toggle emergency state."""
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

        # Load inputs file if present
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

        # Load PLC rules if PLC file exists
        if self.file_path_var.get() and os.path.exists(self.file_path_var.get()):
            try:
                with open(self.file_path_var.get(), "r") as plc:
                    plc_data = json.load(plc)
                    plc_rules = plc_data.get("rules", [])
            except Exception:
                plc_rules = []

        # Initialize commanded values from suggested defaults
        commanded_speed = suggestedSpeed
        commanded_authority = suggestedAuthority

        # Apply PLC rules (if any)
        for rule in plc_rules:
            target = rule.get("target", "")
            op = rule.get("op", "")
            value = rule.get("value", 0)

            if target == "commanded_speed":
                if op == "-":
                    commanded_speed = max(0, suggestedSpeed - value)
                else:
                    commanded_speed = suggestedSpeed
            elif target == "commanded_authority":
                if op == "-":
                    commanded_authority = max(0, suggestedAuthority - value)
                else:
                    commanded_authority = suggestedAuthority

        # Build outputs (no switches in HW-only view here)
        waysideOutputs = {
            "emergency": self.emergency_active,
            "commanded_speed": max(0, commanded_speed),
            "commanded_authority": max(0, commanded_authority),
        }

        # Write outputs file
        try:
            with open("WaysideOutputs_testUI.json", "w") as file:
                json.dump(waysideOutputs, file, indent=4)
        except Exception:
            pass

        # Update displayed values
        self.commandedSpeedLabel.config(text="Commanded Speed: " + str(waysideOutputs["commanded_speed"]) + " mph")
        self.commandedAuthorityLabel.config(text="Commanded Authority: " + str(waysideOutputs["commanded_authority"]) + " ft")
        self.emergencyStatusLabel.config(
            text="Emergency: " + ("ACTIVE" if waysideOutputs["emergency"] else "OFF"),
            foreground=("red" if waysideOutputs["emergency"] else "green")
        )

        self.WaysideInputs = waysideInputs

        # schedule next poll
        self.after(500, self.update_display)

if __name__ == "__main__":
    app = HWTrackControllerUI()
    app.mainloop()