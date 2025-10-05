 #import tkinter and related libraries
import tkinter as tk
from tkinter import ttk, messagebox


class TrainModelUI(tk.Tk):
    def __init__(self):
        super().__init__()

        # === Window setup ===
        self.title("Train Model Software Module")
        self.geometry("1000x700")

        # === Grid layout ===
        for i in range(3):
            self.grid_columnconfigure(i, weight=1, uniform="col")
        self.grid_rowconfigure(0, weight=3)
        self.grid_rowconfigure(1, weight=2)
        self.grid_rowconfigure(2, weight=0)

        # ===== Train Info Frame =====
        InfoFrame = ttk.LabelFrame(self, text="Train Information:")
        InfoFrame.grid(row=0, column=0, columnspan=3, sticky="NSEW", padx=10, pady=10)

        # --- Row 0: Station Info ---
        self.currentStationLabel = ttk.Label(InfoFrame, text="Current Station:")
        self.currentStationLabel.grid(row=0, column=0, sticky="w", padx=10, pady=3)

        self.nextStationLabel = ttk.Label(InfoFrame, text="Next Station:")
        self.nextStationLabel.grid(row=1, column=0, sticky="w", padx=10, pady=3)

        self.etaLabel = ttk.Label(InfoFrame, text="ETA:  minutes")
        self.etaLabel.grid(row=2, column=0, sticky="w", padx=10, pady=3)

        # --- Row 3-6: Train Dynamics ---
        self.velocityLabel = ttk.Label(InfoFrame, text="Velocity: 48 mph")
        self.velocityLabel.grid(row=3, column=0, sticky="w", padx=10, pady=3)

        self.accelerationLabel = ttk.Label(InfoFrame, text="Acceleration: 1.2 mph/s")
        self.accelerationLabel.grid(row=4, column=0, sticky="w", padx=10, pady=3)

        self.temperatureLabel = ttk.Label(InfoFrame, text="Temperature: 67 °F")
        self.temperatureLabel.grid(row=5, column=0, sticky="w", padx=10, pady=3)

        self.doorsLabel = ttk.Label(InfoFrame, text="Doors: Closed")
        self.doorsLabel.grid(row=6, column=0, sticky="w", padx=10, pady=3)

        self.lightsLabel = ttk.Label(InfoFrame, text="Lights: ON")
        self.lightsLabel.grid(row=7, column=0, sticky="w", padx=10, pady=3)

        self.positionLabel = ttk.Label(InfoFrame, text="Position: Block #23")
        self.positionLabel.grid(row=8, column=0, sticky="w", padx=10, pady=3)

        # --- Row 0-3 Right: Physical Dimensions ---
        self.lengthLabel = ttk.Label(InfoFrame, text="Length: 66 ft")
        self.lengthLabel.grid(row=0, column=1, sticky="w", padx=10, pady=3)

        self.widthLabel = ttk.Label(InfoFrame, text="Width: 10 ft")
        self.widthLabel.grid(row=1, column=1, sticky="w", padx=10, pady=3)

        self.heightLabel = ttk.Label(InfoFrame, text="Height: 11.5 ft")
        self.heightLabel.grid(row=2, column=1, sticky="w", padx=10, pady=3)

        self.massLabel = ttk.Label(InfoFrame, text="Mass: 91 lb")
        self.massLabel.grid(row=3, column=1, sticky="w", padx=10, pady=3)

        # --- Row 4-5 Right: People Info ---
        self.crewLabel = ttk.Label(InfoFrame, text="Crew Count: 2")
        self.crewLabel.grid(row=4, column=1, sticky="w", padx=10, pady=3)

        self.passengerLabel = ttk.Label(InfoFrame, text="Passengers: 80")
        self.passengerLabel.grid(row=5, column=1, sticky="w", padx=10, pady=3)

        # --- Emergency Brake ---
        self.emergencyButton = ttk.Button(InfoFrame, text="EMERGENCY BRAKE", command=self.activate_emergency)
        self.emergencyButton.grid(row=8, column=1, sticky="e", padx=10, pady=10)

        # ===== Announcements Frame =====
        AnnouncementFrame = ttk.LabelFrame(self, text="Announcements:")
        AnnouncementFrame.grid(row=1, column=0, sticky="NSEW", padx=10, pady=10)

        self.announcementBox = tk.Text(AnnouncementFrame, height=5, width=40)
        self.announcementBox.insert("end", "Train is approaching next station...\n")
        self.announcementBox.pack(fill="both", expand=True)

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

        # ===== Advertisement Frame =====
        AdFrame = ttk.LabelFrame(self, text="Advertisements:")
        AdFrame.grid(row=2, column=0, columnspan=3, sticky="EW", padx=10, pady=10)

        self.adBox = tk.Text(AdFrame, height=3, width=100)
        self.adBox.insert("end", "Welcome aboard! Enjoy your ride.\n")
        self.adBox.insert("end", "Next stop: Steel Plaza — visit our station cafe for discounts!\n")
        self.adBox.pack(fill="both", expand=True)


    # ===== Functions =====
    def activate_emergency(self):
        """Activate emergency brake and show warning."""
        self.warningLabel.config(text="EMERGENCY BRAKE ACTIVATED")
        messagebox.showwarning("Emergency Brake", "Emergency Brake has been activated!")


if __name__ == "__main__":
    app = TrainModelUI()
    app.mainloop()
