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
emergency_led = LED(27)
emergency_button = Button(17, pull_up=False)
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

        # GUI label for hardware state
        self.commandedSpeedLabel = ttk.Label(self, text="Commanded Speed: N/A")
        self.commandedSpeedLabel.pack(pady=10)

        self.commandedAuthorityLabel = ttk.Label(self, text="Commanded Authority: N/A")
        self.commandedAuthorityLabel.pack(pady=10)

        self.emergencyStatusLabel = ttk.Label(self, text="Emergency: OFF", foreground="green")
        self.emergencyStatusLabel.pack(pady=20)

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
        """Update speed/authority values from JSON and LCD."""
        if os.path.exists("WaysideOutputs_testUI.json"):
            with open("WaysideOutputs_testUI.json", "r") as f:
                data = json.load(f)

            commanded_speed = data.get("commanded_speed", 0)
            commanded_authority = data.get("commanded_authority", 0)

            # Update labels
            self.commandedSpeedLabel.config(text=f"Commanded Speed: {commanded_speed} mph")
            self.commandedAuthorityLabel.config(text=f"Commanded Authority: {commanded_authority} ft")

            # Update LCD
            lcd.clear()
            lcd.write_string(f"Speed: {commanded_speed} mph")
            lcd.crlf()
            lcd.write_string(f"Auth: {commanded_authority} ft")

        self.after(500, self.update_display)

if __name__ == "__main__":
    app = HWTrackControllerUI()
    app.mainloop()