#Wayside Controller Software UI
#Connor Kariotis


#import tkinter and related libraries
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import json
import os
import plc_parser

#variables for window size
WindowWidth = 1200
WindowHeight = 700

class SWTrackControllerUI(tk.Tk):

    def __init__(self, master=None):
        if master is None:
            super().__init__()#initialize the tk.Tk class
        else:
            # If a master is provided, this is being used as a toplevel window
            super().__init__()
            self.master = master

        #set window title and size
        self.title("Track Controller Software Module")
        self.geometry(str(WindowWidth)+"x"+str(WindowHeight))
       # self.geometry(f"{WindowWidth}x{WindowHeight}")

        #initialize loaded inputs
        switchOptions = []#default empty list of switches

        #configure grid layout
        for i in range(3):
            self.grid_columnconfigure(i, weight=1, uniform="col")
        for i in range(2):
            self.grid_rowconfigure(i, weight=1, uniform="row")

        #------Start Maintenance Frame------#
        maintenance_frame = ttk.LabelFrame(self, text="Maintenance Mode:")
        maintenance_frame.grid(row=0, column=0, sticky="NSEW", padx=WindowHeight/70, pady=WindowWidth/120)

        #toggle maintenance mode button
        self.maintenanceMode = tk.BooleanVar(value=False)
        toggleMaintenance = ttk.Checkbutton(maintenance_frame, text="Toggle Maintenance", variable = self.maintenanceMode,command=self.Toggle_Maintenance_Mode)
        toggleMaintenance.pack(padx=WindowHeight/70, pady=WindowWidth/120)

        #switch selection dropdown
        ttk.Label(maintenance_frame, text="Select Switch").pack(padx=WindowHeight/70, pady=(WindowWidth/30,0))
        self.selectedSwitch = tk.StringVar()
        #switchOptions = self.WaysideInputs.get("switches",[])
        self.SwitchMenu = ttk.Combobox(maintenance_frame, textvariable=self.selectedSwitch, values=switchOptions, state="disabled")
        self.SwitchMenu.pack(padx=0, pady=0)

        #Switch state dictionary
        self.switchStatesDictionary = {switch: "BASE" for switch in switchOptions}#initialize all switches to "BASE"


        #display current switch state
        self.switchStateLabel = ttk.Label(maintenance_frame, text="Selected Switch State: N/A")
        self.switchStateLabel.pack(padx=WindowHeight/70, pady=(0,WindowWidth/120))
        self.SwitchMenu.bind("<<ComboboxSelected>>", self.Update_Switch_State)

        #select State label
        self.selectStateLabel = ttk.Label(maintenance_frame, text="Select Desired State")
        self.selectStateLabel.pack(padx=WindowHeight/70, pady=(WindowWidth/30,0))
        #select State combobox
        self.selectState = tk.StringVar()
        self.selectStateMenu = ttk.Combobox(maintenance_frame, textvariable=self.selectState, values=["BASE", "ALT"], state="disabled")
        self.selectStateMenu.pack(padx=0, pady=(WindowWidth/120,0))

        #apply Change
        self.applyChangeButton = ttk.Button(maintenance_frame, text="Apply Change", command=self.Apply_Switch_Change, state="disabled")
        self.applyChangeButton.pack(padx=WindowHeight/70, pady=WindowWidth/120)
        #------End Maintenance Frame------#

        #------Start Input Frame------#
        InputFrame = ttk.LabelFrame(self, text="Input Data:")
        InputFrame.grid(row=0, column=1, sticky="NSEW", padx=WindowHeight/70, pady=WindowWidth/120)

        #label and display for suggested speed
        self.suggestedSpeedLabel = ttk.Label(InputFrame, text="Suggested Speed: N/A")
        self.suggestedSpeedLabel.pack(padx=WindowHeight/70, pady=WindowWidth/120)

        #label and display for authority
        self.suggestedAuthorityLabel = ttk.Label(InputFrame, text="Suggested Authority: N/A")
        self.suggestedAuthorityLabel.pack(padx=WindowHeight/70, pady=WindowWidth/120)

        #label and display for commanded destination
        self.destinationLabel = ttk.Label(InputFrame, text="Destination: N/A")
        self.destinationLabel.pack(padx=WindowHeight/70, pady=WindowWidth/120)

        #label and dsplay for block occupancies
        self.blockOccupanciesLabel = ttk.Label(InputFrame, text="Block Occupancies: N/A")
        self.blockOccupanciesLabel.pack(padx=WindowHeight/70, pady=WindowWidth/120)

        #label and display for passengers disembarking
        # self.passengersDisembarkingLabel = ttk.Label(InputFrame, text="Passengers Disembarking: N/A")
        # self.passengersDisembarkingLabel.pack(padx=WindowHeight/70, pady=WindowWidth/120)
        #------End Input Frame------#

        #------Start Output Frame------#
        OutputFrame = ttk.LabelFrame(self, text="Output Data:")
        OutputFrame.grid(row=1, column=1, sticky="NSEW", padx=WindowHeight/70, pady=WindowWidth/120)

        #label and display for commanded speed
        self.commandedSpeedLabel = ttk.Label(OutputFrame, text="Commanded Speed: N/A")
        self.commandedSpeedLabel.pack(padx=WindowHeight/70, pady=WindowWidth/120)

        #label and display for commanded authority
        self.commandedAuthorityLabel = ttk.Label(OutputFrame, text="Commanded Authority: N/A")
        self.commandedAuthorityLabel.pack(padx=WindowHeight/70, pady=WindowWidth/120)

        #label and display for switch states
        self.switch_state_label = ttk.Label(OutputFrame, text="Switch States: N/A")
        self.switch_state_label.pack(padx=WindowHeight/70, pady=WindowWidth/120)

        #label and display for gate states
        self.gate_state_label = ttk.Label(OutputFrame, text="Gate States: N/A")
        self.gate_state_label.pack(padx=WindowHeight/70, pady=WindowWidth/120)

        #label and display for light states
        self.light_state_label = ttk.Label(OutputFrame, text="Light States: N/A")
        self.light_state_label.pack(padx=WindowHeight/70, pady=WindowWidth/120)



        #label and display for passengers disembarking
        # self.commandedPassengersDisembarkingLabel = ttk.Label(OutputFrame, text="Passengers Disembarking: N/A")
        # self.commandedPassengersDisembarkingLabel.pack(padx=WindowHeight/70, pady=WindowWidth/120)

        #------End Output Frame------#

        #------ Start PLC Upload Frame------#
        UploadFrame = ttk.LabelFrame(self, text="Upload PLC File - Maintenance Mode Necessary:")
        UploadFrame.grid(row=1, column=0, sticky="NSEW", padx=WindowHeight/70, pady=WindowWidth/120)

        self.file_select_label = ttk.Label(UploadFrame, text="Select PLC File:")
        self.file_select_label.pack(padx=WindowHeight/70, pady=(WindowWidth/30,0))

        self.file_path_var = tk.StringVar(value="test_plc.json")

        self.file_path_button = ttk.Button(UploadFrame, text="Browse", command=self.browse_file,state="disabled")
        self.file_path_button.pack(padx=WindowHeight/70, pady=(0,WindowWidth/120))

        self.plc_file_label = ttk.Label(UploadFrame, text="test_plc.json selected")
        self.plc_file_label.pack(padx=WindowHeight/70, pady=WindowWidth/120)
        #------End PLC Upload Frame------#
        
        #---Start Map Frame---#
        MapFrame = ttk.LabelFrame(self, text="Track Map:")
        MapFrame.grid(row=0, column=2, sticky="NSEW", padx=WindowHeight/70, pady=WindowWidth/120)
        #---End Map Frame---#

        #---Start Status Frame---#
        StatusFrame = ttk.LabelFrame(self, text="Status:")
        StatusFrame.grid(row=1, column=2, sticky="NSEW", padx=WindowHeight/70, pady=WindowWidth/120)
        #---End Status Frame---#

        # Initialize file modification time tracking
        self.last_mod_time = 0
        
        self.Load_Inputs_Outputs()#load wayside inputs from JSON file



