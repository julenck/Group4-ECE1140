import tkinter as tk
import os
print("Current working directory:", os.getcwd())
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import json


class TrainModelUI(tk.Tk):
    def __init__(self):
        super().__init__()

        # === Window setup ===
        self.title("Train Model Software Module")
        self.geometry("1100x750")

        # === Grid layout ===
        for i in range(3):
            self.grid_columnconfigure(i, weight=1, uniform="col")
        self.grid_rowconfigure(0, weight=3)
        self.grid_rowconfigure(1, weight=2)
        self.grid_rowconfigure(2, weight=0)

        # ===== Load Train Data =====
        try:
            with open("train_data.json", "r") as file:
                self.train_data = json.load(file)
        except FileNotFoundError:
            messagebox.showerror("Error", "train_data.json file not found.")
            self.train_data = {}

        # ===== Train Info Frame =====
        InfoFrame = ttk.LabelFrame(self, text="Train Information:")
        InfoFrame.grid(row=0, column=0, columnspan=2, sticky="NSEW", padx=10, pady=10)

        # --- Extract JSON data ---
        block = self.train_data.get("block", {})
        env = self.train_data.get("environment", {})
        failures = self.train_data.get("failures", {})
        station = self.train_data.get("station", {})

        # --- Left column (train and block info) ---
        self.currentStationLabel = ttk.Label(InfoFrame, text=f"Current Block: {block.get('name', 'N/A')}")
        self.currentStationLabel.grid(row=0, column=0, sticky="w", padx=10, pady=3)

        self.nextStationLabel = ttk.Label(InfoFrame, text=f"Direction: {block.get('direction', 'N/A')}")
        self.nextStationLabel.grid(row=1, column=0, sticky="w", padx=10, pady=3)

        self.etaLabel = ttk.Label(InfoFrame, text=f"Speed Limit: {block.get('speed_limit', 'N/A')} mph")
        self.etaLabel.grid(row=2, column=0, sticky="w", padx=10, pady=3)

        self.velocityLabel = ttk.Label(InfoFrame, text="Velocity: 48 mph")
        self.velocityLabel.grid(row=3, column=0, sticky="w", padx=10, pady=3)

        self.accelerationLabel = ttk.Label(InfoFrame, text="Acceleration: 1.2 mph/s")
        self.accelerationLabel.grid(row=4, column=0, sticky="w", padx=10, pady=3)

        self.temperatureLabel = ttk.Label(InfoFrame, text=f"Temperature: {env.get('temperature', 'N/A')} °C")
        self.temperatureLabel.grid(row=5, column=0, sticky="w", padx=10, pady=3)

        self.positionLabel = ttk.Label(InfoFrame, text=f"Beacon: {block.get('beacon', 'N/A')}")
        self.positionLabel.grid(row=6, column=0, sticky="w", padx=10, pady=3)

        self.heatingLabel = ttk.Label(InfoFrame, text=f"Track Heating: {block.get('track_heating', False)}")
        self.heatingLabel.grid(row=7, column=0, sticky="w", padx=10, pady=3)

        # --- Right column (station info) ---
        self.ticketSalesLabel = ttk.Label(InfoFrame, text=f"Ticket Sales: {station.get('ticket_sales', 0)}")
        self.ticketSalesLabel.grid(row=0, column=1, sticky="w", padx=10, pady=3)

        self.boardingLabel = ttk.Label(InfoFrame, text=f"Boarding: {station.get('boarding', 0)}")
        self.boardingLabel.grid(row=1, column=1, sticky="w", padx=10, pady=3)

        self.disembarkingLabel = ttk.Label(InfoFrame, text=f"Disembarking: {station.get('disembarking', 0)}")
        self.disembarkingLabel.grid(row=2, column=1, sticky="w", padx=10, pady=3)

        self.occupancyLabel = ttk.Label(InfoFrame, text=f"Occupancy: {station.get('occupancy', 'N/A')}")
        self.occupancyLabel.grid(row=3, column=1, sticky="w", padx=10, pady=3)

        # --- Emergency Brake Button ---
        self.emergencyButton = ttk.Button(InfoFrame, text="EMERGENCY BRAKE", command=self.activate_emergency)
        self.emergencyButton.grid(row=8, column=1, sticky="e", padx=10, pady=10)

        # ===== Map Frame =====
        MapFrame = ttk.LabelFrame(self, text="Track Map:")
        MapFrame.grid(row=0, column=2, sticky="NSEW", padx=10, pady=10)

        try:
            img = Image.open("map.png")
            img = img.resize((400, 300))
            self.map_img = ImageTk.PhotoImage(img)
            map_label = ttk.Label(MapFrame, image=self.map_img)
            map_label.pack(fill="both", expand=True)
        except FileNotFoundError:
            ttk.Label(MapFrame, text="Map image not found.").pack(pady=50)

        # ===== Failures =====
        FailureFrame = ttk.LabelFrame(self, text="Failures:")
        FailureFrame.grid(row=1, column=0, sticky="NSEW", padx=10, pady=10)
        ttk.Label(FailureFrame, text=f"Power Failure: {failures.get('power', False)}").pack(anchor="w")
        ttk.Label(FailureFrame, text=f"Circuit Failure: {failures.get('circuit', False)}").pack(anchor="w")
        ttk.Label(FailureFrame, text=f"Broken Track: {failures.get('broken_track', False)}").pack(anchor="w")

        # ===== Warnings =====
        WarningFrame = ttk.LabelFrame(self, text="Warnings:")
        WarningFrame.grid(row=1, column=1, sticky="NSEW", padx=10, pady=10)
        self.warningLabel = ttk.Label(WarningFrame, text="No Warnings")
        self.warningLabel.pack(pady=20)

        # ===== Announcements =====
        AnnouncementFrame = ttk.LabelFrame(self, text="Announcements:")
        AnnouncementFrame.grid(row=1, column=2, sticky="NSEW", padx=10, pady=10)
        self.announcementBox = tk.Text(AnnouncementFrame, height=5, width=40)
        self.announcementBox.insert("end", "Train approaching next station...\n")
        self.announcementBox.pack(fill="both", expand=True)

        # ===== Advertisement =====
        AdFrame = ttk.LabelFrame(self, text="Advertisements:")
        AdFrame.grid(row=2, column=0, columnspan=3, sticky="EW", padx=10, pady=10)
        self.adBox = tk.Text(AdFrame, height=3, width=100)
        self.adBox.insert("end", "Welcome aboard! Enjoy your ride.\n")
        self.adBox.insert("end", "Next stop: Steel Plaza — visit our station cafe for discounts!\n")
        self.adBox.pack(fill="both", expand=True)

    # ===== Functions =====
    def activate_emergency(self):
        self.warningLabel.config(text="EMERGENCY BRAKE ACTIVATED")
        messagebox.showwarning("Emergency Brake", "Emergency Brake has been activated!")


if __name__ == "__main__":
    app = TrainModelUI()
    app.mainloop()
