
class CTCUI:
    def __init__(self, server_url=None):
        import tkinter as tk, json, os, threading, subprocess, sys
        from datetime import datetime
        from tkinter import filedialog, ttk
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        self.tk = tk
        self.ttk = ttk
        self.filedialog = filedialog
        self.datetime = datetime
        self.json = json
        self.os = os
        self.threading = threading
        self.subprocess = subprocess
        self.sys = sys
        self.Observer = Observer
        self.FileSystemEventHandler = FileSystemEventHandler

        # Initialize API client (remote mode) or use files (local mode)
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from ctc.api.ctc_api_client import CTCAPIClient
        self.api_client = CTCAPIClient(server_url=server_url)
        self.server_url = server_url
        self.is_remote = (server_url is not None)

        # Use absolute path to project root ctc_data.json so it's consistent across components
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.data_file = os.path.join(project_root, 'ctc_data.json')
        
        # Check server connection if in remote mode
        if self.is_remote:
            if self.api_client.health_check():
                print(f"[CTC UI] Connected to server: {server_url}")
            else:
                print(f"[CTC UI] WARNING: Cannot connect to server: {server_url}")
                print(f"[CTC UI] Falling back to local file mode")
                self.is_remote = False
        self.default_data = {
            "Dispatcher": {
                "Trains":{
                    "Train 1": {"Line": "", "Suggested Speed": "", "Authority": "", "Station Destination": "", "Arrival Time": "", "Position": "", "State": "", "Current Station": ""},
                    "Train 2": {"Line": "", "Suggested Speed": "", "Authority": "", "Station Destination": "", "Arrival Time": "", "Position": "", "State": "", "Current Station": ""},
                    "Train 3": {"Line": "", "Suggested Speed": "", "Authority": "", "Station Destination": "", "Arrival Time": "", "Position": "", "State": "", "Current Station": ""},
                    "Train 4": {"Line": "", "Suggested Speed": "", "Authority": "", "Station Destination": "", "Arrival Time": "", "Position": "", "State": "", "Current Station": ""},
                    "Train 5": {"Line": "", "Suggested Speed": "", "Authority": "", "Station Destination": "", "Arrival Time": "", "Position": "", "State": "", "Current Station": ""}
                }
            }
        }

        self.setup_json_file()
        self.root = tk.Tk()
        mode_text = " (Remote Mode)" if self.is_remote else " (Local Mode)"
        self.root.title("CTC User Interface" + mode_text)
        self.root.geometry("1500x700")
        self.root.grid_rowconfigure(3, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.button_style = {
            "width": 60,
            "height": 1,
            "bg": "white",
            "relief": "flat",
            "bd": 0,
            "font": ("Times New Roman", 15, 'bold'),
            "activebackground": "#ddd"
        }
        self.active_button = None

        self.setup_ui()

        # File watcher for local mode; polling for remote mode
        if not self.is_remote:
            class FileChangeHandler(self.FileSystemEventHandler):
                def on_modified(handler_self, event):
                    if event.src_path.endswith("ctc_data.json"):
                        self.root.after(100, self.update_active_trains_table)
            self.event_handler = FileChangeHandler()
            self.observer = self.Observer()
            self.observer.schedule(self.event_handler, path=self.os.path.dirname(self.data_file) or ".", recursive=False)
            self.observer_thread = self.threading.Thread(target=self.observer.start)
            self.observer_thread.daemon = True
            self.observer_thread.start()
        else:
            # In remote mode, use polling instead of file watcher
            self.observer = None
            self.poll_updates()

        self.show_frame(self.auto_frame)
        self.auto_button.config(bg="lightgray")
        self.active_button = self.auto_button

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_active_trains_table()

    def setup_json_file(self):
        # Always reset `ctc_data.json` to default on UI start so active trains/table is fresh
        try:
            with open(self.data_file, "w") as f:
                self.json.dump(self.default_data, f, indent=4)
        except Exception as e:
            print(f"Warning: failed to write default ctc_data.json: {e}")
        # Also reset the project-root track controller file so Active flags start cleared
        try:
            track_file = self.os.path.join(self.os.path.dirname(self.data_file), 'ctc_track_controller.json')
            default_track = {"Trains": {}}
            for i in range(1, 6):
                tname = f"Train {i}"
                default_track["Trains"][tname] = {
                    "Active": 0,
                    "Suggested Speed": 0,
                    "Suggested Authority": 0,
                    "Train Position": 0,
                    "Train State": 0
                }
            with open(track_file, 'w') as tf:
                self.json.dump(default_track, tf, indent=4)
        except Exception as e:
            print(f"Warning: failed to write default ctc_track_controller.json: {e}")

    def load_data(self):
        """Load CTC data via API or local file."""
        if self.is_remote:
            return self.api_client.get_state()
        else:
            if self.os.path.exists(self.data_file):
                with open(self.data_file, "r") as f:
                    try:
                        return self.json.load(f)
                    except self.json.JSONDecodeError:
                        return {}
            return {}

    def save_data(self, data):
        """Save CTC data via API or local file."""
        if self.is_remote:
            self.api_client.update_state(data)
        else:
            with open(self.data_file, "w") as f:
                self.json.dump(data, f, indent=4)
    
    def poll_updates(self):
        """Poll server for updates in remote mode."""
        if self.is_remote:
            self.update_active_trains_table()
            # Schedule next poll in 500ms
            self.root.after(500, self.poll_updates)


    def setup_ui(self):
        tk = self.tk
        ttk = self.ttk
        # Top Row: Date/Time
        self.datetime_frame = tk.Frame(self.root)
        self.datetime_frame.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.date_label = tk.Label(self.datetime_frame, font=('Times New Roman', 15, 'bold'))
        self.date_label.pack(side='left')
        self.time_label = tk.Label(self.datetime_frame, font=('Times New Roman', 15, 'bold'))
        self.time_label.pack(side='left')
        self.update_datetime()

        # Button Row
        self.button_frame = tk.Frame(self.root)
        self.button_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=5)
        self.button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Middle Area: Main Frame Container
        self.main_area = tk.Frame(self.root)
        self.main_area.grid(row=2, column=0, sticky='nsew', padx=10)
        self.main_area.grid_rowconfigure(0, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        # Mode Frames (Manual, Auto, Maint)
        self.manual_frame = tk.Frame(self.main_area, bg="lightgreen")
        self.auto_frame = tk.Frame(self.main_area, bg="lightblue")
        self.maint_frame = tk.Frame(self.main_area, bg="lightyellow")
        for frame in (self.manual_frame, self.auto_frame, self.maint_frame):
            frame.grid(row=0, column=0, sticky="nsew")

        # Buttons to switch frames
        self.auto_button = tk.Button(
            self.button_frame,
            text='Automatic',
            command=lambda: self.show_frame(self.auto_frame, self.auto_button),
            **self.button_style
        )
        self.auto_button.grid(row=0, column=0, sticky='ew', padx=5)

        self.manual_button = tk.Button(
            self.button_frame,
            text='Manual',
            command=lambda: self.show_frame(self.manual_frame, self.manual_button),
            **self.button_style
        )
        self.manual_button.grid(row=0, column=1, sticky='ew', padx=5)

        self.maint_button = tk.Button(
            self.button_frame,
            text='Maintenance',
            command=lambda: self.show_frame(self.maint_frame, self.maint_button),
            **self.button_style
        )
        self.maint_button.grid(row=0, column=2, sticky='ew', padx=5)

        # Manual Frame UI
        label_font = ('Times New Roman', 12, 'bold')
        input_font = ('Times New Roman', 12, 'bold')
        self.manual_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        tk.Label(self.manual_frame, text="Select a Train to Dispatch", font=label_font, bg="lightgreen").grid(row=0, column=0, sticky='w', padx=10, pady=5)
        tk.Label(self.manual_frame, text="Select a Line", font=label_font, bg="lightgreen").grid(row=0, column=1, sticky='w', padx=10, pady=5)
        tk.Label(self.manual_frame, text="Select a Destination Station", font=label_font, bg="lightgreen").grid(row=0, column=2, sticky='w', padx=10, pady=5)
        tk.Label(self.manual_frame, text="Enter Arrival Time", font=label_font, bg="lightgreen").grid(row=0, column=3, sticky='w', padx=10, pady=5)

        self.manual_train_box = ttk.Combobox(self.manual_frame, values=["Train 1", "Train 2", "Train 3", "Train 4", "Train 5"], font=input_font)
        self.manual_line_box = ttk.Combobox(self.manual_frame, values=["Green"], font=input_font)
        self.manual_dest_box = ttk.Combobox(self.manual_frame, values=["Pioneer", "Edgebrook", "Whited", "South Bank", "Central", "Inglewood", "Overbrook", "Glenbury", "Dormont", "Mt. Lebanon", "Poplar", "Castle Shannon"], font=input_font)
        self.manual_time_box = tk.Entry(self.manual_frame, font=input_font)

        self.manual_train_box.grid(row=1, column=0, padx=5, sticky='ew')
        self.manual_line_box.grid(row=1, column=1, padx=5, sticky='ew')
        self.manual_dest_box.grid(row=1, column=2, padx=5, sticky='ew')
        self.manual_time_box.grid(row=1, column=3, padx=5, sticky='ew')

        self.manual_dispatch_button = tk.Button(self.manual_frame, text='DISPATCH', command=self.manual_dispatch, **self.button_style)
        self.manual_dispatch_button.grid(row=2, column=0, columnspan=4, pady=10, padx=500, sticky='ew')

        # Maintenance Frame UI
        self.maint_frame.grid_columnconfigure((0,1,2,3),weight=1)
        switch_frame = tk.LabelFrame(self.maint_frame,text="Set Switch Positions",bg='lightyellow',font=label_font)
        switch_frame.grid_columnconfigure((0,1),weight=1)
        switch_frame.grid(row=0,column=0,padx=20,pady=10,sticky='nsew')
        tk.Label(switch_frame,text="Select a Line",font=label_font,bg="lightyellow").grid(row=0,column=0,sticky='w',padx=5,pady=5)
        tk.Label(switch_frame,text="Select Switch",font=label_font,bg="lightyellow").grid(row=1,column=0,sticky='w',padx=5,pady=5)
        self.maint_line_box1 = ttk.Combobox(switch_frame, values=["Red", "Green"], font=input_font)
        self.maint_switch_box = ttk.Combobox(switch_frame, values=["1", "2", "3", "4"], font=input_font)
        self.maint_line_box1.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.maint_switch_box.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        move_switch_button = tk.Button(switch_frame, text='Move Switch', command=self.move_switch,**self.button_style)
        move_switch_button.grid(row=2, column=0, columnspan=2, padx=100,pady=10, sticky='ew')

        block_frame = tk.LabelFrame(self.maint_frame, text="Close Block", bg="lightyellow", font=label_font)
        block_frame.grid_columnconfigure((0,1),weight=1)
        block_frame.grid(row=0, column=1, padx=20, pady=10, sticky='nsew')
        tk.Label(block_frame, text="Select a Line", font=label_font, bg="lightyellow").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        tk.Label(block_frame, text="Select Block", font=label_font, bg="lightyellow").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.maint_line_box2 = ttk.Combobox(block_frame, values=["Red", "Green"], font=input_font)
        self.maint_block_box = ttk.Combobox(block_frame, values=["1", "2", "3", "4"], font=input_font)
        self.maint_line_box2.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.maint_block_box.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        close_block_button = tk.Button(block_frame, text='Close Block', command=self.close_block,**self.button_style)
        close_block_button.grid(row=2, column=0, columnspan=2, padx=100,pady=10, sticky='ew')

        # Auto Frame UI
        self.auto_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.uploaded_file_label = tk.Label(self.auto_frame, text="", bg="lightblue", font=('Times New Roman', 12, 'italic'))
        upload_button = tk.Button(self.auto_frame, text="Upload Schedule", command=self.upload_schedule, width=40, height=1, bg="white", relief="flat", bd=0, font=("Times New Roman", 15, "bold"))
        upload_button.grid(row=0, column=0, columnspan=4, pady=10)
        self.uploaded_file_label.grid(row=1, column=0, columnspan=4, pady=(0, 10))
        run_button = tk.Button(self.auto_frame, text="Run", width=20, height=1, bg="white", relief="flat", bd=0, font=("Times New Roman", 15, "bold"))
        run_button.grid(row=2, column=0, columnspan=4, pady=10)

        # Tables Below Mode Area
        self.bottom_frame = tk.Frame(self.root)
        self.bottom_frame.grid(row=3, column=0, sticky='nsew', padx=10, pady=10)
        self.root.grid_rowconfigure(3, weight=1)
        self.bottom_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.active_trains_frame, self.active_trains_table = self.create_table_section(
            self.bottom_frame,
            "Active Trains",
            ("Train", "Line", "Block", "State", "Speed (mph)", "Authority (yards)", "Current Station", "Destination", "Arrival Time"),
            []
        )
        self.active_trains_frame.grid(row=0, column=0, columnspan=3, sticky='nsew', padx=10)
        self.lights_frame, self.lights_table = self.create_table_section(
            self.bottom_frame,
            "Lights",
            ("Line", "Block", "Status"),
            [("Red", "A1", "Green"), ("Red", "A2", "Red")]
        )
        self.lights_frame.grid(row=0, column=3, columnspan=1, sticky='nsew', padx=5)
        self.gates_frame, self.gates_table = self.create_table_section(
            self.bottom_frame,
            "Gates",
            ("Line", "Block", "Status"),
            [("Red", "A1", "Closed"), ("Red", "A2", "Closed")]
        )
        self.gates_frame.grid(row=0, column=4, columnspan=1, sticky='nsew', padx=5)
        self.throughput_frame = tk.Frame(self.bottom_frame)
        self.throughput_frame.grid(row=1, column=0, columnspan=3, sticky='ew', pady=(10, 0))
        self.throughput_frame.grid_columnconfigure((0, 1), weight=1)
        tk.Label(self.throughput_frame, text=f"Red Line: 20 passengers/hour", font=('Times New Roman', 20, 'bold')).grid(row=0, column=0, sticky='w', padx=20)
        tk.Label(self.throughput_frame, text="Green Line: 14 passengers/hour", font=('Times New Roman', 20, 'bold')).grid(row=0, column=1, sticky='w', padx=20)

    def manual_dispatch(self):
        train = self.manual_train_box.get()
        line = self.manual_line_box.get()
        dest = self.manual_dest_box.get()
        arrival = self.manual_time_box.get()
        with open('ctc\\ctc_ui_inputs.json', "r") as f1:
            data1 = self.json.load(f1)
        data1["Train"] = train
        data1["Line"] = line
        data1["Station"] = dest
        data1["Arrival Time"] = arrival
        with open('ctc\\ctc_ui_inputs.json', "w") as f1:
            self.json.dump(data1, f1, indent=4)
        self.update_active_trains_table()
        
        # Open Train Manager window
        try:
            from train_controller.train_manager import TrainManagerUI
            if not hasattr(self, 'train_manager_window') or not self.train_manager_window.winfo_exists():
                self.train_manager_window = TrainManagerUI()
        except Exception as e:
            print(f"Failed to open Train Manager: {e}")
        
        # Instead of launching a subprocess, call the in-process dispatch function
        try:
            import ctc.ctc_main_temp as ctc_main_temp
        except Exception as e:
            print(f"Failed to import ctc_main_temp.dispatch_train: {e}")
        else:
            # Run dispatch in a background thread so the UI stays responsive
            if not hasattr(self, 'dispatch_threads'):
                self.dispatch_threads = []
            t = self.threading.Thread(target=ctc_main_temp.dispatch_train,
                                      args=(train, line, dest, arrival),
                                      kwargs={'server_url': self.server_url},  # Pass server URL for remote mode
                                      daemon=True)
            t.start()
            self.dispatch_threads.append(t)
        # ...existing code for train dispatch dialog...

    def move_switch(self):
        switch_line = self.maint_line_box1.get()
        switch = self.maint_switch_box.get()
        data = self.load_data()
        maintenance_outputs = data.get("MaintenenceModeOutputs", {})
        maintenance_outputs["Switch Line"] = switch_line
        maintenance_outputs["Switch Position"] = switch
        data["MaintenenceModeOutputs"] = maintenance_outputs
        self.save_data(data)

    def close_block(self):
        block_line = self.maint_line_box2.get()
        closed_block = self.maint_block_box.get()
        data = self.load_data()
        maintenance_outputs = data.get("MaintenenceModeOutputs", {})
        maintenance_outputs["Block Line"] = block_line
        maintenance_outputs["Closed Block"] = closed_block
        data["MaintenenceModeOutputs"] = maintenance_outputs
        self.save_data(data)

    def upload_schedule(self):
        file_path = self.filedialog.askopenfilename(
            title="Select Schedule File",
            filetypes=[
                ("CSV Files", "*.csv"),
                ("Excel Files", "*.xlsx"),
                ("Text Files", "*.txt"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.uploaded_file_label.config(
                text=f"Loaded: {file_path.split('/')[-1]}",
                fg="darkgreen"
            )
            print(f"Selected schedule file: {file_path}")

    def create_table_section(self, parent, title, columns, data):
        tk = self.tk
        ttk = self.ttk
        section = tk.Frame(parent)
        section.grid_rowconfigure(1, weight=1)
        section.grid_columnconfigure(0, weight=1)
        tk.Label(section, text=title, font=('Times New Roman', 20, 'bold')).grid(row=0, column=0, sticky='w')
        style = ttk.Style()
        style.configure("Custom.Treeview.Heading", font=('Times New Roman', 10, 'bold'))
        table = ttk.Treeview(section, columns=columns, show='headings', style="Custom.Treeview")
        for col in columns:
            table.heading(col, text=col)
            table.column(col, anchor='center', width=80)
        table.grid(row=1, column=0, sticky='nsew')
        for row in data:
            table.insert('', 'end', values=row)
        return section, table

    def update_active_trains_table(self):
        if not self.os.path.exists(self.data_file):
            return
        try:
            with open(self.data_file, "r") as f:
                data = self.json.load(f)
        except self.json.JSONDecodeError:
            return
        dispatcher_data = data.get("Dispatcher", {})
        for row in self.active_trains_table.get_children():
            self.active_trains_table.delete(row)
        trains = dispatcher_data.get("Trains", {})

        # Load track controller file to check 'Active' flags (only show active trains)
        track_file = self.os.path.join(self.os.path.dirname(self.data_file), 'ctc_track_controller.json')
        track_updates = {}
        if self.os.path.exists(track_file):
            try:
                with open(track_file, 'r') as tf:
                    track_updates = self.json.load(tf)
            except Exception:
                track_updates = {}

        track_trains = track_updates.get('Trains', {}) if isinstance(track_updates, dict) else {}

        for train_name, info in trains.items():
            active_flag = track_trains.get(train_name, {}).get('Active', 0)
            if not active_flag:
                # skip trains that are not active
                continue
            self.active_trains_table.insert("", "end", values=(
                train_name,
                info.get("Line", ""),
                info.get("Position"),
                info.get("State", ""),
                info.get("Suggested Speed", ""),
                info.get("Authority", ""),
                info.get("Current Station", ""),
                info.get("Station Destination", ""),
                info.get("Arrival Time", ""),
            ))
        self.root.after(1000, self.update_active_trains_table)

    def update_datetime(self):
        now = self.datetime.now()
        self.date_label.config(text=now.date())
        self.time_label.config(text=f"      {now.strftime('%H:%M:%S')}")
        self.root.after(1000, self.update_datetime)

    def show_frame(self, frame, clicked_button=None):
        frame.tkraise()
        for btn in [self.auto_button, self.manual_button, self.maint_button]:
            btn.config(bg="white", fg="black")
        if clicked_button:
            clicked_button.config(bg="lightgray", fg="black")
            self.active_button = clicked_button

    def run(self):
        self.root.mainloop()
    
    def on_close(self):
        if self.observer:
            self.observer.stop()
            self.observer_thread.join()
        # Terminate any subprocesses started
        if hasattr(self, 'subprocesses'):
            for proc in self.subprocesses:
                if proc.poll() is None:
                    proc.terminate()
        self.root.destroy()

# To use the class:
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="CTC User Interface")
    parser.add_argument('--server', type=str, help='REST API server URL (e.g., http://192.168.1.100:5000)')
    args = parser.parse_args()
    
    print("[CTC UI] Starting CTC User Interface")
    print(f"[CTC UI] Mode: {'Remote' if args.server else 'Local'}")
    if args.server:
        print(f"[CTC UI] Server: {args.server}")
    
    ui = CTCUI(server_url=args.server)
    ui.run()
