import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import json
import pandas as pd
import os
import re


class TrackModelUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Track Model Software Module")
        self.geometry("1240x750")
        self.configure(bg="white")

        # === LEFT PANEL === #
        self.left_frame = ttk.LabelFrame(self, text="Track Layout Interactive Diagram")
        self.left_frame.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)

        self.track_label = ttk.Label(self.left_frame)
        self.track_label.pack(expand=True, padx=10, pady=10)

        ttk.Label(self.left_frame, text="Note: Not Drawn to Scale",
                  font=("Segoe UI", 9, "italic")).pack(pady=(0, 5))
        legend_frame = ttk.Frame(self.left_frame)
        legend_frame.pack(pady=5)
        ttk.Label(legend_frame, text="Train Live Position:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Label(legend_frame, text="★", foreground="gold", font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=3)

        # === RIGHT PANEL === #
        right_frame = ttk.Frame(self)
        right_frame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)
        right_frame.grid_columnconfigure(0, weight=1)

        # --- Upload / Line / Block --- #
        control_frame = ttk.LabelFrame(right_frame, text="Track Layout and Line Selection")
        control_frame.grid(row=0, column=0, sticky="EW", padx=5, pady=5)
        ttk.Button(control_frame, text="Upload Track Layout File", width=25,
                   command=self.upload_track_file).pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Label(control_frame, text="Select Line:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=5)

        # Initialize line selector empty; populate dynamically after upload
        self.line_selector = ttk.Combobox(control_frame, state="readonly", width=10, values=[])
        self.line_selector.pack(side=tk.LEFT, padx=5)
        self.line_selector.bind("<<ComboboxSelected>>", self.on_line_selected)

        ttk.Label(control_frame, text="Select Block:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.block_selector = ttk.Combobox(control_frame, state="readonly", width=10)
        self.block_selector.pack(side=tk.LEFT, padx=5)
        self.block_selector.bind("<<ComboboxSelected>>", self.on_block_selected)

        # --- Currently Selected Block --- #
        block_frame = ttk.LabelFrame(right_frame, text="Currently Selected Block")
        block_frame.grid(row=1, column=0, sticky="EW", padx=5, pady=5)
        block_frame.grid_columnconfigure(0, weight=1)
        block_frame.grid_columnconfigure(1, weight=1)

        left_fields = [
            "Line:", "Direction of Travel:", "Traffic Light:", "Gate:",
            "Speed Limit (mph):", "Grade (%):"
        ]
        right_fields = [
            "Elevation (M):", "Block Length (ft):", "Station:", "Switch Position:", "Crossing:", "Branching:"
        ]

        self.block_labels = {f: tk.StringVar(value="N/A") for f in (left_fields + right_fields)}

        # Left column
        left_col = ttk.Frame(block_frame)
        left_col.grid(row=0, column=0, sticky="NW", padx=5, pady=5)
        for field in left_fields:
            frame = ttk.Frame(left_col)
            frame.pack(anchor="w", pady=2, expand=False)
            ttk.Label(frame, text=field, font=("Segoe UI", 10, "bold"), width=25).pack(side=tk.LEFT)
            ttk.Label(frame, textvariable=self.block_labels[field], font=("Segoe UI", 10)).pack(side=tk.LEFT)

        # Right column
        right_col = ttk.Frame(block_frame)
        right_col.grid(row=0, column=1, sticky="NW", padx=5, pady=5)
        for field in right_fields:
            frame = ttk.Frame(right_col)
            frame.pack(anchor="w", pady=2, expand=False)
            ttk.Label(frame, text=field, font=("Segoe UI", 10, "bold"), width=25).pack(side=tk.LEFT)
            ttk.Label(frame, textvariable=self.block_labels[field], font=("Segoe UI", 10)).pack(side=tk.LEFT)

        # --- Block Information (Dynamic Fields) --- #
        dynamic_frame = ttk.LabelFrame(right_frame, text="Block Information")
        dynamic_frame.grid(row=2, column=0, sticky="EW", padx=5, pady=5)
        dyn_fields = ["Commanded Speed (mph):", "Commanded Authority (yards):", "Occupancy:"]
        self.dynamic_labels = {f: tk.StringVar(value="N/A") for f in dyn_fields}
        for field in dyn_fields:
            frame = ttk.Frame(dynamic_frame)
            frame.pack(anchor="w", pady=2)
            ttk.Label(frame, text=field, font=("Segoe UI", 10, "bold"), width=28).pack(side=tk.LEFT)
            ttk.Label(frame, textvariable=self.dynamic_labels[field], font=("Segoe UI", 10)).pack(side=tk.LEFT)

        # --- Environment Line --- #
        env_line = ttk.Frame(right_frame)
        env_line.grid(row=3, column=0, sticky="EW", padx=5, pady=(0, 5))
        ttk.Label(env_line, text="Track Heating:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(10, 2))
        self.heating_status = ttk.Label(env_line, text="OFF", foreground="red")
        self.heating_status.pack(side=tk.LEFT, padx=(0, 40))
        ttk.Label(env_line, text="Environment Temperature (°F):", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        self.temperature = tk.StringVar(value="N/A")
        ttk.Button(env_line, text="-", width=3, command=self.decrease_temp_immediate).pack(side=tk.LEFT, padx=2)
        ttk.Label(env_line, textvariable=self.temperature, font=("Segoe UI", 10), width=5, anchor="center").pack(side=tk.LEFT)
        ttk.Button(env_line, text="+", width=3, command=self.increase_temp_immediate).pack(side=tk.LEFT, padx=2)

        # --- Station Information --- #
        self.station_vars = {
            "Disembarking:": tk.StringVar(value="N/A")
        }
        station_frame = ttk.LabelFrame(right_frame, text="Station Information")
        station_frame.grid(row=4, column=0, sticky="EW", padx=5, pady=5)
        for label, var in self.station_vars.items():
            frame = ttk.Frame(station_frame)
            frame.pack(anchor="w", pady=2, padx=10)
            ttk.Label(frame, text=label, font=("Segoe UI", 10, "bold"), width=25).pack(side=tk.LEFT)
            ttk.Label(frame, textvariable=var, font=("Segoe UI", 10)).pack(side=tk.LEFT)

        # --- Failure Status --- #
        self.failure_vars = {
            "Power Failure": tk.BooleanVar(value=False),
            "Circuit Failure": tk.BooleanVar(value=False),
            "Broken Track": tk.BooleanVar(value=False)
        }
        failure_frame = ttk.LabelFrame(right_frame, text="Failure Status")
        failure_frame.grid(row=5, column=0, sticky="EW", padx=5, pady=5)
        for label, var in self.failure_vars.items():
            ttk.Checkbutton(failure_frame, text=label, variable=var,
                            command=self.update_failures).pack(anchor="w", padx=15, pady=2)
        self.warning_label = ttk.Label(failure_frame, text="All Systems Normal",
                                       font=("Segoe UI", 10, "italic"), foreground="green")
        self.warning_label.pack(anchor="w", padx=15, pady=(5, 2))

        # Internal Data
        self.static_data = {}
        self.block_selected = False
        self.load_json_data()

        # === Added check for pre-existing static.json === #
        self.check_existing_static_data()

    def check_existing_static_data(self):
        """Check if static JSON file already contains data and load it."""
        if not os.path.exists("track_model_static.json"):
            self.after(500, self.check_existing_static_data)
            return
        try:
            with open("track_model_static.json", "r") as f:
                data = json.load(f)
            static_data = data.get("static_data", {})
            if static_data:
                available_lines = list(static_data.keys())
                self.line_selector["values"] = available_lines
                if available_lines:
                    self.line_selector.current(0)
                    self.on_line_selected()
                    messagebox.showinfo("Success", "Track layout successfully loaded.")
            else:
                self.after(500, self.check_existing_static_data)
        except Exception:
            self.after(500, self.check_existing_static_data)

    def upload_track_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Track Layout File",
            filetypes=[("Excel Files", "*.xlsx *.xls")]
        )
        if not file_path:
            messagebox.showerror("No File Selected", "Please select a valid track layout file before continuing.")
            return

        try:
            xl = pd.ExcelFile(file_path)
            sheet_names = xl.sheet_names
            available_lines = [name.replace(" Line", "").strip() for name in sheet_names if name.endswith(" Line")]

            self.line_selector["values"] = available_lines
            if available_lines:
                self.line_selector.current(0)
            else:
                self.line_selector.set("")

            all_lines_data = {}
            for line in available_lines:
                df = pd.read_excel(file_path, sheet_name=f"{line} Line")
                df = df.fillna("N/A")
                df["Station"] = df["Infrastructure"].apply(self.extract_station)
                df["Crossing"] = df["Infrastructure"].apply(self.extract_crossing)
                df["Branching"] = df["Infrastructure"].apply(self.extract_branching)
                all_lines_data[line] = df.to_dict(orient="records")

            data = {
                "static_data": all_lines_data,
                "block": {},
                "environment": {},
                "station": {},
                "failures": {},
                "commanded": {}
            }

            with open("track_model_static.json", "w") as f:
                json.dump(data, f, indent=4)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to process Excel file:\n{e}")

    def extract_crossing(self, value):
        text = str(value).upper()
        if "RAILWAY CROSSING" in text:
            return "Yes"
        return "No"

    def extract_station(self, value):
        text = str(value).upper()
        match = re.search(r"STATION[:;]?\s*([A-Z\s]+)", text)
        return match.group(1).strip().title() if match else "N/A"

    def extract_branching(self, value):
        text = str(value).upper().strip()
        if "SWITCH TO YARD" in text or "SWITCH FROM YARD" in text:
            return "N/A"
        if "SWITCH" not in text:
            return "N/A"
        match = re.search(r"\(([^)]+)\)", text)
        if not match:
            return "N/A"
        contents = match.group(1)
        connected = [c.strip() for c in re.split(r"[;,]", contents) if c.strip()]
        if not connected:
            return "N/A"
        return ", ".join(connected)

    def on_line_selected(self, event=None):
        selected_line = self.line_selector.get()
        if not os.path.exists("track_model_static.json"):
            self.block_selector["values"] = []
            return
        self.load_static_after_upload(selected_line)
        self.update_track_image()

    def load_static_after_upload(self, selected_line):
        if not os.path.exists("track_model_static.json"):
            return
        with open("track_model_static.json", "r") as f:
            data = json.load(f)
        records = data.get("static_data", {}).get(selected_line, [])
        self.static_data = records
        blocks = [f"{r['Section']}{int(float(r['Block Number']))}" for r in records if
                  str(r['Block Number']).replace('.', '', 1).isdigit()]
        self.block_selector["values"] = blocks
        if blocks:
            self.block_selector.current(0)
            self.on_block_selected(None)

    def update_track_image(self, event=None):
        selected_line = self.line_selector.get().lower()
        image_file = "track.png" if selected_line != "blue" else "track_blue.png"
        try:
            img = Image.open(image_file)
            resized = img.resize((550, 600), Image.Resampling.LANCZOS)
            self.track_image = ImageTk.PhotoImage(resized)
            self.track_label.config(image=self.track_image)
        except Exception:
            self.track_label.config(text="Unable to load track image")

    def on_block_selected(self, event=None):
        self.block_selected = True
        block_id = self.block_selector.get()
        if not self.static_data:
            return
        for b in self.static_data:
            identifier = f"{b['Section']}{int(float(b['Block Number']))}"
            if identifier == block_id:
                kmh = b.get("Speed Limit (Km/Hr)", 0)
                mph = round(float(kmh) * 0.621371, 2) if isinstance(kmh, (int, float)) else "N/A"
                meters = b.get("Block Length (m)", 0)
                feet = round(float(meters) * 3.28084, 2) if isinstance(meters, (int, float)) else "N/A"
                self.block_labels["Line:"].set(b.get("Line", "N/A"))
                self.block_labels["Speed Limit (mph):"].set(mph)
                self.block_labels["Grade (%):"].set(b.get("Block Grade (%)", "N/A"))
                self.block_labels["Elevation (M):"].set(b.get("ELEVATION (M)", "N/A"))
                self.block_labels["Block Length (ft):"].set(feet)
                self.block_labels["Station:"].set(b.get("Station", "N/A"))
                self.block_labels["Switch Position:"].set("N/A")
                self.block_labels["Crossing:"].set(b.get("Crossing", "N/A"))
                self.block_labels["Branching:"].set(b.get("Branching", "N/A"))
                break

    def load_json_data(self):
        if not os.path.exists("track_model_state.json"):
            self.after(500, self.load_json_data)
            return

        try:
            selected_line = self.line_selector.get()
            selected_block = self.block_selector.get()

            if not selected_line or not selected_block:
                self.after(500, self.load_json_data)
                return

            with open("track_model_state.json", "r") as f:
                data = json.load(f)

            line_data = data.get(selected_line, {})
            block_data = line_data.get(selected_block, {})

            block = block_data.get("block", {})
            env = block_data.get("environment", {})
            failures = block_data.get("failures", {})
            station = block_data.get("station", {})
            commanded = block_data.get("commanded", {})

            temp = env.get("temperature", 0)
            occupancy = block.get("occupancy", "NA")
            authority = commanded.get("authority", "NA")
            speed = commanded.get("speed", "NA")
            light_input = block.get("light", "N/A")
            gate_input = block.get("gate", "N/A")

            switch_position = block_data.get("switch_position", "N/A")
            branching_value = next(
                (b["Branching"] for b in self.static_data if f"{b['Section']}{int(float(b['Block Number']))}" == selected_block),
                "No"
            )
            if branching_value in ["No", "N/A", "To/From Yard"]:
                switch_position = "N/A"
            self.block_labels["Switch Position:"].set(switch_position)

            failures_active = any(failures.values())
            heating_on = temp < 32

            if failures.get("power"):
                traffic_light = "OFF"
                crossing_value = next(
                    (b["Crossing"] for b in self.static_data
                     if f"{b['Section']}{int(float(b['Block Number']))}" == selected_block),
                    "No"
                )
                gate_status = "Closed" if crossing_value == "Yes" else "N/A"

            elif failures.get("circuit"):
                occupancy = 0
                displayed_occupancy = "--"
                if authority > 0:
                    traffic_light = "Green"
                    gate_status = "Open"
                else:
                    traffic_light = "Red"
                    gate_status = "Open"

            elif failures.get("broken_track"):
                authority = 0
                speed = 0
                traffic_light = "Red"
                crossing_value = next(
                    (b["Crossing"] for b in self.static_data
                     if f"{b['Section']}{int(float(b['Block Number']))}" == selected_block),
                    "No"
                )
                gate_status = "Closed" if crossing_value == "Yes" else "N/A"

            #elif occupancy:
                #traffic_light = "Yellow"
                #gate_status = "Closed"

            else:
                traffic_light = light_input
                gate_status = gate_input

            self.block_labels["Direction of Travel:"].set("--")
            self.block_labels["Traffic Light:"].set(traffic_light)
            self.block_labels["Gate:"].set(gate_status)
            self.dynamic_labels["Commanded Speed (mph):"].set(speed)
            self.dynamic_labels["Commanded Authority (yards):"].set(authority)
            self.dynamic_labels["Occupancy:"].set("OCCUPIED" if occupancy else "CLEAR")

            self.temperature.set(str(temp))
            self.heating_status.config(
                text="ON" if heating_on else "OFF",
                foreground="green" if heating_on else "red"
            )

            # Boarding removed
            self.station_vars["Disembarking:"].set(station.get("disembarking", "N/A"))

            for key in self.failure_vars:
                state_key = key.split()[0].lower()
                self.failure_vars[key].set(failures.get(state_key, False))

            if failures_active:
                active = []
                if failures.get("power"):
                    active.append("Power Failure")
                if failures.get("circuit"):
                    active.append("Circuit Failure")
                if failures.get("broken_track"):
                    active.append("Broken Track Failure")
                failure_text = ", ".join(active)
                self.warning_label.config(
                    text=f"Warning: Active Failure - {failure_text}",
                    foreground="orange"
                )
            else:
                self.warning_label.config(text="All Systems Normal", foreground="green")

        except Exception:
            pass

        self.after(500, self.load_json_data)

    def increase_temp_immediate(self):
        try:
            current_temp = float(self.temperature.get())
        except ValueError:
            current_temp = 0
        self.temperature.set(str(int(current_temp + 1)))
        self.update_json_temperature()

    def decrease_temp_immediate(self):
        try:
            current_temp = float(self.temperature.get())
        except ValueError:
            current_temp = 0
        self.temperature.set(str(int(current_temp - 1)))
        self.update_json_temperature()

    def update_json_temperature(self):
        if not os.path.exists("track_model_state.json"):
            return
        try:
            with open("track_model_state.json", "r") as f:
                data = json.load(f)
            selected_line = self.line_selector.get()
            selected_block = self.block_selector.get()
            temp = self.temperature.get()

            data.setdefault(selected_line, {})
            data[selected_line].setdefault(selected_block, {})
            data[selected_line][selected_block].setdefault("environment", {})
            data[selected_line][selected_block]["environment"]["temperature"] = temp


            with open("track_model_state.json", "w") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    def update_failures(self):
        if not os.path.exists("track_model_state.json"):
            return
        try:
            with open("track_model_state.json", "r") as f:
                data = json.load(f)
            selected_line = self.line_selector.get()
            selected_block = self.block_selector.get()
            if selected_line and selected_block:

                data.setdefault(selected_line, {})
                data[selected_line].setdefault(selected_block, {})
                data[selected_line][selected_block].setdefault("failures", {})
                data[selected_line][selected_block]["failures"]["power"] = self.failure_vars["Power Failure"].get()
                data[selected_line][selected_block]["failures"]["circuit"] = self.failure_vars["Circuit Failure"].get()
                data[selected_line][selected_block]["failures"]["broken_track"] = self.failure_vars["Broken Track"].get()
                with open("track_model_state.json", "w") as f:
                    json.dump(data, f, indent=4)
        except Exception:
            pass


if __name__ == "__main__":
    app = TrackModelUI()
    app.mainloop()

    if os.path.exists("track_model_static.json"):
        with open("track_model_static.json", "w") as f:
            json.dump({}, f, indent=4)
