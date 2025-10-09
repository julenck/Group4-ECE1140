import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import json
import os
import re


class TrackModelUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Track Model Software Module")
        self.geometry("1100x710")
        self.configure(bg="white")

        # === Track Layout Image === #
        left_frame = ttk.LabelFrame(self, text="Track Layout Interactive Diagram")
        left_frame.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)

        original_image = Image.open("track.png")
        resized_image = original_image.resize((550, 600), Image.Resampling.LANCZOS)
        self.track_image = ImageTk.PhotoImage(resized_image)
        ttk.Label(left_frame, image=self.track_image).pack(expand=True, padx=10, pady=10)

        ttk.Label(left_frame, text="Note: Not Drawn to Scale",
                  font=("Segoe UI", 9, "italic")).pack(pady=(0, 5))
        legend_frame = ttk.Frame(left_frame)
        legend_frame.pack(pady=5)
        ttk.Label(legend_frame, text="Train Live Position:").pack(side=tk.LEFT, padx=5)
        ttk.Label(legend_frame, text="Green Line", foreground="green").pack(side=tk.LEFT, padx=5)
        ttk.Label(legend_frame, text="Red Line", foreground="red").pack(side=tk.LEFT, padx=5)

        # === RIGHT PANEL === #
        right_frame = ttk.Frame(self)
        right_frame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)
        right_frame.grid_columnconfigure(0, weight=1)

        # --- Block Info --- #
        self.block_labels = {}
        block_frame = ttk.LabelFrame(right_frame, text="Currently Selected Block")
        block_frame.grid(row=0, column=0, sticky="EW", padx=5, pady=5)
        fields = ["Direction of Travel:", "Traffic Light:", "Speed Limit (mph):",
                  "Switch:", "Grade:", "Crossing:", "Station/Side:",
                  "Branching:", "Beacon:", "Elevation:"]
        self.block_labels = {f: tk.StringVar(value="N/A") for f in fields}

        for field in fields:
            frame = ttk.Frame(block_frame)
            frame.pack(anchor="w", pady=2)
            ttk.Label(frame, text=field, font=("Segoe UI", 10, "bold"), width=25).pack(side=tk.LEFT)
            ttk.Label(frame, textvariable=self.block_labels[field], font=("Segoe UI", 10)).pack(side=tk.LEFT)

        # --- Train Presence --- #
        presence_frame = ttk.Frame(right_frame)
        presence_frame.grid(row=1, column=0, sticky="EW", padx=5, pady=(5, 0))
        ttk.Label(presence_frame, text="Train Presence On:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=10)
        self.train_presence = tk.StringVar(value="Block F6 - GREEN")
        ttk.Label(presence_frame, textvariable=self.train_presence, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5)

        # --- Track Heating + Temperature --- #
        track_env_frame = ttk.Frame(right_frame)
        track_env_frame.grid(row=2, column=0, sticky="EW", padx=5, pady=5)
        ttk.Label(track_env_frame, text="Track Heating:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(10, 2))
        self.heating_status = ttk.Label(track_env_frame, text="OFF", foreground="red")
        self.heating_status.pack(side=tk.LEFT, padx=(0, 15))
        ttk.Label(track_env_frame, text="Environment Temperature (°F):",
                  font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        self.temperature = tk.IntVar(value=18)
        ttk.Button(track_env_frame, text="-", width=3, command=self.decrease_temp_immediate).pack(side=tk.LEFT, padx=2)
        ttk.Label(track_env_frame, textvariable=self.temperature,
                  font=("Segoe UI", 10), width=4, anchor="center").pack(side=tk.LEFT)
        ttk.Button(track_env_frame, text="+", width=3, command=self.increase_temp_immediate).pack(side=tk.LEFT, padx=2)

        # --- Totals --- #
        self.total_vars = {
            "Green Line": tk.StringVar(value="0"),
            "Red Line": tk.StringVar(value="0"),
            "Combined": tk.StringVar(value="0")
        }
        totals_frame = ttk.LabelFrame(right_frame, text="Total")
        totals_frame.grid(row=3, column=0, sticky="EW", padx=5, pady=5)
        for label, var in self.total_vars.items():
            frame = ttk.Frame(totals_frame)
            frame.pack(anchor="w", pady=2, padx=10)
            ttk.Label(frame, text=f"Total Blocks - {label}:", font=("Segoe UI", 10, "bold"), width=30).pack(side=tk.LEFT)
            ttk.Label(frame, textvariable=var, font=("Segoe UI", 10)).pack(side=tk.LEFT)

        # --- Failure Status --- #
        self.failure_vars = {
            "Power Failure": tk.BooleanVar(value=False),
            "Circuit Failure": tk.BooleanVar(value=False),
            "Broken Track": tk.BooleanVar(value=False)
        }
        failure_frame = ttk.LabelFrame(right_frame, text="Failure Status")
        failure_frame.grid(row=4, column=0, sticky="EW", padx=5, pady=5)
        for label, var in self.failure_vars.items():
            ttk.Checkbutton(failure_frame, text=label, variable=var,
                            command=self.update_failures).pack(anchor="w", padx=15, pady=2)
        self.warning_label = ttk.Label(
            failure_frame,
            text="All Systems Normal",
            font=("Segoe UI", 10, "italic"),
            foreground="green"
        )
        self.warning_label.pack(anchor="w", padx=15, pady=(5, 2))

        # --- Station Info --- #
        self.station_vars = {
            "Ticket Sales:": tk.StringVar(value="N/A"),
            "Boarding:": tk.StringVar(value="N/A"),
            "Train Occupancy:": tk.StringVar(value="N/A"),
            "Disembarking:": tk.StringVar(value="N/A")
        }
        station_frame = ttk.LabelFrame(right_frame, text="Station Information")
        station_frame.grid(row=5, column=0, sticky="EW", padx=5, pady=5)
        for label, var in self.station_vars.items():
            frame = ttk.Frame(station_frame)
            frame.pack(anchor="w", pady=2, padx=10)
            ttk.Label(frame, text=label, font=("Segoe UI", 10, "bold"), width=25).pack(side=tk.LEFT)
            ttk.Label(frame, textvariable=var, font=("Segoe UI", 10)).pack(side=tk.LEFT)

        # Track last boarding/disembarking values
        self.last_boarding = None
        self.last_disembarking = None

        # Begin loop
        self.load_json_data()

    # === JSON Reading / Detection Loop === #
    def load_json_data(self):
        if os.path.exists("track_model_state.json"):
            try:
                with open("track_model_state.json", "r") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    return

                block = data.get("block", {})
                env = data.get("environment", {})
                totals = data.get("totals", {})
                failures = data.get("failures", {})
                station = data.get("station", {})

                # --- Block Data ---
                self.block_labels["Direction of Travel:"].set(block.get("direction", "N/A"))
                self.block_labels["Traffic Light:"].set(block.get("traffic_light", "N/A"))
                self.block_labels["Speed Limit (mph):"].set(block.get("speed_limit", "N/A"))
                self.block_labels["Switch:"].set(block.get("switch", "N/A"))
                self.block_labels["Grade:"].set(f"{block.get('grade', 'N/A')}%")
                self.block_labels["Crossing:"].set(block.get("crossing", "N/A"))
                self.block_labels["Station/Side:"].set(block.get("station_side", "N/A"))
                branching_value = block.get("branching", "N/A")
                if isinstance(branching_value, list):
                    branching_value = ', '.join(branching_value) if branching_value else "N/A"
                self.block_labels["Branching:"].set(branching_value)
                self.block_labels["Beacon:"].set(block.get("beacon", "N/A"))
                self.block_labels["Elevation:"].set(f"{block.get('elevation', 'N/A')} ft")

                # --- Environment and Heating ---
                file_temp = env.get("temperature")
                if isinstance(file_temp, (int, float)):
                    self.temperature.set(file_temp)
                heating_on = block.get("track_heating", False)
                self.heating_status.config(
                    text="ON" if heating_on else "OFF",
                    foreground="green" if heating_on else "red"
                )

                # --- Totals ---
                self.total_vars["Green Line"].set(totals.get("green", 0))
                self.total_vars["Red Line"].set(totals.get("red", 0))
                self.total_vars["Combined"].set(totals.get("combined", 0))

                # --- Failures ---
                self.failure_vars["Power Failure"].set(failures.get("power", False))
                self.failure_vars["Circuit Failure"].set(failures.get("circuit", False))
                self.failure_vars["Broken Track"].set(failures.get("broken_track", False))

                active_failures = [n for n, v in self.failure_vars.items() if v.get()]
                if active_failures:
                    failure_list = ", ".join([n.lower() for n in active_failures])
                    self.warning_label.config(
                        text=f"Warning: System has {failure_list}",
                        foreground="orange",
                        font=("Segoe UI", 10, "italic")
                    )
                else:
                    self.warning_label.config(
                        text="All Systems Normal",
                        foreground="green",
                        font=("Segoe UI", 10, "italic")
                    )

                # --- Station Info ---
                boarding = station.get("boarding", 0)
                disembarking = station.get("disembarking", 0)
                self.station_vars["Ticket Sales:"].set(station.get("ticket_sales", "N/A"))
                self.station_vars["Boarding:"].set(boarding)
                self.station_vars["Disembarking:"].set(disembarking)
                self.station_vars["Train Occupancy:"].set(station.get("occupancy", "N/A"))

                # Detect if boarding/disembarking changed since last cycle
                if (self.last_boarding is not None and self.last_disembarking is not None):
                    if boarding != self.last_boarding or disembarking != self.last_disembarking:
                        # Trigger occupancy recalculation externally
                        self.update_occupancy(boarding, disembarking)

                # Store current state for next loop
                self.last_boarding = boarding
                self.last_disembarking = disembarking

            except Exception:
                pass

        self.after(500, self.load_json_data)

    # === Recalculate Occupancy (outside loop) === #
    def update_occupancy(self, boarding, disembarking):
        """Recalculate and store occupancy in JSON when boarding/disembarking change."""
        try:
            with open("track_model_state.json", "r") as f:
                data = json.load(f)
            station = data.get("station", {})
            occupancy_str = station.get("occupancy", "0/400")
            match = re.match(r"(\d+)", occupancy_str) if isinstance(occupancy_str, str) else None
            base_occupancy = int(match.group(1)) if match else 0

            new_occupancy = max(0, min(400, base_occupancy + boarding - disembarking))
            occupancy_text = f"{new_occupancy}/400 ({(new_occupancy / 400) * 100:.0f}%)"
            station["occupancy"] = occupancy_text
            data["station"] = station

            with open("track_model_state.json", "w") as f:
                json.dump(data, f, indent=4)

            self.station_vars["Train Occupancy:"].set(occupancy_text)
        except Exception:
            pass

    # === JSON Update Helpers === #
    def update_json(self):
        if not os.path.exists("track_model_state.json"):
            return
        try:
            with open("track_model_state.json", "r") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {}

            data.setdefault("environment", {})["temperature"] = self.temperature.get()
            data.setdefault("block", {})["track_heating"] = self.temperature.get() < 32
            data.setdefault("failures", {})
            data["failures"]["power"] = self.failure_vars["Power Failure"].get()
            data["failures"]["circuit"] = self.failure_vars["Circuit Failure"].get()
            data["failures"]["broken_track"] = self.failure_vars["Broken Track"].get()

            with open("track_model_state.json", "w") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    def increase_temp_immediate(self):
        self.temperature.set(self.temperature.get() + 1)
        self.update_heating_status()
        self.update_json()

    def decrease_temp_immediate(self):
        self.temperature.set(self.temperature.get() - 1)
        self.update_heating_status()
        self.update_json()

    def update_heating_status(self):
        if self.temperature.get() < 32:
            self.heating_status.config(text="ON", foreground="green")
        else:
            self.heating_status.config(text="OFF", foreground="red")

    def update_failures(self):
        self.update_json()


if __name__ == "__main__":
    app = TrackModelUI()
    app.mainloop()
