 #import tkinter and related libraries
import tkinter as tk
from tkinter import ttk, messagebox


class TrainModelUI(tk.Tk):
    def __init__(self):
        super().__init__()

        # Set window title and size
        self.title("Train Model Software Module")
        self.geometry("1000x600")

        # Configure grid layout
        for i in range(3):
            self.grid_columnconfigure(i, weight=1, uniform="col")
        for i in range(2):
            self.grid_rowconfigure(i, weight=1, uniform="row")

        # ===== Input Frame =====
        InputFrame = ttk.LabelFrame(self, text="Input Data:")
        InputFrame.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)

        self.commandedSpeedLabel = ttk.Label(InputFrame, text="Commanded Speed: 50 mph")
        self.commandedSpeedLabel.pack(pady=5)

        self.commandedAuthorityLabel = ttk.Label(InputFrame, text="Commanded Authority: 300 yds")
        self.commandedAuthorityLabel.pack(pady=5)

        self.beaconLabel = ttk.Label(InputFrame, text="Beacon Data: Next Station: A")
        self.beaconLabel.pack(pady=5)

        self.passengersBoardingLabel = ttk.Label(InputFrame, text="Passengers Boarding: 5")
        self.passengersBoardingLabel.pack(pady=5)

        # ===== Output Frame =====
        OutputFrame = ttk.LabelFrame(self, text="Output Data:")
        OutputFrame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)

        self.velocityLabel = ttk.Label(OutputFrame, text="Train Velocity: 48 mph")
        self.velocityLabel.pack(pady=5)

        self.temperatureLabel = ttk.Label(OutputFrame, text="Train Temperature: 67 °F")
        self.temperatureLabel.pack(pady=5)

        self.doorsLabel = ttk.Label(OutputFrame, text="Doors: Closed")
        self.doorsLabel.pack(pady=5)

        self.passageLightsLabel = ttk.Label(OutputFrame, text="Passage Lights: OFF")
        self.passageLightsLabel.pack(pady=5)

        self.passengersDisembarkingLabel = ttk.Label(OutputFrame, text="Passengers Disembarking: 3")
        self.passengersDisembarkingLabel.pack(pady=5)

        self.failureModeLabel = ttk.Label(OutputFrame, text="Failure Mode: None")
        self.failureModeLabel.pack(pady=5)

        # ===== Control Frame =====
        ControlFrame = ttk.LabelFrame(self, text="Controls:")
        ControlFrame.grid(row=0, column=2, sticky="NSEW", padx=10, pady=10)

        # Overhead Light toggle button
        self.lights_on = False
        self.lightsButton = ttk.Button(ControlFrame, text="Overhead Lights: OFF", command=self.toggle_lights)
        self.lightsButton.pack(pady=5)

        # Temperature feedback (expected temperature input)
        self.tempFeedbackLabel = ttk.Label(ControlFrame, text="Expected Temperature (°F):")
        self.tempFeedbackLabel.pack(pady=5)

        self.tempEntry = ttk.Entry(ControlFrame)
        self.tempEntry.pack(pady=2)

        self.tempSubmit = ttk.Button(ControlFrame, text="Submit", command=self.submit_temperature_feedback)
        self.tempSubmit.pack(pady=5)

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

    # ===== Functions =====
    def toggle_lights(self):
        """Toggle overhead lights ON/OFF."""
        self.lights_on = not self.lights_on
        state = "ON" if self.lights_on else "OFF"
        self.lightsButton.config(text=f"Overhead Lights: {state}")

    def submit_temperature_feedback(self):
        """Passenger enters expected temperature, feedback is sent to Train Controller."""
        try:
            expected_temp = int(self.tempEntry.get())
            messagebox.showinfo("Temperature Feedback", f"Passenger Expected Temperature: {expected_temp} °F")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid integer temperature!")

    def activate_emergency(self):
        """Activate emergency brake and show warning."""
        self.warningLabel.config(text="EMERGENCY BRAKE ACTIVATED")
        messagebox.showwarning("Emergency Brake", "Emergency Brake has been activated!")


if __name__ == "__main__":
    app = TrainModelUI()
    app.mainloop()
