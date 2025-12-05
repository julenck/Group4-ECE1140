from ctc_ui_temp import CTCUI

if __name__ == "__main__":
    ui = CTCUI()
    ui.run()
import tkinter as tk, json, os, threading, subprocess, sys
from datetime import datetime
from tkinter import filedialog, ttk 
from watchdog.observers import Observer 
from watchdog.events import FileSystemEventHandler 

from track_controller.New_SW_Code import sw_wayside_controller, sw_vital_check

# Add train_controller to path for train dispatch integration
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'train_controller'))

# Set up json file 
data_file = 'ctc_data.json'

# load_data
def load_data():
    if os.path.exists(data_file):
        with open(data_file, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

default_data = {
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

# Check if json file structure is ok 
if not os.path.exists(data_file) or os.stat(data_file).st_size == 0:
    with open(data_file, "w") as f:
        json.dump(default_data, f, indent=4)
else:
    try:
        with open(data_file, "r") as f:
            json.load(f)
    except json.JSONDecodeError:
        # Recreate file if it's corrupted or empty
        with open(data_file, "w") as f:
            json.dump(default_data, f, indent=4)

# save_data 
def save_data(data):
    with open(data_file, "w") as f:
        json.dump(data, f, indent=4)

class FileChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith("ctc_data.json"):
            root.after(100, update_active_trains_table)

# Root window
root = tk.Tk()
root.title("CTC User Interface")
root.geometry("1500x700")
root.grid_rowconfigure(3, weight=1)  
root.grid_columnconfigure(0, weight=1)

# Top Row: Date/Time
datetime_frame = tk.Frame(root)
datetime_frame.grid(row=0, column=0, sticky="w", padx=10, pady=5)

date_label = tk.Label(datetime_frame, font=('Times New Roman', 15, 'bold'))
date_label.pack(side='left')
time_label = tk.Label(datetime_frame, font=('Times New Roman', 15, 'bold'))
time_label.pack(side='left')

def update_datetime(): 
    now = datetime.now()
    date_label.config(text=now.date())
    time_label.config(text=f"      {now.strftime("%H:%M:%S")}")
    root.after(1000,update_datetime)

update_datetime()

# Button Row
button_frame = tk.Frame(root)
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

active_button = None

# Middle Area: Main Frame Container
main_area = tk.Frame(root)
main_area.grid(row=2, column=0, sticky='nsew', padx=10)
main_area.grid_rowconfigure(0, weight=1)
main_area.grid_columnconfigure(0, weight=1)

# Mode Frames (Manual, Auto, Maint) 
manual_frame = tk.Frame(main_area, bg="lightgreen")
auto_frame = tk.Frame(main_area, bg="lightblue")
maint_frame = tk.Frame(main_area, bg="lightyellow")

for frame in (manual_frame, auto_frame, maint_frame):
    frame.grid(row=0, column=0, sticky="nsew")

# Frame Toggle Function 
def show_frame(frame, clicked_button=None):
    global active_button
    frame.tkraise()

    # Reset all button colors to white
    for btn in [auto_button, manual_button, maint_button]:
        btn.config(bg="white", fg="black")

    # Highlight the active one (if provided)
    if clicked_button:
        clicked_button.config(bg="lightgray", fg="black")
        active_button = clicked_button

# Buttons to switch frames 
auto_button = tk.Button(
    button_frame, 
    text='Automatic', 
    command=lambda: show_frame(auto_frame, auto_button), 
    **button_style
)
auto_button.grid(row=0, column=0, sticky='ew', padx=5)

manual_button = tk.Button(
    button_frame, 
    text='Manual', 
    command=lambda: show_frame(manual_frame, manual_button), 
    **button_style
)
manual_button.grid(row=0, column=1, sticky='ew', padx=5)

maint_button = tk.Button(
    button_frame, 
    text='Maintenance', 
    command=lambda: show_frame(maint_frame, maint_button), 
    **button_style
)
maint_button.grid(row=0, column=2, sticky='ew', padx=5)


# Manual Frame UI 
label_font = ('Times New Roman', 12, 'bold')
input_font = ('Times New Roman', 12, 'bold')
manual_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

tk.Label(manual_frame, text="Select a Train to Dispatch", font=label_font, bg="lightgreen").grid(row=0, column=0, sticky='w', padx=10, pady=5)
tk.Label(manual_frame, text="Select a Line", font=label_font, bg="lightgreen").grid(row=0, column=1, sticky='w', padx=10, pady=5)
tk.Label(manual_frame, text="Select a Destination Station", font=label_font, bg="lightgreen").grid(row=0, column=2, sticky='w', padx=10, pady=5)
tk.Label(manual_frame, text="Enter Arrival Time", font=label_font, bg="lightgreen").grid(row=0, column=3, sticky='w', padx=10, pady=5)

manual_train_box = ttk.Combobox(manual_frame, values=["Train 1", "Train 2", "Train 3", "Train 4", "Train 5"], font=input_font)
manual_line_box = ttk.Combobox(manual_frame, values=["Green"], font=input_font)
manual_dest_box = ttk.Combobox(manual_frame, values=["Pioneer",
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
manual_time_box = tk.Entry(manual_frame, font=input_font)

manual_train_box.grid(row=1, column=0, padx=5, sticky='ew')
manual_line_box.grid(row=1, column=1, padx=5, sticky='ew')
manual_dest_box.grid(row=1, column=2, padx=5, sticky='ew')
manual_time_box.grid(row=1, column=3, padx=5, sticky='ew')

manual_dispatch_button = tk.Button(manual_frame, text='DISPATCH', command=lambda: manual_dispatch(), **button_style)
manual_dispatch_button.grid(row=2,column=0,columnspan=4,pady=10,padx=500,sticky='ew')

def manual_dispatch():
    train = manual_train_box.get()
    line = manual_line_box.get()
    dest = manual_dest_box.get()
    arrival = manual_time_box.get()

    ############# write to ctc_ui_inputs.json ##############
    with open(os.path.join('ctc', 'ctc_ui_inputs.json'),"r") as f1: 
        data1 = json.load(f1)
    
    data1["Train"] = train
    data1["Line"] = line
    data1["Station"] = dest
    data1["Arrival Time"] = arrival

    with open(os.path.join('ctc', 'ctc_ui_inputs.json'),"w") as f1: 
        json.dump(data1,f1,indent=4)

    update_active_trains_table()

    # Run ctc_main.py to update ctc_data.json
    python_exe = sys.executable 
    script_path = os.path.join(os.path.dirname(__file__), "ctc_main.py")
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

# Maintenance Frame UI 
maint_frame.grid_columnconfigure((0,1,2,3),weight=1)

# Set switch positions section 
switch_frame = tk.LabelFrame(maint_frame,text="Set Switch Positions",bg='lightyellow',font=label_font)
switch_frame.grid_columnconfigure((0,1),weight=1)
switch_frame.grid(row=0,column=0,padx=20,pady=10,sticky='nsew')

tk.Label(switch_frame,text="Select a Line",font=label_font,bg="lightyellow").grid(row=0,column=0,sticky='w',padx=5,pady=5)
tk.Label(switch_frame,text="Select Switch",font=label_font,bg="lightyellow").grid(row=1,column=0,sticky='w',padx=5,pady=5)

maint_line_box1 = ttk.Combobox(switch_frame, values=["Red", "Green"], font=input_font)
maint_switch_box = ttk.Combobox(switch_frame, values=["1", "2", "3", "4"], font=input_font)

maint_line_box1.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
maint_switch_box.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

move_switch_button = tk.Button(switch_frame, text='Move Switch', command=lambda: move_switch(),**button_style)
move_switch_button.grid(row=2, column=0, columnspan=2, padx=100,pady=10, sticky='ew')

# Close block section 
block_frame = tk.LabelFrame(maint_frame, text="Close Block", bg="lightyellow", font=label_font)
block_frame.grid_columnconfigure((0,1),weight=1)
block_frame.grid(row=0, column=1, padx=20, pady=10, sticky='nsew')

tk.Label(block_frame, text="Select a Line", font=label_font, bg="lightyellow").grid(row=0, column=0, sticky='w', padx=5, pady=5)
tk.Label(block_frame, text="Select Block", font=label_font, bg="lightyellow").grid(row=1, column=0, sticky='w', padx=5, pady=5)

maint_line_box2 = ttk.Combobox(block_frame, values=["Red", "Green"], font=input_font)
maint_block_box = ttk.Combobox(block_frame, values=["1", "2", "3", "4"], font=input_font)

maint_line_box2.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
maint_block_box.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

close_block_button = tk.Button(block_frame, text='Close Block', command=lambda:close_block(),**button_style)
close_block_button.grid(row=2, column=0, columnspan=2, padx=100,pady=10, sticky='ew')

def move_switch():
    switch_line = maint_line_box1.get()
    switch = maint_switch_box.get()

    data = load_data()

    # Get existing section or create if missing
    maintenance_outputs = data.get("MaintenenceModeOutputs", {})

    # Update only switch data
    maintenance_outputs["Switch Line"] = switch_line
    maintenance_outputs["Switch Position"] = switch

    data["MaintenenceModeOutputs"] = maintenance_outputs
    save_data(data)


def close_block(): 
    block_line = maint_line_box2.get()
    closed_block = maint_block_box.get()

    data = load_data()

    # Get existing section or create if missing
    maintenance_outputs = data.get("MaintenenceModeOutputs", {})

    # Update only block data
    maintenance_outputs["Block Line"] = block_line
    maintenance_outputs["Closed Block"] = closed_block

    data["MaintenenceModeOutputs"] = maintenance_outputs
    save_data(data)


# Auto Frame UI 
auto_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

# Upload Schedule Section 
def upload_schedule():
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
        uploaded_file_label.config(
            text=f"Loaded: {file_path.split('/')[-1]}",
            fg="darkgreen"
        )
        print(f"Selected schedule file: {file_path}")  

# Load and run schedule section
upload_button = tk.Button(auto_frame,text="Upload Schedule", command=upload_schedule, width=40,height=1,bg="white",relief="flat",bd=0,font=("Times New Roman",15,"bold"))
upload_button.grid(row=0, column=0, columnspan=4,pady=10)

uploaded_file_label = tk.Label(auto_frame, text="", bg="lightblue", font=('Times New Roman', 12, 'italic'))
uploaded_file_label.grid(row=1, column=0, columnspan=4,pady=(0,10))

run_button = tk.Button(auto_frame, text="Run", width=20,height=1,bg="white",relief="flat",bd=0,font=("Times New Roman",15,"bold"))
run_button.grid(row=2, column=0, columnspan=4,pady=10)

# Tables Below Mode Area 
bottom_frame = tk.Frame(root)
bottom_frame.grid(row=3, column=0, sticky='nsew', padx=10, pady=10)
root.grid_rowconfigure(3, weight=1)
bottom_frame.grid_columnconfigure((0, 1, 2), weight=1)

# Active Trains Table 
def create_table_section(parent, title, columns, data):
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

    return section,table

# Add each section
active_trains_frame, active_trains_table = create_table_section(
    bottom_frame,
    "Active Trains",
    ("Train", "Line", "Block", "State", "Speed (mph)", "Authority (yards)", "Current Station", "Destination", "Arrival Time"),
    []
)
active_trains_frame.grid(row=0, column=0, columnspan=3,sticky='nsew', padx=10)


def update_active_trains_table():
    if not os.path.exists(data_file):
        return

    try:
        with open(data_file, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return

    dispatcher_data = data.get("Dispatcher", {})

    # Clear current rows
    for row in active_trains_table.get_children():
        active_trains_table.delete(row)

    trains = dispatcher_data.get("Trains", {})

    for train_name, info in trains.items():
        active_trains_table.insert("", "end", values=(
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

    # Repeat every second
    root.after(1000, update_active_trains_table)

lights_frame,lights_table = create_table_section(
    bottom_frame,
    "Lights",
    ("Line", "Block", "Status"),
    [("Red", "A1", "Green"), ("Red", "A2", "Red")]
)
lights_frame.grid(row=0, column=3, columnspan=1,sticky='nsew', padx=5)

gates_frame,gates_table = create_table_section(
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

event_handler = FileChangeHandler()
observer = Observer()
observer.schedule(event_handler, path=os.path.dirname(data_file) or ".", recursive=False)
threading.Thread(target=observer.start, daemon=True).start()

# Show default frame 
show_frame(auto_frame)
auto_button.config(bg="lightgray")
active_button = auto_button

# update_ui()
root.protocol("WM_DELETE_WINDOW", lambda: (observer.stop(), root.destroy()))
update_active_trains_table()
root.mainloop()
observer.join()