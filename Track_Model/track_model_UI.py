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
        self.geometry("1240x820")
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
        ttk.Label(legend_frame, text="Train Live Position:").pack(side=tk.LEFT, padx=5)
        ttk.Label(legend_frame, text="Green Line", foreground="green").pack(side=tk.LEFT, padx=5)
        ttk.Label(legend_frame, text="Red Line", foreground="red").pack(side=tk.LEFT, padx=5)

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
        self.line_selector = ttk.Combobox(control_frame, state="readonly", width=10,
                                          values=["Red", "Green", "Blue"])
        self.line_selector.pack(side=tk.LEFT, padx=5)
        self.line_selector.bind("<<ComboboxSelected>>", self.on_line_selected)
        ttk.Label(control_frame, text="Select Block:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.block_selector = ttk.Combobox(control_frame, state="readonly", width=10)
        self.block_selector.pack(side=tk.LEFT, padx=5)
        self.block_selector.bind("<<ComboboxSelected>>", self.on_block_selected)

        # --- Currently Selected Block (2-column layout) --- #
        block_frame = ttk.LabelFrame(right_frame, text="Currently Selected Block")
        block_frame.grid(row=1, column=0, sticky="EW", padx=5, pady=5)
        block_frame.grid_columnconfigure(0, weight=1)
        block_frame.grid_columnconfigure(1, weight=1)

        left_fields = [
            "Line:", "Direction of Travel:", "Traffic Light:", "Gate:",
            "Speed Limit (mph):", "Grade (%):"
        ]
        right_fields = [
            "Elevation (M):", "Block Length (ft):", "Station:", "Switch:", "Crossing:", "Branching:"
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

        # --- Environment Line (aligned properly, extra spacing) --- #
        env_line = ttk.Frame(right_frame)
        env_line.grid(row=3, column=0, sticky="EW", padx=5, pady=(0, 5))

        ttk.Label(env_line, text="Track Heating:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(10, 2))
        self.heating_status = ttk.Label(env_line, text="OFF", foreground="red")
        self.heating_status.pack(side=tk.LEFT, padx=(0, 40))  # increased spacing here

        ttk.Label(env_line, text="Environment Temperature (°F):", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        self.temperature = tk.IntVar(value=18)
        ttk.Button(env_line, text="-", width=3, command=self.decrease_temp_immediate).pack(side=tk.LEFT, padx=2)
        ttk.Label(env_line, textvariable=self.temperature, font=("Segoe UI", 10), width=5, anchor="center").pack(side=tk.LEFT)
        ttk.Button(env_line, text="+", width=3, command=self.increase_temp_immediate).pack(side=tk.LEFT, padx=2)

        # --- Station Information --- #
        self.station_vars = {
            "Boarding:": tk.StringVar(value="N/A"),
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

    # === Upload Excel File === #
    def upload_track_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Track Layout File",
            filetypes=[("Excel Files", "*.xlsx *.xls")]
        )

        if not file_path:
            messagebox.showerror("No File Selected", "Please select a valid track layout file before continuing.")
            return

        selected_line = self.line_selector.get()
        if not selected_line:
            messagebox.showerror("No Line Selected", "Please select a line (Red, Green, or Blue) before loading.")
            return

        try:
            df = pd.read_excel(file_path, sheet_name=f"{selected_line} Line")
            required_cols = [
                "Line", "Section", "Block Number", "Block Length (m)",
                "Block Grade (%)", "Speed Limit (Km/Hr)", "Infrastructure",
                "ELEVATION (M)"
            ]
            for col in required_cols:
                if col not in df.columns:
                    messagebox.showerror("Invalid File", f"Missing required column: {col}")
                    return

            df = df.fillna("N/A")
            df["Station"] = df["Infrastructure"].apply(self.extract_station)
            df["Switch"] = df["Infrastructure"].apply(self.extract_switch)
            df["Crossing"] = df["Infrastructure"].apply(lambda x: "Yes" if "CROSSING" in str(x).upper() else "No")
            df["Branching"] = df["Infrastructure"].apply(self.extract_branching)
            static_data = df.to_dict(orient="records")

            all_lines_data = {selected_line: static_data}
            for line in ["Red", "Green", "Blue"]:
                if line == selected_line:
                    continue
                try:
                    alt_df = pd.read_excel(file_path, sheet_name=f"{line} Line")
                    alt_df = alt_df.fillna("N/A")
                    alt_df["Station"] = alt_df["Infrastructure"].apply(self.extract_station)
                    alt_df["Switch"] = alt_df["Infrastructure"].apply(self.extract_switch)
                    alt_df["Crossing"] = alt_df["Infrastructure"].apply(lambda x: "Yes" if "CROSSING" in str(x).upper() else "No")
                    alt_df["Branching"] = alt_df["Infrastructure"].apply(self.extract_branching)
                    all_lines_data[line] = alt_df.to_dict(orient="records")
                except Exception:
                    continue

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

            messagebox.showinfo("Success", f"Track layout for all lines loaded. Displaying {selected_line} line.")
            self.load_static_after_upload(selected_line)

        except ValueError:
            messagebox.showerror("Invalid Sheet", f"The Excel file does not contain a sheet named '{selected_line} Line'.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process Excel file:\n{e}")

    # === Infrastructure Parsing === #
    def extract_station(self, value):
        text = str(value).upper()
        match = re.search(r"STATION[:;]?\s*([A-Z\s]+)", text)
        return match.group(1).strip().title() if match else "N/A"

    def extract_switch(self, value):
        text = str(value).upper()
        match = re.search(r"SWITCH\s*\(([^)]+)\)", text)
        return match.group(1).strip() if match else ("Yard" if "YARD" in text else "N/A")

    def extract_branching(self, value):
        text = str(value).upper()
        if "YARD" in text:
            return "To/From Yard"
        elif "SWITCH" in text:
            return "Yes"
        return "No"

    # === Reload on Line Change === #
    def on_line_selected(self, event=None):
        selected_line = self.line_selector.get()
        if os.path.exists("track_model_static.json"):
            self.load_static_after_upload(selected_line)
        self.update_track_image()

    # === Load Static Data After Upload === #
    def load_static_after_upload(self, selected_line):
        if not os.path.exists("track_model_static.json"):
            return
        with open("track_model_static.json", "r") as f:
            data = json.load(f)
        records = data.get("static_data", {}).get(selected_line, [])
        self.static_data = records
        blocks = [f"{r['Section']}{int(float(r['Block Number']))}" for r in records if str(r['Block Number']).replace('.', '', 1).isdigit()]
        self.block_selector["values"] = blocks
        if blocks:
            self.block_selector.current(0)
            self.on_block_selected(None)

    # === Track Image === #
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

    # === Block Selection === #
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
                self.block_labels["Switch:"].set(b.get("Switch", "N/A"))
                self.block_labels["Crossing:"].set(b.get("Crossing", "N/A"))
                self.block_labels["Branching:"].set(b.get("Branching", "N/A"))
                break

    # === Dynamic Data Update Loop === #
    def load_json_data(self):
        if not self.block_selected or not os.path.exists("track_model_state.json"):
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

            direction = block.get("direction", "Forward")
            temp = env.get("temperature", 0)
            occupancy = block.get("occupancy", 0)
            authority = commanded.get("authority", 0)
            speed = commanded.get("speed", 0)
            any_failure = any(failures.values())

            heating_on = temp < 32
            if any_failure:
                traffic_light = "Red"
                gate_status = "Closed"
            elif occupancy:
                traffic_light = "Yellow"
                gate_status = "Closed"
            elif authority > 0:
                traffic_light = "Green"
                gate_status = "Open"
            else:
                traffic_light = "Red"
                gate_status = "Open"

            self.block_labels["Direction of Travel:"].set(direction)
            self.block_labels["Traffic Light:"].set(traffic_light)
            self.block_labels["Gate:"].set(gate_status)
            self.dynamic_labels["Commanded Speed (mph):"].set(speed)
            self.dynamic_labels["Commanded Authority (yards):"].set(authority)
            self.dynamic_labels["Occupancy:"].set("OCCUPIED" if occupancy else "CLEAR")

            # Correctly reflect environment temperature
            self.temperature.set(temp)
            self.heating_status.config(
                text="ON" if heating_on else "OFF",
                foreground="green" if heating_on else "red"
            )

            self.station_vars["Boarding:"].set(station.get("boarding", "N/A"))
            self.station_vars["Disembarking:"].set(station.get("disembarking", "N/A"))

            for key in self.failure_vars:
                state_key = key.split()[0].lower()
                self.failure_vars[key].set(failures.get(state_key, False))

            if any_failure:
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

    # === Temperature Controls === #
    def increase_temp_immediate(self):
        self.temperature.set(self.temperature.get() + 1)
        self.update_json_temperature()

    def decrease_temp_immediate(self):
        self.temperature.set(self.temperature.get() - 1)
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

            # Write to nested JSON
            if selected_line in data and selected_block in data[selected_line]:
                data[selected_line][selected_block]["environment"]["temperature"] = temp

            with open("track_model_state.json", "w") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    # === Failure Update === #
    def update_failures(self):
        if not os.path.exists("track_model_state.json"):
            return
        try:
            with open("track_model_state.json", "r") as f:
                data = json.load(f)
            data.setdefault("failures", {})
            data["failures"]["power"] = self.failure_vars["Power Failure"].get()
            data["failures"]["circuit"] = self.failure_vars["Circuit Failure"].get()
            data["failures"]["broken_track"] = self.failure_vars["Broken Track"].get()
            with open("track_model_state.json", "w") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass


if __name__ == "__main__":
    try:
        with open("track_model_static.json", "w") as f:
            json.dump({}, f, indent=4)
    except Exception:
        pass

    app = TrackModelUI()
    app.mainloop()
