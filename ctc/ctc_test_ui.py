import tkinter as tk 
from tkinter import ttk
from tkinter import filedialog

# Root window 
root = tk.Tk()
root.title("CTC Test User Interface")
root.geometry("1550x650")
root.grid_rowconfigure(3,weight=1)
root.grid_columnconfigure(0,weight=1)

label_font = ('Times New Roman', 12, 'bold')

# Force inputs text 
force_inputs_frame = tk.Frame(root) 
force_inputs_frame.grid(row=0,column=0,sticky='w', padx=10,pady=5)
tk.Label(force_inputs_frame,text="Force Inputs",font=("Times New Roman",20,'bold')).pack()

# Inputs frame 
inputs_frame = tk.Frame(root)
inputs_frame.grid(row=1,column=0,sticky='nsew', padx=10,pady=5)

# Dispatcher frame 
dispatcher_frame = tk.LabelFrame(inputs_frame,text='Dispatcher Inputs',font=label_font)
dispatcher_frame.grid_columnconfigure((0,1),weight=1)
dispatcher_frame.grid(row=1,column=0,sticky='nsew',padx=5,pady=5)

tk.Label(dispatcher_frame, text="Train",font=label_font).grid(row=1,column=0,sticky='w',padx=5,pady=10)
tk.Label(dispatcher_frame, text="Line",font=label_font).grid(row=2,column=0,sticky='w',padx=5,pady=10)
tk.Label(dispatcher_frame, text="Section and Block",font=label_font).grid(row=3,column=0,sticky='w',padx=5,pady=10)
tk.Label(dispatcher_frame, text="State",font=label_font).grid(row=4,column=0,sticky='w',padx=5,pady=10)
tk.Label(dispatcher_frame, text="Suggested Speed (mph)",font=label_font).grid(row=5,column=0,sticky='w',padx=5,pady=10)
tk.Label(dispatcher_frame, text="Authority (yards)",font=label_font).grid(row=6,column=0,sticky='w',padx=5,pady=10)
tk.Label(dispatcher_frame, text="Direction",font=label_font).grid(row=7,column=0,sticky='w',padx=5,pady=10)
tk.Label(dispatcher_frame, text="Station",font=label_font).grid(row=8,column=0,sticky='w',padx=5,pady=10)
tk.Label(dispatcher_frame, text="Arrival Time",font=label_font).grid(row=9,column=0,sticky='w',padx=5,pady=10)

train_box = ttk.Combobox(dispatcher_frame,values=["Train 1","Train 2","Train 3"], font=label_font)
train_box.grid(row=1,column=1,padx=5,pady=5,sticky='ew')

line_box = ttk.Combobox(dispatcher_frame,values=["Blue","Red","Green"], font=label_font)
line_box.grid(row=2,column=1,padx=5,pady=5,sticky='ew')

block_box = tk.Entry(dispatcher_frame,font=label_font)
block_box.grid(row=3,column=1,padx=5,pady=5,sticky='ew')

state_box =  ttk.Combobox(dispatcher_frame,values=["Running", "Not Running"], font=label_font)
state_box.grid(row=4,column=1,padx=5,pady=5,sticky='ew')

suggested_speed_box = tk.Entry(dispatcher_frame,font=label_font)
suggested_speed_box.grid(row=5,column=1,padx=5,pady=5,sticky='ew')

authority_box = tk.Entry(dispatcher_frame,font=label_font)
authority_box.grid(row=6,column=1,padx=5,pady=5,sticky='ew')

direction_box =  ttk.Combobox(dispatcher_frame,values=["CW", "CCW"], font=label_font)
direction_box.grid(row=7,column=1,padx=5,pady=5,sticky='ew')

station_box =  ttk.Combobox(dispatcher_frame,values=["1", "2"], font=label_font)
station_box.grid(row=8,column=1,padx=5,pady=5,sticky='ew')

arrival_time_box = tk.Entry(dispatcher_frame,font=label_font)
arrival_time_box.grid(row=9,column=1,padx=5,pady=5,sticky='ew')


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

button_style = {
    "bg": "lightgreen",
    "relief": "flat",
    "bd": 0,
    "activebackground": "#ddd"
}

upload_button = tk.Button(dispatcher_frame,text="Upload Schedule",command=upload_schedule,font=('Times New Roman',15,'bold'),**button_style)
upload_button.grid(row=11,column=0,columnspan=2,padx=5,pady=5,sticky='nsew',)

uploaded_file_label=tk.Label(dispatcher_frame,text="",font=('Times New Roman',12,'italic'))
uploaded_file_label.grid(row=12,column=1,padx=0,pady=0,sticky='nsew')

def get_dispatcher_inputs():
    data = {
        "Train": train_box.get(),
        "Line": line_box.get(),
        "Section and Block": block_box.get(),
        "State": state_box.get(),
        "Suggested Speed": suggested_speed_box.get(),
        "Authority": authority_box.get(),
        "Direction": direction_box.get(),
        "Station": station_box.get(),
        "Arrival Time": arrival_time_box.get(),
    }
    train_input = data["Train"]
    line_input = data["Line"]
    section_block_input = data["Section and Block"]
    state_input =  data["State"]
    sugg_speed_input = data["Suggested Speed"]
    authority_input = data["Authority"]
    direction_input = data["Direction"]
    station_input = data["Station"]
    arrival_time_input = data["Arrival Time"]

save_button = tk.Button(
    dispatcher_frame,
    text="Save",
    command=get_dispatcher_inputs, 
    font=('Times New Roman', 15, 'bold'),
    bg="lightgray"
)
save_button.grid(row=10, column=0, columnspan=2, pady=20)