#----Maintenance Mode Functions----#
        #only let everything in maintenance frame be editable if maintenance mode is on
    def Toggle_Maintenance_Mode(self):

       
        widgets = [self.SwitchMenu, self.selectStateMenu, self.applyChangeButton, self.file_path_button]
        if self.maintenanceMode.get():
            s="readonly"
        else:
            s="disabled"
        for widget in widgets:
            widget.config(state=s)

    #apply switch change to dictionary and update label
    def Apply_Switch_Change(self):
        switch = self.selectedSwitch.get()
        newState = self.selectState.get()
        if switch and newState:
            self.switchStatesDictionary[switch] = newState
            self.switchStateLabel.config(text="Selected Switch State: " + newState)


    #update switch state label when a new switch is selected
    def Update_Switch_State(self,event):
        switch = self.selectedSwitch.get()
        if switch in self.switchStatesDictionary:
            currentState = self.switchStatesDictionary[switch]
            self.switchStateLabel.config(text="Selected Switch State: " +currentState)
        else:
            self.switchStateLabel.config(text="Selected Switch State: N/A") 
#-------------------------------------#

#----Input/Outut Loading Function----#
    def Load_Inputs_Outputs(self):

        #load wayside inputs from JSON file
        if os.path.exists("WaysideInputsTestUISW.json"):
            with open("WaysideInputsTestUISW.json", "r") as file:
                waysideInputs = json.load(file)
        else:
            waysideInputs = {}


        #if not self.maintenanceMode.get(): #only update switch options and states if not in maintenance mode
            #get switch options
            #switchOptions = waysideInputs.get("switches",[])
            #self.SwitchMenu.config(values=switchOptions)
            #get switch states
            #switchStates = waysideInputs.get("switch_states",[])
            #update switch states dictionary with loaded states
            # for index in range(len(switchOptions)):
            #     switch = switchOptions[index]
            #     if index < len(switchStates):
            #         state = switchStates[index]
            #     else:
            #         state = "Straight"
            #     self.switchStatesDictionary[switch] = state

        #Get suggested speed
        suggestedSpeed = waysideInputs.get("suggested_speed",0)
        self.suggestedSpeedLabel.config(text="Suggested Speed: " + str(suggestedSpeed) + " mph")

        #Get suggested authority
        suggestedAuthority = waysideInputs.get("suggested_authority",0)
        self.suggestedAuthorityLabel.config(text="Suggested Authority: " + str(suggestedAuthority) + " yds")

        #Get destination
        destination = waysideInputs.get("destination",0)
        self.destinationLabel.config(text="Destination: " + str(destination))

        #Get block occupancies
        blockOccupancies = waysideInputs.get("block_occupancies",[])
        self.blockOccupanciesLabel.config(text="Block Occupancies: " + str(blockOccupancies))

        

        #Get passengers disembarking
        #passengersDisembarking = waysideInputs.get("passengers_disembarking",0)
        #self.passengersDisembarkingLabel.config(text="Passengers Disembarking: " + str(passengersDisembarking))

        # Minimal safe initializations to avoid NameError if PLC file or rules missing
        plc_rules = []
        commanded_speed = suggestedSpeed
        commanded_authority = suggestedAuthority        #Added by oliver to help with HW files, if it messes things up you can remove it

        #process plc file
        #if not self.maintenanceMode.get(): #only update outputs if not in maintenance mode
        wayside_outputs = plc_parser.parse_plc_data(self.file_path_var.get(), blockOccupancies, destination, suggestedSpeed, suggestedAuthority)
        switch_options = list("switch"+str(key) for key in wayside_outputs.get("switches",[]).keys())
        self.SwitchMenu.config(values=switch_options)

        #update switch states label
        switch_states = wayside_outputs.get("switches",{})
        switch_states_str = ", ".join(f"\n\tSwitch {key}: {value}" for key, value in switch_states.items())
        self.switch_state_label.config(text="Switch States: " + switch_states_str if switch_states_str else "Switch States: N/A")

        #update gate states label
        gate_states = wayside_outputs.get("crossings",{})
        gate_states_str = ", ".join(f"\n\tCrossing {key}: {value}" for key, value in gate_states.items())
        self.gate_state_label.config(text="Gate States: " + gate_states_str if gate_states_str else "Gate States: N/A")
                                     
        #update light states label
        light_states = wayside_outputs.get("lights",{})
        light_states_str = ", ".join(f"\n\tLight {key}: {value}" for key, value in light_states.items())
        self.light_state_label.config(text="Light States: " + light_states_str if light_states_str else "Light States: N/A")
        
        # Always write outputs when inputs change
        with open("WaysideOutputs_testUISW.json", "w") as file:
            json.dump(wayside_outputs, file, indent=4)

        #update output labels
        self.commandedSpeedLabel.config(text="Commanded Speed: " + str(wayside_outputs["commanded_speed"]) + " mph")
        self.commandedAuthorityLabel.config(text="Commanded Authority: " + str(wayside_outputs["commanded_authority"]) + " yds")
        #self.commandedPassengersDisembarkingLabel.config(text="Passengers Disembarking: " + str(waysideOutputs["passengers_disembarking"]))
            
        # Store the loaded inputs for next comparison
        self.WaysideInputs = waysideInputs

        self.after(500, self.Load_Inputs_Outputs)#reload inputs every 500ms
        #return waysideInputs

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if file_path:
            self.file_path_var.set(file_path)
            self.plc_file_label.config(text=os.path.basename(file_path) + " selected")
        else:
            self.file_path_var.set("test_plc.json")
            self.plc_file_label.config(text="test_plc.json selected")

#-------------------------------------#



if __name__ == "__main__":
    app = SWTrackControllerUI()
    app.mainloop()






