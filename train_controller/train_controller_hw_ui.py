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
        super().__init__()


        #set window title and size
        self.title("Hardware Driver Interface")
        self.geometry(f"{window_width}x{window_height}")
        self.minsize(900, 600)

        #top frame which displays and allows selections of train
        train_selection_frame = ttk.Frame(self)
        train_selection_frame.pack(fill="x", padx=10, pady=(8, 2))

        ttk.Label(train_selection_frame, font=(12), text="Select Train:").pack(side="left")
        self.train_var = tk.StringVar()
        self.train_combobox = ttk.Combobox(train_selection_frame,
                                           textvariable=self.train_var,
                                           state="readonly",
                                           width=18,
                                           values=["Train 1", "Train 2", "Train 3", "Train 4", "Train 5"])        
        self.train_combobox.current(0)
        self.train_combobox.pack(side="left", padx=5)

        #main frame which shows important train information panel
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=6)

        info_panel_frame = ttk.LabelFrame(main_frame, text="Train Information Panel", padding=(8,8))
        info_panel_frame.pack(fill="both", expand=True, padx=(0,8))

        columns = ("parameter", "value")
        self.info_treeview = ttk.Treeview(info_panel_frame, columns=columns, show="headings")
        self.info_treeview.heading("parameter", text="Parameter")
        self.info_treeview.heading("value", text="Value")
        self.info_treeview.column("parameter", anchor="w", width=300)
        self.info_treeview.column("value", anchor="center", width=150)
        self.info_treeview.pack(fill="both", expand=True)

        self.important_parameters = [
            ("Commanded Speed", "25 mph"),
            ("Commanded Authority", "21 yards"),
            ("Speed Limit", "30 mph"),
            ("Power Availability", "1000 kW"),
            ("Station Side", "Left/Right"),
            ("Cabin Temperature", "67 F"),
        ]
        for param, val in self.important_parameters:
            self.info_treeview.insert("", "end", values=(param, val))

        #bottom left frame with status indicators
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill="x", padx=10, pady=(0,10))

        status_frame = ttk.Frame(bottom_frame)
        status_frame.pack(side="left", fill="both", expand=True)

        self.status_buttons = {}
        statuses = ["Lights", "Left Door", "Right Door", "Horn", "Announcement", "Emergency Brake"]

        button_frame = ttk.Frame(status_frame)
        button_frame.pack(fill="x", padx=4, pady=6)

        for idx, status in enumerate(statuses):
            r = idx // 3
            c = idx % 3
            b = tk.Button(button_frame, text=status, width=22, height=3, 
                           bg="#f0f0f0", command=lambda s=status: self.toggle_status(s))
            b.grid(row=r, column=c, padx=10, pady=8, sticky="nsew")
            button_frame.grid_columnconfigure(c, weight=1)
            self.status_buttons[status] = {"button": b, "active": False}

        #bottom right frame engineering panel
        engineering_frame = ttk.LabelFrame(bottom_frame, text="Engineering Panel", padding=(8,8))
        engineering_frame.pack(side="right", fill="y", ipadx=6)

        ttk.Label(engineering_frame, text="Kp:").grid(row=0, column=0, sticky="w", pady=(2,6))
        self.kp_var = tk.StringVar(value="0.5")
        self.kp_entry = ttk.Entry(engineering_frame, textvariable=self.kp_var, width=20)
        self.kp_entry.grid(row=0, column=1, pady=(2,6))

        ttk.Label(engineering_frame, text="Ki:").grid(row=1, column=0, sticky="w", pady=(2,6))
        self.ki_var = tk.StringVar(value="0.1")
        self.ki_entry = ttk.Entry(engineering_frame, textvariable=self.ki_var, width=20)
        self.ki_entry.grid(row=1, column=1, pady=(2,6))

        # setting apply button to only be applied once
        self.apply_button = ttk.Button(engineering_frame, text="Apply", command=self.apply_gain)
        self.apply_button.grid(row=2, column=0, columnspan=2, pady=(8,2), sticky="ew")

        # make layout responsive
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def on_train_change(self, event):
        selected_train = self.train_var.get()
        new_values = {
            "Train 1": "25 mph",
            "Train 2": "20 mph",
            "Train 3": "30 mph",
        }
        children = self.info_treeview.get_children()
        for iid in children:
            param = self.info_treeview.item(iid)["values"][0]
            if param == "Commanded Speed":
                self.info_treeview.set(iid, "value", new_values.get(selected_train, "N/A"))

    def toggle_status(self, status):
        entry = self.status_buttons[status]
        entry["active"] = not entry["active"]
        button = entry["button"]
        if entry["active"]:
            button.config(bg="red", fg="white")
        else:
            button.config(bg="#f0f0f0", fg="black")

    def apply_gain(self):
        try:
            kp = float(self.kp_var.get())
            ki = float(self.ki_var.get())
            messagebox.showinfo("Gains Applied", f"Gains set to:\nKp: {kp}\nKi: {ki}")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric values for Kp and Ki.")

if __name__ == "__main__":
    app = hw_train_controller_ui()
    app.mainloop()
# THINGS THAT I SHOULD DISPLAY ON THE DRIVE UI FOR HARDWARE:
# THE SPEEDOMETER, THE INFORMATION PANNEL

# THINGS THAT MY HARDWARE SHOULD CONTROL ON THE DRIVER UI (LED CAN BE SHOWN ON THE UI, SO INCLUDE THE BUTTONS THERE):
# ALL BUTTONS, THE SPEED INPUT, THE TEMP INPUT, AND SERVICE BRAKE INPUT