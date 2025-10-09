import tkinter as tk 
from tkinter import ttk,filedialog
import json
import os 

data_file = 'ctc_data.json'

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
                "AUthority": "",
                "Station Destination": "",
                "Arrival Time": ""
            },
            "Train 2": {
                "Line": "",
                "Suggested Speed": "",
                "AUthority": "",
                "Station Destination": "",
                "Arrival Time": ""
            },
            "Train 3": {
                "Line": "",
                "Suggested Speed": "",
                "AUthority": "",
                "Station Destination": "",
               "Arrival Time": "" 
            }
        }
    },
    "TrackController": {
        "Train Position": "",
        "State of the Train": "",
        "Train Failure Mode": "",
        "Section and Block1": "",
        "Light Color": "",
        "Section and Block2": "",
        "Gate": ""
    },
    "TrackModel": {
        "Station": "",
        "Passengers Leaving Station": "",
        "Passengers Entering Station": "",
    },
    "MaintenenceModeOutputs": {
        "Block Line": "Green",
        "Closed Block": "3"
    }

}

# Ensure JSON file exists and has valid structure
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


def save_to_json(section, data):
    with open(data_file, "r") as f:
        json_data = json.load(f)
    json_data[section].update(data)
    with open(data_file, "w") as f:
        json.dump(json_data, f, indent=4)
    print(f"{section} data saved:", data)


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
inputs_frame.grid(row=1, column=0, sticky='nsew', padx=10, pady=5)

root.grid_rowconfigure(1, weight=1)
root.grid_columnconfigure(0, weight=1)
inputs_frame.grid_columnconfigure(0, weight=1, uniform="col")
inputs_frame.grid_columnconfigure(1, weight=1, uniform="col")
inputs_frame.grid_columnconfigure(2, weight=1, uniform="col")
inputs_frame.grid_rowconfigure(0, weight=1)

# Dispatcher frame 
dispatcher_frame = tk.LabelFrame(inputs_frame, text='Dispatcher Inputs', font=label_font)
dispatcher_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)

tk.Label(dispatcher_frame, text="Train",font=label_font).grid(row=1,column=0,sticky='w',padx=5,pady=5)
tk.Label(dispatcher_frame, text="Line",font=label_font).grid(row=2,column=0,sticky='w',padx=5,pady=10)
tk.Label(dispatcher_frame, text="Suggested Speed (mph)",font=label_font).grid(row=3,column=0,sticky='w',padx=5,pady=5)
tk.Label(dispatcher_frame, text="Authority (yards)",font=label_font).grid(row=4,column=0,sticky='w',padx=5,pady=5)
tk.Label(dispatcher_frame, text="Station",font=label_font).grid(row=5,column=0,sticky='w',padx=5,pady=5)
tk.Label(dispatcher_frame, text="Arrival Time",font=label_font).grid(row=6,column=0,sticky='w',padx=5,pady=5)

train_box = ttk.Combobox(dispatcher_frame,values=["Train 1","Train 2","Train 3"], font=label_font)
train_box.grid(row=1,column=1,padx=5,pady=5,sticky='ew')

line_box = ttk.Combobox(dispatcher_frame,values=["Blue","Red","Green"], font=label_font)
line_box.grid(row=2,column=1,padx=5,pady=5,sticky='ew')

suggested_speed_box = tk.Entry(dispatcher_frame,font=label_font)
suggested_speed_box.grid(row=3,column=1,padx=5,pady=5,sticky='ew')

authority_box = tk.Entry(dispatcher_frame,font=label_font)
authority_box.grid(row=4,column=1,padx=5,pady=5,sticky='ew')

station_box =  ttk.Combobox(dispatcher_frame,values=["1", "2"], font=label_font)
station_box.grid(row=5,column=1,padx=5,pady=5,sticky='ew')

arrival_time_box = tk.Entry(dispatcher_frame,font=label_font)
arrival_time_box.grid(row=6,column=1,padx=5,pady=5,sticky='ew')


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

