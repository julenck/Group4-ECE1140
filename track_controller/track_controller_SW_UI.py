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
        ttk.Label(MaintenanceFrame, text="Select Switch").pack(padx=10, pady=10)
        self.selectedSwitch = tk.StringVar()
        switchOptions = ["SW1", "SW2", "SW3", "SW4", "SW5"]
        self.SwitchMenu = ttk.Combobox(MaintenanceFrame, textvariable=self.selectedSwitch, values=switchOptions, state="disabled")
        self.SwitchMenu.pack(padx=10, pady=10)

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

        



    def Toggle_Maintenance_Mode(self):

        #only let everything in maintenance frame be editable if maintenance mode is on
        widgets = [self.SwitchMenu]
        if self.maintenanceMode.get():
            s="readonly"
        else:
            s="disabled"
        for widget in widgets:
            widget.config(state=s)



if __name__ == "__main__":
    SWTrackControllerUI().mainloop()




