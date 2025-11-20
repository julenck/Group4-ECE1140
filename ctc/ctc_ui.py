import tkinter as tk, json, os, threading, subprocess, sys
from datetime import datetime
from tkinter import filedialog, ttk, messagebox
from watchdog.observers import Observer 
from watchdog.events import FileSystemEventHandler

# Add parent directory to path for time_controller
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from time_controller import get_time_controller 

# Add train_controller to path for train dispatch integration
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'train_controller'))


class CTCUI:
    def __init__(self):
        # Set up json file with absolute path
        ctc_dir = os.path.dirname(__file__)
        self.data_file = os.path.join(ctc_dir, 'ctc_data.json')
        
        self.default_data = {
            "Dispatcher": {
                "Trains":{
                    "Train 1": {
                        "Line": "",
                        "Suggested Speed": "",
                        "Authority": "",
                        "Station Destination": "",
                        "Arrival Time": "",
                        "Position": "",
                        "State": "",
                        "Current Station": ""
                    },
                    "Train 2": {
                        "Line": "",
                        "Suggested Speed": "",
                        "Authority": "",
                        "Station Destination": "",
                        "Arrival Time": "",
                        "Position": "",
                        "State": "",
                        "Current Station": ""
                    },
                    "Train 3": {
                        "Line": "",
                        "Suggested Speed": "",
                        "Authority": "",
                        "Station Destination": "",
                       "Arrival Time": "",
                       "Position": "",
                       "State": "",
                       "Current Station": ""

                    },
                    "Train 4": {
                        "Line": "",
                        "Suggested Speed": "",
                        "Authority": "",
                        "Station Destination": "",
                        "Arrival Time": "",
                        "Position": "",
                        "State": "",
                        "Current Station": ""
                    },
                    "Train 5": {
                        "Line": "",
                        "Suggested Speed": "",
                        "Authority": "",
                        "Station Destination": "",
                        "Arrival Time": "",
                        "Position": "",
                        "State": "",
                        "Current Station": ""
                    }
                }
            }
        }

        # Check if json file structure is ok - Always reset to blank on startup
        with open(self.data_file, "w") as f:
            json.dump(self.default_data, f, indent=4)

        self.active_button = None
        self.observer = None
        
        # Get time controller for synchronized timing (before setup_ui)
        self.time_controller = get_time_controller()
        
        self.setup_ui()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    def save_data(self, data):
        with open(self.data_file, "w") as f:
            json.dump(data, f, indent=4)

    def setup_ui(self):
        # Root window
        self.root = tk.Tk()
        self.root.title("CTC User Interface")
        self.root.geometry("1500x700")
        self.root.grid_rowconfigure(3, weight=1)  
        self.root.grid_columnconfigure(0, weight=1)

        self.setup_datetime_frame()
        self.setup_button_frame()
        self.setup_main_area()
        self.setup_bottom_frame()
        self.setup_file_watcher()

        # Show default frame 
        self.show_frame(self.auto_frame)
        self.auto_button.config(bg="lightgray")
        self.active_button = self.auto_button

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.update_active_trains_table()

    def setup_datetime_frame(self):
        # Top Row: Date/Time
        datetime_frame = tk.Frame(self.root)
        datetime_frame.grid(row=0, column=0, sticky="w", padx=10, pady=5)

        self.date_label = tk.Label(datetime_frame, font=('Times New Roman', 15, 'bold'))
        self.date_label.pack(side='left')
        self.time_label = tk.Label(datetime_frame, font=('Times New Roman', 15, 'bold'))
        self.time_label.pack(side='left')

        self.update_datetime()

    def update_datetime(self): 
        now = datetime.now()
        self.date_label.config(text=now.date())
        self.time_label.config(text=f"      {now.strftime("%H:%M:%S")}")
        self.root.after(1000, self.update_datetime)

    def setup_button_frame(self):
        # Button Row
        button_frame = tk.Frame(self.root)
        button_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=5)
        button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        button_style = {
            "width": 60,
            "height": 1,
            "bg": "white",
            "relief": "flat",
            "bd": 0,
            "font": ("Times New Roman", 15, 'bold'),
            "activebackground": "#ddd"
        }

        # Buttons to switch frames 
        self.auto_button = tk.Button(
            button_frame, 
            text='Automatic', 
            command=lambda: self.show_frame(self.auto_frame, self.auto_button), 
            **button_style
        )
        self.auto_button.grid(row=0, column=0, sticky='ew', padx=5)

        self.manual_button = tk.Button(
            button_frame, 
            text='Manual', 
            command=lambda: self.show_frame(self.manual_frame, self.manual_button), 
            **button_style
        )
        self.manual_button.grid(row=0, column=1, sticky='ew', padx=5)

        self.maint_button = tk.Button(
            button_frame, 
            text='Maintenance', 
            command=lambda: self.show_frame(self.maint_frame, self.maint_button), 
            **button_style
        )
        self.maint_button.grid(row=0, column=2, sticky='ew', padx=5)

    def setup_main_area(self):
        # Middle Area: Main Frame Container
        main_area = tk.Frame(self.root)
        main_area.grid(row=2, column=0, sticky='nsew', padx=10)
        main_area.grid_rowconfigure(0, weight=1)
        main_area.grid_columnconfigure(0, weight=1)

        # Mode Frames (Manual, Auto, Maint) 
        self.manual_frame = tk.Frame(main_area, bg="lightgreen")
        self.auto_frame = tk.Frame(main_area, bg="lightblue")
        self.maint_frame = tk.Frame(main_area, bg="lightyellow")

        for frame in (self.manual_frame, self.auto_frame, self.maint_frame):
            frame.grid(row=0, column=0, sticky="nsew")

        self.setup_manual_frame()
        self.setup_auto_frame()
        self.setup_maint_frame()

    def show_frame(self, frame, clicked_button=None):
        frame.tkraise()

        # Reset all button colors to white
        for btn in [self.auto_button, self.manual_button, self.maint_button]:
            btn.config(bg="white", fg="black")

        # Highlight the active one (if provided)
        if clicked_button:
            clicked_button.config(bg="lightgray", fg="black")
            self.active_button = clicked_button

    def setup_manual_frame(self):
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
        self.manual_dest_box = ttk.Combobox(self.manual_frame, values=["Pioneer",
                                                             "Edgebrook",
                                                             "Whited",
                                                             "South Bank",
                                                             "Central",
                                                             "Inglewood",
                                                             "Overbrook",
                                                             "Glenbury",
                                                             "Dormont",
                                                             "Mt. Lebanon",
                                                             "Poplar",
                                                             "Castle Shannon"],font=input_font)
        self.manual_time_box = tk.Entry(self.manual_frame, font=input_font)

        self.manual_train_box.grid(row=1, column=0, padx=5, sticky='ew')
        self.manual_line_box.grid(row=1, column=1, padx=5, sticky='ew')
        self.manual_dest_box.grid(row=1, column=2, padx=5, sticky='ew')
        self.manual_time_box.grid(row=1, column=3, padx=5, sticky='ew')

        button_style = {
            "width": 60,
            "height": 1,
            "bg": "white",
            "relief": "flat",
            "bd": 0,
            "font": ("Times New Roman", 15, 'bold'),
            "activebackground": "#ddd"
        }

        manual_dispatch_button = tk.Button(self.manual_frame, text='DISPATCH', command=self.manual_dispatch, **button_style)
        manual_dispatch_button.grid(row=2,column=0,columnspan=4,pady=10,padx=500,sticky='ew')

    def manual_dispatch(self):
        train = self.manual_train_box.get()
        line = self.manual_line_box.get()
        dest = self.manual_dest_box.get()
        arrival = self.manual_time_box.get()

        # Validate inputs
        if not all([train, line, dest, arrival]):
            tk.messagebox.showerror("Missing Information", 
                "Please fill in all fields:\n- Train\n- Line\n- Destination\n- Arrival Time")
            return

        print(f"[CTC Dispatch] Train: {train}, Line: {line}, Dest: {dest}, Arrival: {arrival}")

        ############# write to ctc_ui_inputs.json ##############
        ctc_dir = os.path.dirname(__file__)
        ui_inputs_file = os.path.join(ctc_dir, 'ctc_ui_inputs.json')
        
        with open(ui_inputs_file, "r") as f1: 
            data1 = json.load(f1)
        
        data1["Train"] = train
        data1["Line"] = line
        data1["Station"] = dest
        data1["Arrival Time"] = arrival

        with open(ui_inputs_file, "w") as f1: 
            json.dump(data1,f1,indent=4)

        self.update_active_trains_table()

        # Run ctc_main.py to update ctc_data.json
        python_exe = sys.executable 
        script_path = os.path.join(os.path.dirname(__file__), "ctc_main.py")
        print(f"[CTC] Launching ctc_main.py: {script_path}")
        subprocess.Popen([python_exe, script_path])

        # Open train dispatch dialog to select controller type
        try:
            from train_manager import dispatch_train_from_ctc
            
            # Show dispatch dialog and get selected train
            train_id, controller_type = dispatch_train_from_ctc()
            
            if train_id is not None:
                print(f"[CTC] Train {train_id} dispatched successfully with {controller_type} controller")
            else:
                print("[CTC] Train dispatch cancelled")
        except Exception as e:
            print(f"[CTC] Error dispatching train: {e}")
            import traceback
            traceback.print_exc()

    def setup_maint_frame(self):
        # Maintenance Frame UI 
        label_font = ('Times New Roman', 12, 'bold')
        input_font = ('Times New Roman', 12, 'bold')
        button_style = {
            "width": 60,
            "height": 1,
            "bg": "white",
            "relief": "flat",
            "bd": 0,
            "font": ("Times New Roman", 15, 'bold'),
            "activebackground": "#ddd"
        }

        self.maint_frame.grid_columnconfigure((0,1,2,3),weight=1)

        # Set switch positions section 
        switch_frame = tk.LabelFrame(self.maint_frame,text="Set Switch Positions",bg='lightyellow',font=label_font)
        switch_frame.grid_columnconfigure((0,1),weight=1)
        switch_frame.grid(row=0,column=0,padx=20,pady=10,sticky='nsew')

        tk.Label(switch_frame,text="Select a Line",font=label_font,bg="lightyellow").grid(row=0,column=0,sticky='w',padx=5,pady=5)
        tk.Label(switch_frame,text="Select Switch",font=label_font,bg="lightyellow").grid(row=1,column=0,sticky='w',padx=5,pady=5)

        self.maint_line_box1 = ttk.Combobox(switch_frame, values=["Red", "Green"], font=input_font)
        self.maint_switch_box = ttk.Combobox(switch_frame, values=["1", "2", "3", "4"], font=input_font)

        self.maint_line_box1.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.maint_switch_box.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

        move_switch_button = tk.Button(switch_frame, text='Move Switch', command=self.move_switch,**button_style)
        move_switch_button.grid(row=2, column=0, columnspan=2, padx=100,pady=10, sticky='ew')

        # Close block section 
        block_frame = tk.LabelFrame(self.maint_frame, text="Close Block", bg="lightyellow", font=label_font)
        block_frame.grid_columnconfigure((0,1),weight=1)
        block_frame.grid(row=0, column=1, padx=20, pady=10, sticky='nsew')

        tk.Label(block_frame, text="Select a Line", font=label_font, bg="lightyellow").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        tk.Label(block_frame, text="Select Block", font=label_font, bg="lightyellow").grid(row=1, column=0, sticky='w', padx=5, pady=5)

        self.maint_line_box2 = ttk.Combobox(block_frame, values=["Red", "Green"], font=input_font)
        self.maint_block_box = ttk.Combobox(block_frame, values=["1", "2", "3", "4"], font=input_font)

        self.maint_line_box2.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.maint_block_box.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

        close_block_button = tk.Button(block_frame, text='Close Block', command=self.close_block,**button_style)
        close_block_button.grid(row=2, column=0, columnspan=2, padx=100,pady=10, sticky='ew')

    def move_switch(self):
        switch_line = self.maint_line_box1.get()
        switch = self.maint_switch_box.get()

        data = self.load_data()

        # Get existing section or create if missing
        maintenance_outputs = data.get("MaintenenceModeOutputs", {})

        # Update only switch data
        maintenance_outputs["Switch Line"] = switch_line
        maintenance_outputs["Switch Position"] = switch

        data["MaintenenceModeOutputs"] = maintenance_outputs
        self.save_data(data)

    def close_block(self): 
        block_line = self.maint_line_box2.get()
        closed_block = self.maint_block_box.get()

        data = self.load_data()

        # Get existing section or create if missing
        maintenance_outputs = data.get("MaintenenceModeOutputs", {})

        # Update only block data
        maintenance_outputs["Block Line"] = block_line
        maintenance_outputs["Closed Block"] = closed_block

        data["MaintenenceModeOutputs"] = maintenance_outputs
        self.save_data(data)

    def setup_auto_frame(self):
        # Auto Frame UI 
        self.auto_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Load and run schedule section
        upload_button = tk.Button(self.auto_frame,text="Upload Schedule", command=self.upload_schedule, width=40,height=1,bg="white",relief="flat",bd=0,font=("Times New Roman",15,"bold"))
        upload_button.grid(row=0, column=0, columnspan=4,pady=10)

        self.uploaded_file_label = tk.Label(self.auto_frame, text="", bg="lightblue", font=('Times New Roman', 12, 'italic'))
        self.uploaded_file_label.grid(row=1, column=0, columnspan=4,pady=(0,10))

        run_button = tk.Button(self.auto_frame, text="Run", width=20,height=1,bg="white",relief="flat",bd=0,font=("Times New Roman",15,"bold"))
        run_button.grid(row=2, column=0, columnspan=4,pady=10)

    def upload_schedule(self):
        file_path = filedialog.askopenfilename(
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

    def setup_bottom_frame(self):
        # Tables Below Mode Area 
        bottom_frame = tk.Frame(self.root)
        bottom_frame.grid(row=3, column=0, sticky='nsew', padx=10, pady=10)
        self.root.grid_rowconfigure(3, weight=1)
        bottom_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Add each section
        active_trains_frame, self.active_trains_table = self.create_table_section(
            bottom_frame,
            "Active Trains",
            ("Train", "Line", "Block", "State", "Speed (mph)", "Authority (yards)", "Current Station", "Destination", "Arrival Time"),
            []
        )
        active_trains_frame.grid(row=0, column=0, columnspan=3,sticky='nsew', padx=10)

        lights_frame, self.lights_table = self.create_table_section(
            bottom_frame,
            "Lights",
            ("Line", "Block", "Status"),
            [("Red", "A1", "Green"), ("Red", "A2", "Red")]
        )
        lights_frame.grid(row=0, column=3, columnspan=1,sticky='nsew', padx=5)

        gates_frame, self.gates_table = self.create_table_section(
            bottom_frame,
            "Gates",
            ("Line", "Block", "Status"),
            [("Red", "A1", "Closed"), 
             ("Red", "A2", "Closed")]
        )
        gates_frame.grid(row=0, column=4, columnspan=1,sticky='nsew', padx=5)

        # Throughput 
        throughput_frame = tk.Frame(bottom_frame)
        throughput_frame.grid(row=1, column=0, columnspan=3, sticky='ew', pady=(10, 0))
        throughput_frame.grid_columnconfigure((0, 1), weight=1)

        tk.Label(throughput_frame, text=f"Red Line: 20 passengers/hour", font=('Times New Roman', 20, 'bold')).grid(row=0, column=0, sticky='w', padx=20)
        tk.Label(throughput_frame, text="Green Line: 14 passengers/hour", font=('Times New Roman', 20, 'bold')).grid(row=0, column=1, sticky='w', padx=20)

    def create_table_section(self, parent, title, columns, data):
        section = tk.Frame(parent)
        section.grid_rowconfigure(1, weight=1)
        section.grid_columnconfigure(0, weight=1)

        tk.Label(section, text=title, font=('Times New Roman', 20, 'bold')).grid(row=0, column=0, sticky='w')

        style = ttk.Style()
        style.configure("Custom.Treeview.Heading",font=('Times New Roman',10,'bold'))

        table = ttk.Treeview(section, columns=columns, show='headings',style="Custom.Treeview")
        for col in columns:
            table.heading(col, text=col)
            table.column(col, anchor='center', width=80)
        table.grid(row=1, column=0, sticky='nsew')

        for row in data:
            table.insert('', 'end', values=row)

        return section, table

    def update_active_trains_table(self):
        if not os.path.exists(self.data_file):
            return

        try:
            with open(self.data_file, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return

        dispatcher_data = data.get("Dispatcher", {})

        # Clear current rows
        for row in self.active_trains_table.get_children():
            self.active_trains_table.delete(row)

        trains = dispatcher_data.get("Trains", {})

        for train_name, info in trains.items():
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

        # Repeat using synchronized interval
        interval_ms = self.time_controller.get_update_interval_ms()
        self.root.after(interval_ms, self.update_active_trains_table)

    def setup_file_watcher(self):
        class FileChangeHandler(FileSystemEventHandler):
            def __init__(self, ctc_ui):
                self.ctc_ui = ctc_ui
                
            def on_modified(self, event):
                if event.src_path.endswith("ctc_data.json"):
                    self.ctc_ui.root.after(100, self.ctc_ui.update_active_trains_table)

        event_handler = FileChangeHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, path=os.path.dirname(self.data_file) or ".", recursive=False)
        threading.Thread(target=self.observer.start, daemon=True).start()

    def on_closing(self):
        if self.observer:
            self.observer.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()
        if self.observer:
            self.observer.join()


if __name__ == "__main__":
    app = CTCUI()
    app.run()