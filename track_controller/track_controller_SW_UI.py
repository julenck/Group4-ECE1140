#Wayside Controller Software UI
#Connor Kariotis


#import tkinter and related libraries
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import json
import os



#variables for window size
WindowWidth = 1200
WindowHeight = 700

class SWTrackControllerUI(tk.Tk):

    def __init__(self):

        super().__init__()#initialize the tk.Tk class

        #set window title and size
        self.title("Track Controller Software Module")
        self.geometry(f"{WindowWidth}x{WindowHeight}")

        #initialize loaded inputs
        switchOptions = []#default empty list of switches

        #configure grid layout
        for i in range(3):
            self.grid_columnconfigure(i, weight=1, uniform="col")
        for i in range(2):
            self.grid_rowconfigure(i, weight=1, uniform="row")

        #------Start Maintenance Frame------#
        MaintenanceFrame = ttk.LabelFrame(self, text="Maintenance Mode:")
        MaintenanceFrame.grid(row=0, column=0, sticky="NSEW", padx=WindowHeight/70, pady=WindowWidth/120)

        #toggle maintenance mode button
        self.maintenanceMode = tk.BooleanVar(value=False)
        toggleMaintenance = ttk.Checkbutton(MaintenanceFrame, text="Toggle Maintenance", variable = self.maintenanceMode,command=self.Toggle_Maintenance_Mode)
        toggleMaintenance.pack(padx=WindowHeight/70, pady=WindowWidth/120)

        #switch selection dropdown
        ttk.Label(MaintenanceFrame, text="Select Switch").pack(padx=WindowHeight/70, pady=(WindowWidth/30,0))
        self.selectedSwitch = tk.StringVar()
        #switchOptions = self.WaysideInputs.get("switches",[])
        self.SwitchMenu = ttk.Combobox(MaintenanceFrame, textvariable=self.selectedSwitch, values=switchOptions, state="disabled")
        self.SwitchMenu.pack(padx=0, pady=0)

        #Switch state dictionary
        self.switchStatesDictionary = {switch: "Straight" for switch in switchOptions}#initialize all switches to "Straight"


        #display current switch state
        self.switchStateLabel = ttk.Label(MaintenanceFrame, text="Selected Switch State: N/A")
        self.switchStateLabel.pack(padx=WindowHeight/70, pady=(0,WindowWidth/120))
        self.SwitchMenu.bind("<<ComboboxSelected>>", self.Update_Switch_State)

        #select State label
        self.selectStateLabel = ttk.Label(MaintenanceFrame, text="Select Desired State")
        self.selectStateLabel.pack(padx=WindowHeight/70, pady=(WindowWidth/30,0))
        #select State combobox
        self.selectState = tk.StringVar()
        self.selectStateMenu = ttk.Combobox(MaintenanceFrame, textvariable=self.selectState, values=["Straight", "Diverging"], state="disabled")
        self.selectStateMenu.pack(padx=0, pady=(WindowWidth/120,0))

        #apply Change
        self.applyChangeButton = ttk.Button(MaintenanceFrame, text="Apply Change", command=self.Apply_Switch_Change, state="disabled")
        self.applyChangeButton.pack(padx=WindowHeight/70, pady=WindowWidth/120)
        #------End Maintenance Frame------#

        #------Start Input Frame------#
        InputFrame = ttk.LabelFrame(self, text="Input Data:")
        InputFrame.grid(row=0, column=1, sticky="NSEW", padx=WindowHeight/70, pady=WindowWidth/120)
        #------End Input Frame------#

        #------Start Output Frame------#
        OutputFrame = ttk.LabelFrame(self, text="Output Data:")
        OutputFrame.grid(row=1, column=1, sticky="NSEW", padx=WindowHeight/70, pady=WindowWidth/120)
        #------End Output Frame------#

        #------ Start PLC Upload Frame------#
        UploadFrame = ttk.LabelFrame(self, text="Upload PLC File:")
        UploadFrame.grid(row=0, column=2, sticky="NSEW", padx=WindowHeight/70, pady=WindowWidth/120)
        #------End PLC Upload Frame------#
        
        #---Start Map Frame---#
        MapFrame = ttk.LabelFrame(self, text="Track Map:")
        MapFrame.grid(row=1, column=0, sticky="NSEW", padx=WindowHeight/70, pady=WindowWidth/120)
        #---End Map Frame---#

        #---Start Status Frame---#
        StatusFrame = ttk.LabelFrame(self, text="Status:")
        StatusFrame.grid(row=1, column=2, sticky="NSEW", padx=WindowHeight/70, pady=WindowWidth/120)
        #---End Status Frame---#

        self.WaysideInputs = self.Load_inputs()#load wayside inputs from JSON file



#----Maintenance Mode Functions----#
        #only let everything in maintenance frame be editable if maintenance mode is on
    def Toggle_Maintenance_Mode(self):

       
        widgets = [self.SwitchMenu, self.selectStateMenu, self.applyChangeButton]
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

#----Input Loading Function----#
    def Load_inputs(self):

        #load wayside inputs from JSON file
        if os.path.exists("WaysideInputs_testUI.json"):
            with open("WaysideInputs_testUI.json", "r") as file:
                waysideInputs = json.load(file)
        else:
            waysideInputs = {}

        #get switch options
        switchOptions = waysideInputs.get("switches",[])
        self.SwitchMenu.config(values=switchOptions)
        #update switch states dictionary to include any new switches, defaulting to "Straight"
        for switch in switchOptions:
            if switch not in self.switchStatesDictionary:
                self.switchStatesDictionary[switch] = "Straight"





        self.after(500, self.Load_inputs)#reload inputs every 500ms
#-------------------------------------#





if __name__ == "__main__":
    SWTrackControllerUI().mainloop()




