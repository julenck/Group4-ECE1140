#Train Controller Hardware UI
#James Struyk


#import tkinter and related libraries
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import json
import os

#variables for window size
window_width = 1200
window_height = 700

class hw_train_controller_ui(tk.Tk):

    def __init__(self):
        super().__init__()#initialize the tk.Tk class


        #set window title and size
        self.title("Hardware Driver Interface")
        self.geometry(str(window_width)+"x"+str(window_height))


# THINGS THAT I SHOULD DISPLAY ON THE DRIVE UI FOR HARDWARE:
# THE SPEEDOMETER, THE INFORMATION PANNEL

# THINGS THAT MY HARDWARE SHOULD CONTROL ON THE DRIVER UI (LED CAN BE SHOWN ON THE UI, SO INCLUDE THE BUTTONS THERE):
# ALL BUTTONS, THE SPEED INPUT, THE TEMP INPUT, AND SERVICE BRAKE INPUT