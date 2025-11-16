import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from Track_Visualizer import RailwayDiagram
from DynamicBlockManager import DynamicBlockManager
from PIL import Image, ImageTk
import json
import pandas as pd
import os
import re


class TrackModelUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Track Model Software Module")
        self.geometry("1700x950")
        self.configure(bg="white")
        self.block_manager = DynamicBlockManager()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=5)  # Left panel gets more space
        self.grid_columnconfigure(1, weight=1)  # Right panel

        # === LEFT PANEL === #
        self.left_frame = ttk.LabelFrame(self, text="Track Layout Interactive Diagram")
        self.left_frame.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)

        self.left_frame.grid_rowconfigure(0, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.setup_track_visualizer()

        ttk.Label(
            self.left_frame,
            text="Note: Not Drawn to Scale",
            font=("Segoe UI", 9, "italic"),
        ).pack(pady=(0, 5))
        legend_frame = ttk.Frame(self.left_frame)
        legend_frame.pack(pady=5)
        ttk.Label(
            legend_frame, text="Train Live Position:", font=("Segoe UI", 10, "bold")
        ).pack(side=tk.LEFT, padx=5)
        ttk.Label(
            legend_frame, text="★", foreground="gold", font=("Segoe UI", 12)
        ).pack(side=tk.LEFT, padx=3)

        # === RIGHT PANEL === #
        right_frame = ttk.Frame(self)
        right_frame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)
        right_frame.grid_columnconfigure(0, weight=1)

        # --- Upload / Line / Block --- #
        control_frame = ttk.LabelFrame(
            right_frame, text="Track Layout and Line Selection"
        )
        control_frame.grid(row=0, column=0, sticky="EW", padx=5, pady=5)
        ttk.Button(
            control_frame,
            text="Upload Track Layout File",
            width=25,
            command=self.upload_track_file,
        ).pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Label(
            control_frame, text="Select Line:", font=("Segoe UI", 10, "bold")
        ).pack(side=tk.LEFT, padx=5)

        # Initialize line selector empty; populate dynamically after upload
        self.line_selector = ttk.Combobox(
            control_frame, state="readonly", width=10, values=[]
        )
        self.line_selector.pack(side=tk.LEFT, padx=5)
        self.line_selector.bind("<<ComboboxSelected>>", self.on_line_selected)

        ttk.Label(
            control_frame, text="Select Block:", font=("Segoe UI", 10, "bold")
        ).pack(side=tk.LEFT, padx=5)
        self.block_selector = ttk.Combobox(control_frame, state="readonly", width=10)
        self.block_selector.pack(side=tk.LEFT, padx=5)
        self.block_selector.bind("<<ComboboxSelected>>", self.on_block_selected)

        # --- Currently Selected Block --- #
        block_frame = ttk.LabelFrame(right_frame, text="Currently Selected Block")
        block_frame.grid(row=1, column=0, sticky="EW", padx=5, pady=5)
        block_frame.grid_columnconfigure(0, weight=1)
        block_frame.grid_columnconfigure(1, weight=1)

        left_fields = [
            "Line:",
            "Direction of Travel:",
            "Traffic Light:",
            "Gate:",
            "Speed Limit (mph):",
            "Grade (%):",
        ]
        right_fields = [
            "Elevation (M):",
            "Block Length (ft):",
            "Station:",
            "Switch Position:",
            "Crossing:",
            "Branching:",
        ]

        self.block_labels = {
            f: tk.StringVar(value="N/A") for f in (left_fields + right_fields)
        }

        # Left column
        left_col = ttk.Frame(block_frame)
        left_col.grid(row=0, column=0, sticky="NW", padx=5, pady=5)
        for field in left_fields:
            frame = ttk.Frame(left_col)
            frame.pack(anchor="w", pady=2, expand=False)
            ttk.Label(frame, text=field, font=("Segoe UI", 10, "bold"), width=25).pack(
                side=tk.LEFT
            )
            ttk.Label(
                frame, textvariable=self.block_labels[field], font=("Segoe UI", 10)
            ).pack(side=tk.LEFT)

        # Right column
        right_col = ttk.Frame(block_frame)
        right_col.grid(row=0, column=1, sticky="NW", padx=5, pady=5)
        for field in right_fields:
            frame = ttk.Frame(right_col)
            frame.pack(anchor="w", pady=2, expand=False)
            ttk.Label(frame, text=field, font=("Segoe UI", 10, "bold"), width=25).pack(
                side=tk.LEFT
            )
            ttk.Label(
                frame, textvariable=self.block_labels[field], font=("Segoe UI", 10)
            ).pack(side=tk.LEFT)

        # --- Block Information (Dynamic Fields) --- #
        dynamic_frame = ttk.LabelFrame(right_frame, text="Block Information")
        dynamic_frame.grid(row=2, column=0, sticky="EW", padx=5, pady=5)
        dyn_fields = ["Occupancy:"]
        self.dynamic_labels = {f: tk.StringVar(value="N/A") for f in dyn_fields}
        for field in dyn_fields:
            frame = ttk.Frame(dynamic_frame)
            frame.pack(anchor="w", pady=2)
            ttk.Label(frame, text=field, font=("Segoe UI", 10, "bold"), width=28).pack(
                side=tk.LEFT
            )
            ttk.Label(
                frame, textvariable=self.dynamic_labels[field], font=("Segoe UI", 10)
            ).pack(side=tk.LEFT)

        # --- Environment Line --- #
        env_line = ttk.Frame(right_frame)
        env_line.grid(row=3, column=0, sticky="EW", padx=5, pady=(0, 5))
        ttk.Label(env_line, text="Track Heating:", font=("Segoe UI", 10, "bold")).pack(
            side=tk.LEFT, padx=(10, 2)
        )
        self.heating_status = ttk.Label(env_line, text="OFF", foreground="red")
        self.heating_status.pack(side=tk.LEFT, padx=(0, 40))
        ttk.Label(
            env_line,
            text="Environment Temperature (°F):",
            font=("Segoe UI", 10, "bold"),
        ).pack(side=tk.LEFT)
        self.temperature = tk.StringVar(value="N/A")
        ttk.Button(
            env_line, text="-", width=3, command=self.decrease_temp_immediate
        ).pack(side=tk.LEFT, padx=2)
        ttk.Label(
            env_line,
            textvariable=self.temperature,
            font=("Segoe UI", 10),
            width=5,
            anchor="center",
        ).pack(side=tk.LEFT)
        ttk.Button(
            env_line, text="+", width=3, command=self.increase_temp_immediate
        ).pack(side=tk.LEFT, padx=2)

        # --- Station Information --- #
        self.station_vars = {
            "Boarding:": tk.StringVar(value="N/A"),
            "Disembarking:": tk.StringVar(value="N/A"),
            "Ticket Sales:": tk.StringVar(value="N/A"),
        }
        station_frame = ttk.LabelFrame(right_frame, text="Station Information")
        station_frame.grid(row=4, column=0, sticky="EW", padx=5, pady=5)
        for label, var in self.station_vars.items():
            frame = ttk.Frame(station_frame)
            frame.pack(anchor="w", pady=2, padx=10)
            ttk.Label(frame, text=label, font=("Segoe UI", 10, "bold"), width=25).pack(
                side=tk.LEFT
            )
            ttk.Label(frame, textvariable=var, font=("Segoe UI", 10)).pack(side=tk.LEFT)

        # --- Failure Status --- #
        self.failure_vars = {
            "Power Failure": tk.BooleanVar(value=False),
            "Circuit Failure": tk.BooleanVar(value=False),
            "Broken Track": tk.BooleanVar(value=False),
        }
        failure_frame = ttk.LabelFrame(right_frame, text="Failure Status")
        failure_frame.grid(row=5, column=0, sticky="EW", padx=5, pady=5)
        for label, var in self.failure_vars.items():
            ttk.Checkbutton(
                failure_frame, text=label, variable=var, command=self.update_failures
            ).pack(anchor="w", padx=15, pady=2)
        self.warning_label = ttk.Label(
            failure_frame,
            text="All Systems Normal",
            font=("Segoe UI", 10, "italic"),
            foreground="green",
        )
        self.warning_label.pack(anchor="w", padx=15, pady=(5, 2))

        # Internal Data
        self.static_data = {}
        self.block_selected = False
        self.load_data()

        # === Added check for pre-existing static.json === #
        self.check_existing_static_data()
        self.poll_visualizer_clicks()

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
            filetypes=[("Excel Files", "*.xlsx *.xls")],
        )
        if not file_path:
            messagebox.showerror(
                "No File Selected",
                "Please select a valid track layout file before continuing.",
            )
            return

        try:
            xl = pd.ExcelFile(file_path)
            sheet_names = xl.sheet_names
            available_lines = [
                name.replace(" Line", "").strip()
                for name in sheet_names
                if name.endswith(" Line")
            ]

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
                "commanded": {},
            }

            with open("track_model_static.json", "w") as f:
                json.dump(data, f, indent=4)

            self.update_visualizer_display(excel_path=file_path)

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
        """Handle line selection and update the visualizer exactly once."""
        selected_line = self.line_selector.get()
        if not selected_line or not os.path.exists("track_model_static.json"):
            self.block_selector["values"] = []
            return

        self.load_static_after_upload(selected_line)

        if hasattr(self, "visualizer") and self.visualizer:
            try:
                full_line_name = f"{selected_line} Line"
                if getattr(self.visualizer, "current_line", None) != full_line_name:
                    self.visualizer.display_line(full_line_name)
            except Exception as e:
                print(f"[Visualizer] Failed to display {selected_line}: {e}")

    def load_static_after_upload(self, selected_line):
        if not os.path.exists("track_model_static.json"):
            return
        with open("track_model_static.json", "r") as f:
            data = json.load(f)
        records = data.get("static_data", {}).get(selected_line, [])
        self.static_data = records
        blocks = [
            f"{r['Section']}{int(float(r['Block Number']))}"
            for r in records
            if str(r["Block Number"]).replace(".", "", 1).isdigit()
        ]
        if self.block_manager and blocks:
            self.block_manager.initialize_blocks(selected_line, blocks)
        self.block_selector["values"] = blocks
        if blocks:
            self.block_selector.current(0)
            self.on_block_selected(None)

    def setup_track_visualizer(self):
        if hasattr(self, "track_label"):
            self.track_label.destroy()
        self.visualizer = RailwayDiagram(
            self.left_frame, block_manager=self.block_manager
        )
        self.excel_file_path = None

    def update_visualizer_display(
        self, excel_path=None, line_name=None, block_name=None
    ):
        if not hasattr(self, "visualizer"):
            print("Visualizer not initialized!")
            return
        if excel_path:
            self.excel_file_path = excel_path
        if not self.excel_file_path:
            print("No Excel file loaded yet")
            return
        if line_name is None:
            line_name = self.line_selector.get()
        if block_name is None:
            block_name = self.block_selector.get()
        if not self.visualizer.track_data:
            self.visualizer.load_excel_data(self.excel_file_path)
        full_line_name = f"{line_name} Line" if line_name else None
        self.visualizer.display_line(full_line_name, highlighted_block=block_name)

    def on_block_selected(self, event=None):
        self.block_selected = True
        block_id = self.block_selector.get()
        if not self.static_data:
            return
        for b in self.static_data:
            identifier = f"{b['Section']}{int(float(b['Block Number']))}"
            if identifier == block_id:
                kmh = b.get("Speed Limit (Km/Hr)", 0)
                mph = (
                    round(float(kmh) * 0.621371, 2)
                    if isinstance(kmh, (int, float))
                    else "N/A"
                )
                meters = b.get("Block Length (m)", 0)
                feet = (
                    round(float(meters) * 3.28084, 2)
                    if isinstance(meters, (int, float))
                    else "N/A"
                )
                self.block_labels["Line:"].set(b.get("Line", "N/A"))
                self.block_labels["Speed Limit (mph):"].set(mph)
                self.block_labels["Grade (%):"].set(b.get("Block Grade (%)", "N/A"))
                self.block_labels["Elevation (M):"].set(b.get("ELEVATION (M)", "N/A"))
                self.block_labels["Block Length (ft):"].set(feet)
                self.block_labels["Station:"].set(b.get("Station", "N/A"))
                self.block_labels["Switch Position:"].set("N/A")
                self.block_labels["Crossing:"].set(b.get("Crossing", "N/A"))
                self.block_labels["Branching:"].set(b.get("Branching", "N/A"))
                selected_block = identifier
                break

        if selected_block and hasattr(self, "visualizer"):
            try:
                self.visualizer.highlight_block(selected_block)
            except Exception as e:
                print(f"Failed to highlight block '{selected_block}': {e}")

    def get_crossing_for_block(self, block_id):
        """Helper method to get crossing status for a block from static data."""
        for b in self.static_data:
            identifier = f"{b['Section']}{int(float(b['Block Number']))}"
            if identifier == block_id:
                return b.get("Crossing", "No")
        return "No"

    def load_data(self):
        """Read Phase: Retrieve dynamic data from block_manager and update UI."""
        selected_line = self.line_selector.get()
        selected_block = self.block_selector.get()

        if self.block_manager and selected_block:
            block_data = self.block_manager.get_block_dynamic_data(
                selected_line, selected_block
            )

            if block_data:
                temp = block_data["temperature"]
                occupancy = block_data["occupancy"]
                traffic_light = block_data["traffic_light"]
                gate = block_data["gate"]
                failures = block_data["failures"]
                switch_position = block_data["switch_position"]

                station_name = self.get_station_name_for_block(selected_block)
                passengers_boarding = 0
                if station_name != "N/A":
                    # Sum passengers boarding from all trains at this station
                    for train_id in self.block_manager.passengers_boarding_data:
                        passengers_boarding += (
                            self.block_manager.get_passengers_boarding(
                                train_id, station_name
                            )
                        )

                # Ticket sales is cumulative across all trains
                ticket_sales = self.block_manager.total_ticket_sales

                # Check for failures and apply overrides
                if failures.get("power"):
                    # Power failure: lights off, gates closed, switches N/A
                    traffic_light = "OFF"
                    crossing = self.get_crossing_for_block(selected_block)
                    if crossing == "Yes":
                        gate = "Closed"
                    else:
                        gate = "N/A"
                    switch_position = "N/A"

                if failures.get("circuit"):
                    # Circuit failure: occupancy unavailable
                    self.dynamic_labels["Occupancy:"].set("N/A")
                else:
                    # Normal occupancy display
                    self.dynamic_labels["Occupancy:"].set(
                        "OCCUPIED" if occupancy else "CLEAR"
                    )

                # Update UI with processed values
                self.block_labels["Direction of Travel:"].set("--")
                self.block_labels["Traffic Light:"].set(traffic_light)
                self.block_labels["Gate:"].set(gate)
                self.block_labels["Switch Position:"].set(switch_position)

                self.station_vars["Boarding:"].set(passengers_boarding)
                self.station_vars["Ticket Sales:"].set(ticket_sales)

                self.temperature.set(str(temp))
                heating_on = temp < 32
                self.heating_status.config(
                    text="ON" if heating_on else "OFF",
                    foreground="green" if heating_on else "red",
                )

                for key in self.failure_vars:
                    state_key = key.split()[0].lower()
                    self.failure_vars[key].set(failures.get(state_key, False))

                failures_active = any(failures.values())
                if failures_active:
                    active = []
                    if failures.get("power"):
                        active.append("Power Failure")
                    if failures.get("circuit"):
                        active.append("Circuit Failure")
                    if failures.get("broken"):
                        active.append("Broken Track")
                    failure_text = ", ".join(active)
                    self.warning_label.config(
                        text=f"Warning: Active Failure - {failure_text}",
                        foreground="orange",
                    )
                else:
                    self.warning_label.config(
                        text="All Systems Normal", foreground="green"
                    )

        self.check_and_start_trains()
        self.after(500, self.load_data)

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
        selected_line = self.line_selector.get()
        selected_block = self.block_selector.get()
        if selected_line and selected_block and self.block_manager:
            temp = int(self.temperature.get())
            self.block_manager.update_temperature(selected_line, selected_block, temp)

    def update_failures(self):
        selected_line = self.line_selector.get()
        selected_block = self.block_selector.get()
        if selected_line and selected_block and self.block_manager:
            self.block_manager.update_failures(
                selected_line,
                selected_block,
                power=self.failure_vars["Power Failure"].get(),
                circuit=self.failure_vars["Circuit Failure"].get(),
                broken=self.failure_vars["Broken Track"].get(),
            )

    def poll_visualizer_clicks(self):
        """Check for new block clicks every 500 ms."""
        if not hasattr(self, "visualizer"):
            self.after(500, self.poll_visualizer_clicks)
            return

        clicked = getattr(self.visualizer, "last_clicked_block", None)
        if clicked:
            self.visualizer.last_clicked_block = None  # reset

            if clicked in self.block_selector["values"]:
                self.block_selector.set(clicked)
                self.on_block_selected()
            else:
                print(f"[POLL] '{clicked}' not found in current block list.")

        self.after(500, self.poll_visualizer_clicks)

    def get_station_name_for_block(self, block_id):
        """Get station name for a block from static JSON."""
        import json

        selected_line = self.line_selector.get()

        try:
            with open("track_model_static.json", "r") as f:
                static_data = json.load(f)

            line_key = selected_line.replace(" Line", "")

            # FIX: Access through "static_data" wrapper
            blocks = static_data.get("static_data", {}).get(line_key, [])

            for block in blocks:
                block_num = block.get("Block Number")
                section = block.get("Section", "")

                # Construct the identifier the same way it's done in upload_track_file
                if block_num not in ["N/A", "nan", None] and section not in [
                    "N/A",
                    "nan",
                    None,
                ]:
                    try:
                        constructed_id = f"{section}{int(float(block_num))}"
                        if constructed_id == block_id:
                            return block.get("Station", "N/A")
                    except (ValueError, TypeError):
                        continue

            return "N/A"

        except FileNotFoundError:
            print("Error: track_model_static.json not found")
            return "N/A"
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in static file: {e}")
            return "N/A"
        except Exception as e:
            print(f"Error getting station name: {e}")
            return "N/A"

    def check_and_start_trains(self):
        for train in self.block_manager.trains:
            train_id = train["train_id"]
            line = train["line"]
            if train["start"] and train_id not in self.visualizer.trains:
                self.visualizer.animate_train(train_id, line)


if __name__ == "__main__":
    app = TrackModelUI()
    app.mainloop()

    if os.path.exists("track_model_static.json"):
        with open("track_model_static.json", "w") as f:
            json.dump({}, f, indent=4)