def save_train_data():
    train_name = train_box.get()
    if not train_name:
        return  # nothing selected

    with open("ctc_data.json", "r") as f:
        data = json.load(f)

    train_data = {
        "Line": line_box.get(),
        "Suggested Speed": suggested_speed_box.get(),
        "Authority": authority_box.get(),
        "Station Destination": station_box.get(),
        "Arrival Time": arrival_time_box.get(),
    }

    # make sure "Trains" exists
    data.setdefault("Dispatcher", {}).setdefault("Trains", {})
    data["Dispatcher"]["Trains"][train_name] = train_data

    with open("ctc_data.json", "w") as f:
        json.dump(data, f, indent=4)

    print(f"Saved data for {train_name}")

save_button = tk.Button(
    dispatcher_frame,
    text="Save",
    command=save_train_data, 
    font=('Times New Roman', 15, 'bold'),
    bg="lightgray"
)
save_button.grid(row=10, column=0, columnspan=2, pady=20)

# Track Controller Frame 
track_controller_frame = tk.LabelFrame(inputs_frame, text='Track Controller Inputs', font=label_font)
track_controller_frame.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)

tk.Label(track_controller_frame, text="Train Position",font=label_font).grid(row=2,column=0,sticky='w',padx=5,pady=10)
tk.Label(track_controller_frame, text="State of the Train",font=label_font).grid(row=3,column=0,sticky='w',padx=5,pady=10)
tk.Label(track_controller_frame, text="Track Failure Mode",font=label_font).grid(row=4,column=0,sticky='w',padx=5,pady=10)

position_box = tk.Entry(track_controller_frame,font=label_font)
position_box.grid(row=2,column=1, sticky='w',padx=5,pady=20)

state_box = ttk.Combobox(track_controller_frame,values=["Running","Not Running"],font=label_font)
state_box.grid(row=3,column=1,sticky='w',padx=5,pady=20)

failure_box = ttk.Combobox(track_controller_frame,values=["None","Broken Track","Circuit Failure","Power Failure"],font=label_font)
failure_box.grid(row=4,column=1,sticky='w',padx=5,pady=20)

# Lights and Gates Frame 
lights_gates_frame = tk.LabelFrame(track_controller_frame,text='Lights and Gates',font=label_font)
lights_gates_frame.grid_columnconfigure((0,1),weight=1)
lights_gates_frame.grid(row=5, column=0, columnspan=2, sticky='nsew', padx=5, pady=20)

tk.Label(lights_gates_frame,text="Line",font=label_font).grid(row=6,column=0, sticky='nsew',padx=10,pady=10)
lights_gates_line_box = ttk.Combobox(lights_gates_frame,values=["Green","Red","Blue"],font=label_font)
lights_gates_line_box.grid(row=6,column=1,sticky='nsew',padx=10,pady=10)

tk.Label(lights_gates_frame,text="Light Section and Block",font=label_font).grid(row=7,column=0, sticky='nsew',padx=10,pady=10)
section_block_box1 = tk.Entry(lights_gates_frame,font=label_font)
section_block_box1.grid(row=7,column=1,sticky='nw',padx=5,pady=5)

tk.Label(lights_gates_frame,text="Light Color",font=label_font).grid(row=8,column=0, sticky='nsew',padx=10,pady=10)
light_color_box = ttk.Combobox(lights_gates_frame,values=["Green","Red"],font=label_font)
light_color_box.grid(row=8,column=1,sticky='nsew',padx=5,pady=10)

tk.Label(lights_gates_frame,text="Gate Section and Block",font=label_font).grid(row=9,column=0, sticky='nsew',padx=10,pady=10)
section_block_box2 = tk.Entry(lights_gates_frame,font=label_font)
section_block_box2.grid(row=9,column=1,sticky='nsew',padx=5,pady=10)

tk.Label(lights_gates_frame,text="Gate",font=label_font).grid(row=10,column=0, sticky='nsew',padx=10,pady=10)
gate_box = ttk.Combobox(lights_gates_frame,values=["Open","Closed"],font=label_font)
gate_box.grid(row=10,column=1,sticky='nsew',padx=5,pady=10)

