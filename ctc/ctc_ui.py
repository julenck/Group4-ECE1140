import tkinter as tk, json, os, threading
from tkinter import filedialog, ttk 
from watchdog.observers import Observer 
from watchdog.events import FileSystemEventHandler 

# json file set up 
data_file = "ctc_data.json"

def load_data():
    if os.path.exists(data_file):
        with open(data_file, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def update_labels():
    data = load_data()
    dispatcher = data.get("Dispatcher", {})
    track_controller = data.get("TrackController", {})
    track_model = data.get("TrackModel", {})

    # Dispatcher
    #active_trains_table.delete(*active_trains_table.get_children())
    train_data = dispatcher.get("Train", "")
    line_data = dispatcher.get("Line","")
    sugg_speed_data = dispatcher.get("Suggested Speed","")
    authority_data = dispatcher.get("Authority","")
    station_dest_data = dispatcher.get("Station Destination","")
    arrival_time_data = dispatcher.get("Arrival Time","")

    # Track Controller 
    lights_table.delete(*lights_table.get_children())
    gates_table.delete(*gates_table.get_children())
    train_position_data = track_controller.get("Train Position","")
    state_of_train_data = track_controller.get("State of the Train","")
    failure_mode_data = track_controller.get("Track Failure Mode","")
    lights_gates_line = track_controller.get("Line","")
    light_loc_data = track_controller.get("Section and Block1","")
    light_color_data = track_controller.get("Light Color","")
    gate_loc_data = track_controller.get("Section and Block2","")
    gate_data = track_controller.get("Gate","")

    # Track Model 
    station_data = track_model.get("Station", "")
    passengers_leaving_data = track_model.get("Passengers Leaving Station")
    passengers_entering_data = track_model.get("Passengers Entering Station")

    active_trains_table.insert("", "end", values=(train_data, line_data, train_position_data, state_of_train_data, sugg_speed_data, authority_data, "", station_dest_data, arrival_time_data, ""))
    lights_table.insert("","end",values=(lights_gates_line,light_loc_data,light_color_data))
    gates_table.insert("","end",values=(lights_gates_line,gate_loc_data,gate_data))

class FileChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith("ctc_data.json"):
            root.after(100, update_labels)

# Root window
root = tk.Tk()
root.title("CTC User Interface")
root.geometry("1500x700")
root.grid_rowconfigure(3, weight=1)  
root.grid_columnconfigure(0, weight=1)

# Top Row: Date/Time
datetime_frame = tk.Frame(root)
datetime_frame.grid(row=0, column=0, sticky="w", padx=10, pady=5)

tk.Label(datetime_frame, text="9/30/2025", font=('Times New Roman', 15, 'bold')).pack(side='left')
tk.Label(datetime_frame, text="    4:12 PM", font=('Times New Roman', 15, 'bold')).pack(side='left')

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
tk.Label(manual_frame, text="Enter Suggested Speed in mph", font=label_font, bg="lightgreen").grid(row=0, column=2, sticky='w', padx=10, pady=5)
tk.Label(manual_frame, text="Enter Authority in yards", font=label_font, bg="lightgreen").grid(row=0, column=3, sticky='w', padx=10, pady=5)

manual_train_box = ttk.Combobox(manual_frame, values=["Train 1", "Train 2", "Train 3"], font=input_font)
manual_line_box = ttk.Combobox(manual_frame, values=["Red", "Blue", "Green"], font=input_font)
manual_sugg_speed_box = tk.Entry(manual_frame, font=input_font)
manual_authority_box = tk.Entry(manual_frame, font=input_font)

manual_train_box.grid(row=1, column=0, padx=5, sticky='ew')
manual_line_box.grid(row=1, column=1, padx=5, sticky='ew')
manual_sugg_speed_box.grid(row=1, column=2, padx=5, sticky='ew')
manual_authority_box.grid(row=1, column=3, padx=5, sticky='ew')

manual_dispatch_button = tk.Button(manual_frame,text='DISPATCH',**button_style)
manual_dispatch_button.grid(row=2,column=0,columnspan=4,pady=10,padx=500,sticky='ew')

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

move_switch_button = tk.Button(switch_frame, text='Move Switch', **button_style)
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

close_block_button = tk.Button(block_frame, text='Close Block', **button_style)
close_block_button.grid(row=2, column=0, columnspan=2, padx=100,pady=10, sticky='ew')

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
run_schedule_frame = tk.LabelFrame(auto_frame, text="Load and Run Schedule", bg="lightblue", font=label_font)
run_schedule_frame.grid(row=0, column=0, padx=20, pady=10, sticky='nsew')
run_schedule_frame.grid_columnconfigure(0, weight=1)

upload_button = tk.Button(run_schedule_frame, text="Upload Schedule", command=upload_schedule, **button_style)
upload_button.grid(row=0, column=0, padx=10, pady=10, sticky='ew')

uploaded_file_label = tk.Label(run_schedule_frame, text="", bg="lightblue", font=('Times New Roman', 12, 'italic'))
uploaded_file_label.grid(row=1, column=0, padx=10, pady=(0,10), sticky='w')

run_button = tk.Button(run_schedule_frame, text="Run", **button_style)
run_button.grid(row=2, column=0, padx=50, pady=10, sticky='ew')

# Dispatch section 
dispatch_frame = tk.LabelFrame(auto_frame, text="", bg="lightblue", font=label_font)
dispatch_frame.grid(row=0, column=1, padx=20, pady=10, sticky='nsew')
dispatch_frame.grid_columnconfigure((0, 1), weight=1)

tk.Label(dispatch_frame, text="Select a Train to Dispatch", font=label_font, bg="lightblue").grid(row=0, column=0, sticky='w', padx=5, pady=5)
auto_train_box = ttk.Combobox(dispatch_frame, values=["Train 1", "Train 2", "Train 3", "Train 4", "Train 5"], font=input_font)
auto_train_box.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

tk.Label(dispatch_frame, text="Select a Line", font=label_font, bg="lightblue").grid(row=1, column=0, sticky='w', padx=5, pady=5)
auto_line_box = ttk.Combobox(dispatch_frame, values=["Red", "Green"], font=input_font)
auto_line_box.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

tk.Label(dispatch_frame, text="Select a Destination Station", font=label_font, bg="lightblue").grid(row=2, column=0, sticky='w', padx=5, pady=5)
auto_dest_box = ttk.Combobox(dispatch_frame, values=["Shadyside", "Pioneer", "Edgeworth", "Herron Ave", "Whited"], font=input_font)
auto_dest_box.grid(row=2, column=1, padx=5, pady=5, sticky='ew')

tk.Label(dispatch_frame, text="Enter Arrival Time", font=label_font, bg="lightblue").grid(row=3, column=0, sticky='w', padx=5, pady=5)
auto_arrival_box = tk.Entry(dispatch_frame, font=input_font)
auto_arrival_box.grid(row=3, column=1, padx=5, pady=5, sticky='ew')

dispatch_button = tk.Button(dispatch_frame, text="DISPATCH", **button_style)
dispatch_button.grid(row=4, column=0, columnspan=2, padx=50, pady=10, sticky='ew')

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

    tk.Label(section, text=title, font=('Times New Roman', 15, 'bold')).grid(row=0, column=0, sticky='w')

    table = ttk.Treeview(section, columns=columns, show='headings')
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
    ("Train", "Line", "Block", "State", "Suggested Speed", "Authority", "Direction", "Station", "Arrival Time"),
    []
)
active_trains_frame.grid(row=0, column=0, sticky='nsew', padx=5)


