#Train Controller Software UI
#Julen Coca-Knorr


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

class sw_train_controller_ui(tk.Tk):

    def __init__(self):
        super().__init__()#initialize the tk.Tk class


        #set window title and size
        self.title("Driver Interface")
        self.geometry(str(window_width)+"x"+str(window_height))





if __name__ == "__main__":
    sw_train_controller_ui().mainloop()



