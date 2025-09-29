#Wayside Controller Software UI
#Connor Kariotis


#import tkinter and related libraries
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog

#variables for window size
WindowWidth = 1200
WindowHeight = 700

class SWTrackControllerUI(tk.Tk):

    def __init__(self):

        super().__init__()#initialize the tk.Tk class

        #set window title and size
        self.title("Track Controller Software Module")
        self.geometry(f"{WindowWidth}x{WindowHeight}")


        #configure grid layout

        for i in range(3):
            self.grid_columnconfigure(i, weight=1, uniform="col")
        for i in range(2):
            self.grid_rowconfigure(i, weight=1, uniform="row")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)


    #Maintenance Frame
        MaintenanceFrame = ttk.LabelFrame(self, text="Maintenance Mode:")
        MaintenanceFrame.grid(row=0, column=0, sticky="NSEW", padx=10, pady=10)

        #toggle maintenance mode button
        self.maintenanceMode = tk.BooleanVar(value=False)
        toggleMaintenance = ttk.Checkbutton(MaintenanceFrame, text="Toggle Maintenance", variable = self.maintenanceMode,command=self.Toggle_Maintenance_Mode)
        toggleMaintenance.pack(padx=10, pady=10)

        #switch selection dropdown
        ttk.Label(MaintenanceFrame, text="Select Switch").pack(padx=10, pady=(10,0))
        self.selectedSwitch = tk.StringVar()
        switchOptions = ["SW1", "SW2", "SW3", "SW4", "SW5"]
        self.SwitchMenu = ttk.Combobox(MaintenanceFrame, textvariable=self.selectedSwitch, values=switchOptions, state="disabled")
        self.SwitchMenu.pack(padx=0, pady=0)

        #Switch state dictionary
        self.switchStatesDictionary = {switch: "Straight" for switch in switchOptions}#initialize all switches to "Straight"


        #display current switch state
        self.switchStateLabel = ttk.Label(MaintenanceFrame, text="Selected Switch State: N/A")
        self.switchStateLabel.pack(padx=10, pady=10)
        self.SwitchMenu.bind("<<ComboboxSelected>>", self.Update_Switch_State)

        #select State
        self.selectState = tk.StringVar()
        self.selectStateMenu = ttk.Combobox(MaintenanceFrame, textvariable=self.selectState, values=["Straight", "Diverging"], state="disabled")
        self.selectStateMenu.pack(padx=0, pady=(40,0))

        #apply Change
        self.applyChangeButton = ttk.Button(MaintenanceFrame, text="Apply Change", command=self.Apply_Switch_Change, state="disabled")
        self.applyChangeButton.pack(padx=10, pady=10)

        

    #Input Frame
        InputFrame = ttk.LabelFrame(self, text="Input Data:")
        InputFrame.grid(row=0, column=1, sticky="NSEW", padx=10, pady=10)

    #Output Frame
        OutputFrame = ttk.LabelFrame(self, text="Output Data:")
        OutputFrame.grid(row=1, column=1, sticky="NSEW", padx=10, pady=10)

    #upload frame
        UploadFrame = ttk.LabelFrame(self, text="Upload PLC File:")
        UploadFrame.grid(row=0, column=2, sticky="NSEW", padx=10, pady=10)
    
    #Map Frame
        MapFrame = ttk.LabelFrame(self, text="Track Map:")
        MapFrame.grid(row=1, column=0, sticky="NSEW", padx=10, pady=10)
    
    #Status Frame
        StatusFrame = ttk.LabelFrame(self, text="Status:")
        StatusFrame.grid(row=1, column=2, sticky="NSEW", padx=10, pady=10)

        


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



if __name__ == "__main__":
    SWTrackControllerUI().mainloop()