def get_track_controller_inputs():
    data = {
        "Train Position": position_box.get(),
        "State of the Train": state_box.get(),
        "Track Failure Mode": failure_box.get(),
        "Section and Block1": section_block_box1.get(),
        "Line": lights_gates_line_box.get(),
        "Light Color": light_color_box.get(),
        "Section and Block2": section_block_box2.get(),
        "Gate": gate_box.get(),
    }
    save_to_json("TrackController",data)

save_button_tc = tk.Button(
    track_controller_frame,
    text="Save",
    command=get_track_controller_inputs,
    font=('Times New Roman', 15, 'bold'),
    bg="lightgray"
)
save_button_tc.grid(row=6, column=0, columnspan=2, pady=20)

# Track Model Inputs
right_col = tk.Frame(inputs_frame)
right_col.grid(row=0, column=2, sticky='nsew', padx=5, pady=5)
right_col.grid_rowconfigure(0, weight=1)
right_col.grid_rowconfigure(1, weight=1)
right_col.grid_columnconfigure(0, weight=1)

track_model_inputs = tk.LabelFrame(right_col, text="Track Model Inputs", font=label_font)
track_model_inputs.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)

tk.Label(track_model_inputs, text="Station", font=label_font).grid(row=0, column=0, sticky='w', padx=10, pady=10)
tk.Label(track_model_inputs, text="Passengers Leaving Station", font=label_font).grid(row=1, column=0, sticky='w', padx=10, pady=10)
tk.Label(track_model_inputs, text="Passengers Entering Station", font=label_font).grid(row=2, column=0, sticky='w', padx=10, pady=10)

station_destination_box = ttk.Combobox(track_model_inputs, values=["1", "2", "3"], font=label_font)
station_destination_box.grid(row=0, column=1, padx=10, pady=10, sticky='ew')

leaving_box = tk.Entry(track_model_inputs, font=label_font)
leaving_box.grid(row=1, column=1, padx=10, pady=10, sticky='ew')

entering_box = tk.Entry(track_model_inputs, font=label_font)
entering_box.grid(row=2, column=1, padx=10, pady=10, sticky='ew')

def get_track_model_inputs():
    data = {
        "Station": station_destination_box.get(),
        "Passengers Leaving Station": leaving_box.get(),
        "Passengers Entering Station": entering_box.get(),
    }
    save_to_json("TrackModel",data)

save_button_tm = tk.Button(
    track_model_inputs,
    text="Save",
    command=get_track_model_inputs,
    font=('Times New Roman', 15, 'bold'),
    bg="lightgray"
)
save_button_tm.grid(row=6, column=3, columnspan=2, pady=10)

# Generated Outputs 
generated_outputs_frame = tk.LabelFrame(right_col, text="Generated Outputs", font=label_font)
generated_outputs_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)

data = load_data()
maint_data = data.get("MaintenenceModeOutputs",{})
switch_line = maint_data.get("Switch Line","")
switch = maint_data.get("Switch Position","")
block_line = maint_data.get("Block Line","")
closed_block = maint_data.get("Closed Block","")

tk.Label(generated_outputs_frame, text="Line:", font=label_font).grid(row=0, column=0, sticky='w', padx=5, pady=10)
tk.Label(generated_outputs_frame,text=f"{switch_line}",font=label_font).grid(row=0,column=1,sticky='w',padx=5,pady=10)
tk.Label(generated_outputs_frame, text="Switch Position:", font=label_font).grid(row=0, column=2, sticky='w', padx=5, pady=10)
tk.Label(generated_outputs_frame,text=f"{switch}",font=label_font).grid(row=0,column=3,sticky='w',padx=5,pady=10)

tk.Label(generated_outputs_frame, text="Line:", font=label_font).grid(row=1, column=0, sticky='w', padx=5, pady=10)
tk.Label(generated_outputs_frame,text=f"{block_line}",font=label_font).grid(row=1,column=1,sticky='w',padx=5,pady=10)
tk.Label(generated_outputs_frame, text="Closed Block:", font=label_font).grid(row=1, column=2, sticky='w', padx=5, pady=10)
tk.Label(generated_outputs_frame,text=f"{closed_block}",font=label_font).grid(row=1,column=3,sticky='w',padx=5,pady=10)

root.mainloop()

