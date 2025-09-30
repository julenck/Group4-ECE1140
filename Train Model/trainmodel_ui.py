#import tkinter and related libraries
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import json
import os

# Window size
WindowWidth = 1200
WindowHeight = 700

class TrainModelUI(tk.Tk):
    def __init__(self):
        super().__init__()

        # Set window title and size
        self.title("Train Model Software Module")
        self.geometry(f"{WindowWidth}x{WindowHeight}")

        # Configure grid layout (3 columns, 2 rows)
        for i in range(3):
            self.grid_columnconfigure(i, weight=1, uniform="col")
        for i in range(2):
            self.grid_rowconfigure(i, weight=1, uniform="row")

        # ===== Input Frame =====
        InputFrame = ttk.LabelFrame(self, text="Input Data:")
        InputFrame.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)

        self.commandedSpeedLabel = ttk.Label(InputFrame, text="Commanded Speed: N/A")
        self.commandedSpeedLabel.pack(pady=5)

        self.commandedAuthorityLabel = ttk.Label(InputFrame, text="Commanded Authority: N/A")
        self.commandedAuthorityLabel.pack(pady=5)

        self.beaconLabel = ttk.Label(InputFrame, text="Beacon Data: N/A")
        self.beaconLabel.pack(pady=5)

        self.passengersBoardingLabel = ttk.Label(InputFrame, text="Passengers Boarding: N/A")
        self.passengersBoardingLabel.pack(pady=5)

        # ===== Output Frame =====
        OutputFrame = ttk.LabelFrame(self, text="Output Data:")
        OutputFrame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)

        self.velocityLabel = ttk.Label(OutputFrame, text="Train Velocity: N/A")
        self.velocityLabel.pack(pady=5)

        self.temperatureLabel = ttk.Label(OutputFrame, text="Train Temperature: N/A")
        self.temperatureLabel.pack(pady=5)

        self.passengersDisembarkingLabel = ttk.Label(OutputFrame, text="Passengers Disembarking: N/A")
        self.passengersDisembarkingLabel.pack(pady=5)

        self.failureModeLabel = ttk.Label(OutputFrame, text="Failure Mode: None")
        self.failureModeLabel.pack(pady=5)

        # ===== Control Frame =====
        ControlFrame = ttk.LabelFrame(self, text="Controls:")
        ControlFrame.grid(row=0, column=2, sticky="NSEW", padx=10, pady=10)

        # Light control
        self.lightsOn = tk.BooleanVar(value=False)
        self.lightsButton = ttk.Checkbutton(ControlFrame, text="Lights (ON/OFF)", variable=self.lightsOn)
        self.lightsButton.pack(pady=5)

        # Door control
        self.doorsOpen = tk.BooleanVar(value=False)
        self.doorButton = ttk.Checkbutton(ControlFrame, text="Doors (Open/Closed)", variable=self.doorsOpen)
        self.doorButton.pack(pady=5)

        # Temperature setting
        self.tempEntry = ttk.Entry(ControlFrame)
        self.tempEntry.pack(pady=5)
        self.tempButton = ttk.Button(ControlFrame, text="Set Temperature", command=self.set_temperature)
        self.tempButton.pack(pady=5)

        # Emergency brake button
        self.emergencyButton = ttk.Button(ControlFrame, text="EMERGENCY BRAKE", command=self.activate_emergency)
        self.emergencyButton.pack(pady=10)

        # ===== Announcement Frame =====
        AnnouncementFrame = ttk.LabelFrame(self, text="Announcements:")
        AnnouncementFrame.grid(row=1, column=0, sticky="NSEW", padx=10, pady=10)

        self.announcementBox = tk.Text(AnnouncementFrame, height=5, width=40)
        self.announcementBox.insert("end", "Train is approaching next station...\n")
        self.announcementBox.pack()

        # ===== Failure Status Frame =====
        FailureFrame = ttk.LabelFrame(self, text="Failure Status:")
        FailureFrame.grid(row=1, column=1, sticky="NSEW", padx=10, pady=10)

        self.engineFailure = tk.BooleanVar(value=False)
        ttk.Checkbutton(FailureFrame, text="Engine Failure", variable=self.engineFailure).pack(anchor="w")

        self.signalFailure = tk.BooleanVar(value=False)
        ttk.Checkbutton(FailureFrame, text="Signal Pickup Failure", variable=self.signalFailure).pack(anchor="w")

        self.brakeFailure = tk.BooleanVar(value=False)
        ttk.Checkbutton(FailureFrame, text="Brake Failure", variable=self.brakeFailure).pack(anchor="w")

        # ===== Warnings Frame =====
        WarningFrame = ttk.LabelFrame(self, text="Warnings:")
        WarningFrame.grid(row=1, column=2, sticky="NSEW", padx=10, pady=10)

        self.warningLabel = ttk.Label(WarningFrame, text="No Warnings")
        self.warningLabel.pack(pady=20)

        # Auto-refresh every second
        self.after(1000, self.update_UI)

    # ===== Functions =====
    def set_temperature(self):
        """Set train cabin temperature from user entry."""
        try:
            t = int(self.tempEntry.get())
            self.temperatureLabel.config(text=f"Train Temperature: {t} °F")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid integer temperature!")

    def activate_emergency(self):
        """Activate emergency brake and show warning."""
        self.warningLabel.config(text="EMERGENCY BRAKE ACTIVATED")
        messagebox.showwarning("Emergency Brake", "Emergency Brake has been activated!")

    def update_UI(self):
        """Update input/output values periodically (example values)."""
        # Example data
        commanded_speed = 50
        commanded_authority = 300
        beacon = "Next Station: A"
        boarding = 5
        velocity = 48
        disembarking = 3

        # Update input labels
        self.commandedSpeedLabel.config(text=f"Commanded Speed: {commanded_speed} mph")
        self.commandedAuthorityLabel.config(text=f"Commanded Authority: {commanded_authority} yds")
        self.beaconLabel.config(text=f"Beacon Data: {beacon}")
        self.passengersBoardingLabel.config(text=f"Passengers Boarding: {boarding}")

        # Update output labels
        self.velocityLabel.config(text=f"Train Velocity: {velocity} mph")
        self.passengersDisembarkingLabel.config(text=f"Passengers Disembarking: {disembarking}")

        # Refresh again after 1s
        self.after(1000, self.update_UI)


if __name__ == "__main__":
    app = TrainModelUI()
    app.mainloop()