def update_active_trains_table():
    """Refresh the Active Trains table from JSON file."""
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

    # If you saved multiple trains in your JSON
    trains = dispatcher_data.get("Trains", {})

    for train_name, info in trains.items():
        active_trains_table.insert("", "end", values=(
            train_name,
            info.get("Line", ""),
            "",  # Block (if not stored yet)
            info.get("State", ""),
            info.get("Suggested Speed", ""),
            info.get("Authority", ""),
            info.get("Direction", ""),
            info.get("Station Destination", ""),
            info.get("Arrival Time", "")
        ))

    # Repeat every second
    root.after(1000, update_active_trains_table)

lights_frame,lights_table = create_table_section(
    bottom_frame,
    "Lights",
    ("Line", "Block", "Status"),
    [("Red", "A1", "Green"), ("Red", "A2", "Red")]
)
lights_frame.grid(row=0, column=1, sticky='nsew', padx=5)

gates_frame,gates_table = create_table_section(
    bottom_frame,
    "Gates",
    ("Line", "Block", "Status"),
    [("Red", "A1", "Closed"), 
     ("Red", "A2", "Closed")]
)
gates_frame.grid(row=0, column=2, sticky='nsew', padx=5)


# Throughput 
throughput_frame = tk.Frame(bottom_frame)
throughput_frame.grid(row=1, column=0, columnspan=3, sticky='ew', pady=(10, 0))
throughput_frame.grid_columnconfigure((0, 1), weight=1)

tk.Label(throughput_frame, text=f"Train", font=('Times New Roman', 20, 'bold')).grid(row=0, column=0, sticky='w', padx=20)
tk.Label(throughput_frame, text="Green Line: 14 passengers/hour", font=('Times New Roman', 20, 'bold')).grid(row=0, column=1, sticky='w', padx=20)

event_handler = FileChangeHandler()
observer = Observer()
observer.schedule(event_handler, path=os.path.dirname(data_file) or ".", recursive=False)
threading.Thread(target=observer.start, daemon=True).start()

# Show default frame 
show_frame(auto_frame)
auto_button.config(bg="lightgray")
active_button = auto_button

# Start event loop
update_labels()
root.protocol("WM_DELETE_WINDOW", lambda: (observer.stop(), root.destroy()))
update_active_trains_table()
root.mainloop()
observer.join()