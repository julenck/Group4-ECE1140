import tkinter as tk
from tkinter import filedialog

# --- Functions ---

def simulate():

    # Read force input values
    suggested_speed = speed_entry.get()
    authority = authority_entry.get()
    track_closures = track_closures_entry.get()
    route = route_entry.get()
    failure_alerts = failure_entry.get()
    train_positions = train_positions_entry.get()
    passengers = passengers_entry.get()
    switch_positions = switch_entry.get()

    # Simple output logic (can be expanded later)
    beacon_value.set("128B")
    switch_output.set(switch_positions)
    commanded_speed.set(f"{int(suggested_speed.replace('mph','')) - 2}mph")
    authority_output.set(authority)
    lights_output.set("Green")                                  #Light logic needs to be implemented    
    gates_output.set("Closed")                                  #Gate logic needs to be implemented
    state_of_track.set("2 Trains Active")                       #State of track logic needs to be implemented
    train_positions_output.set(train_positions)
    passengers_output.set(passengers)

def stop_simulation():
    # Reset outputs
    beacon_value.set("")
    switch_output.set("")
    commanded_speed.set("")
    authority_output.set("")
    lights_output.set("")
    gates_output.set("")
    state_of_track.set("")
    train_positions_output.set("")
    passengers_output.set("")

def upload_schedule():
    filedialog.askopenfilename(title="Select Schedule File")        #Do we get this from CTC?


# --- Main Window ---
root = tk.Tk()
root.title("Wayside Controller Test UI")

# Left Frame (Force Input)
frame_left = tk.Frame(root, padx=10, pady=10)
frame_left.grid(row=0, column=0, sticky="n")

tk.Label(frame_left, text="Force Input", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2)

tk.Label(frame_left, text="Suggested Speed").grid(row=1, column=0, sticky="w")
speed_entry = tk.Entry(frame_left)
speed_entry.insert(0, "22mph")
speed_entry.grid(row=1, column=1)

tk.Label(frame_left, text="Authority").grid(row=2, column=0, sticky="w")
authority_entry = tk.Entry(frame_left)
authority_entry.insert(0, "Block C1")
authority_entry.grid(row=2, column=1)

tk.Label(frame_left, text="Track Closures").grid(row=3, column=0, sticky="w")
track_closures_entry = tk.Entry(frame_left)
track_closures_entry.insert(0, "None")
track_closures_entry.grid(row=3, column=1)

tk.Label(frame_left, text="Route").grid(row=4, column=0, sticky="w")
route_entry = tk.Entry(frame_left)
route_entry.insert(0, "Red")
route_entry.grid(row=4, column=1)

tk.Label(frame_left, text="Failure Alerts").grid(row=5, column=0, sticky="w")
failure_entry = tk.Entry(frame_left)
failure_entry.insert(0, "None")
failure_entry.grid(row=5, column=1)

tk.Label(frame_left, text="Train Positions").grid(row=6, column=0, sticky="w")
train_positions_entry = tk.Entry(frame_left)
train_positions_entry.insert(0, "Block(s) A1")
train_positions_entry.grid(row=6, column=1)

tk.Label(frame_left, text="Passengers Disembarking").grid(row=7, column=0, sticky="w")
passengers_entry = tk.Entry(frame_left)
passengers_entry.insert(0, "15")
passengers_entry.grid(row=7, column=1)

tk.Label(frame_left, text="Schedule").grid(row=8, column=0, sticky="w")
tk.Button(frame_left, text="File Upload", command=upload_schedule).grid(row=8, column=1)

tk.Label(frame_left, text="Switch Positions").grid(row=9, column=0, sticky="w")
switch_entry = tk.Entry(frame_left)
switch_entry.insert(0, "0")
switch_entry.grid(row=9, column=1)

# Buttons
tk.Button(frame_left, text="Simulate", command=simulate).grid(row=10, column=0, pady=10)
tk.Button(frame_left, text="Stop Simulation", command=stop_simulation).grid(row=10, column=1, pady=10)

# Right Frame (Generated Output)
frame_right = tk.Frame(root, padx=10, pady=10)
frame_right.grid(row=0, column=1, sticky="n")

tk.Label(frame_right, text="Generated Output", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2)

def make_output(label, row):
    tk.Label(frame_right, text=label).grid(row=row, column=0, sticky="w")
    var = tk.StringVar()
    tk.Label(frame_right, textvariable=var).grid(row=row, column=1, sticky="w")
    return var

beacon_value = make_output("Beacon", 1)
switch_output = make_output("Switch Positions", 2)
commanded_speed = make_output("Commanded Speed", 3)
authority_output = make_output("Authority", 4)
lights_output = make_output("Lights", 5)
gates_output = make_output("Gates", 6)
state_of_track = make_output("State of Track", 7)
train_positions_output = make_output("Train Positions", 8)
passengers_output = make_output("Passengers Disembarking", 9)

root.mainloop()