# Track Model Frame 
track_model_frame = tk.LabelFrame(inputs_frame,text='Track Model Inputs',font=label_font)
track_model_frame.grid(row=1,column=3,sticky='nsew',padx=5,pady=5)

tk.Label(track_model_frame, text="Station",font=label_font).grid(row=2,column=3,sticky='w',padx=5,pady=10)
tk.Label(track_model_frame, text="Passengers Leaving Station",font=label_font).grid(row=3,column=3,sticky='w',padx=5,pady=10)
tk.Label(track_model_frame, text="Passengers Entering Station",font=label_font).grid(row=4,column=3,sticky='w',padx=5,pady=10)

station_box = ttk.Combobox(track_model_frame,values=["1","2","3"],font=label_font)
station_box.grid(row=2,column=4,padx=5,pady=5,sticky='ew')

leaving_box = tk.Entry(track_model_frame,font=label_font)
leaving_box.grid(row=3,column=4,padx=5,pady=5,sticky='ew')

entering_box = tk.Entry(track_model_frame,font=label_font)
entering_box.grid(row=4,column=4,padx=5,pady=5,sticky='ew')

def get_track_model_inputs():
    data = {
        "Station": station_box.get(),
        "Passengers Leaving Station": leaving_box.get(),
        "Passengers Entering Station": entering_box.get(),
    }
    station_input = data["Station"]
    leaving_input = data["Passengers Leaving Station"]
    entering_input = data["Passengers Entering Station"]

save_button_tm = tk.Button(
    track_model_frame,
    text="Save",
    command=get_track_model_inputs,
    font=('Times New Roman', 15, 'bold'),
    bg="lightgray"
)
save_button_tm.grid(row=6, column=3, columnspan=2, pady=10)

    
# Track Controller Frame 
track_controller_frame = tk.LabelFrame(inputs_frame,text='Track Controller Inputs', font=label_font)
track_controller_frame.grid(row=1,column=1,sticky='nsew',padx=20,pady=20)

tk.Label(track_controller_frame, text="Train Position",font=label_font).grid(row=2,column=0,sticky='w',padx=5,pady=10)
tk.Label(track_controller_frame, text="State of the Train",font=label_font).grid(row=3,column=0,sticky='w',padx=5,pady=10)
tk.Label(track_controller_frame, text="Track Failure Mode",font=label_font).grid(row=4,column=0,sticky='w',padx=5,pady=10)

position_box = tk.Entry(track_controller_frame,font=label_font)
position_box.grid(row=2,column=1, sticky='ew',padx=20,pady=20)

state_box = ttk.Combobox(track_controller_frame,values=["Running","Not Running"],font=label_font)
state_box.grid(row=3,column=1,sticky='ew',padx=20,pady=20)

failure_box = ttk.Combobox(track_controller_frame,values=["None","Broken Track","Circuit Failure","Power Failure"],font=label_font)
failure_box.grid(row=4,column=1,sticky='ew',padx=20,pady=20)

# Lights and Gates Frame 
lights_gates_frame = tk.LabelFrame(track_controller_frame,text='Lights and Gates',font=label_font)
lights_gates_frame.grid_columnconfigure((0,1),weight=1)
lights_gates_frame.grid(row=5, column=0, columnspan=2, sticky='nw', padx=20, pady=20)

tk.Label(lights_gates_frame,text="Section and Block",font=label_font).grid(row=6,column=0, sticky='nsew',padx=10,pady=10)
section_block_box1 = tk.Entry(lights_gates_frame,font=label_font)
section_block_box1.grid(row=6,column=1,sticky='w',padx=10,pady=10)
tk.Label(lights_gates_frame,text="Light Color",font=label_font).grid(row=6,column=2, sticky='nsew',padx=10,pady=10)
light_color_box = ttk.Combobox(lights_gates_frame,values=["Green","Red"],font=label_font)
light_color_box.grid(row=6,column=3,sticky='nsew',padx=10,pady=10)

tk.Label(lights_gates_frame,text="Section and Block",font=label_font).grid(row=7,column=0, sticky='nsew',padx=10,pady=10)
section_block_box2 = tk.Entry(lights_gates_frame,font=label_font)
section_block_box2.grid(row=7,column=1,sticky='w',padx=10,pady=10)
tk.Label(lights_gates_frame,text="Gate",font=label_font).grid(row=7,column=2, sticky='nsew',padx=10,pady=10)
gate_box = ttk.Combobox(lights_gates_frame,values=["Open","Closed"],font=label_font)
gate_box.grid(row=7,column=3,sticky='nsew',padx=10,pady=10)

def get_track_controller_inputs():
    data = {
        "Train Position": position_box.get(),
        "State of the Train": state_box.get(),
        "Track Failure Mode": failure_box.get(),
        "Section and Block1": section_block_box1.get(),
        "Light Color": light_color_box.get(),
        "Section and Block2": section_block_box2.get(),
        "Gate": gate_box.get(),
    }
    train_position_input = data["Train Position"]
    train_state_input = data["State of the Train"]
    track_failure_mode_input = data["Track Failure Mode"]
    light_loc = data["Section and Block1"]
    light_color = data["Light Color"]
    gate_loc = data["Section and Block2"]
    gate_status = data["Gate"]

save_button_tc = tk.Button(
    track_controller_frame,
    text="Save",
    command=get_track_controller_inputs,
    font=('Times New Roman', 15, 'bold'),
    bg="lightgray"
)
save_button_tc.grid(row=6, column=0, columnspan=2, pady=20)


root.mainloop()