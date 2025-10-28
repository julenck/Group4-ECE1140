


#Author: Connor Kariotis
#ECE 1140 - Wayside Controller Software
#Discription: UI for track controller maintenance and monitoring

"""Module for the Wayside Track Controller User Interface.

This module provides a Tkinter-based GUI for monitoring and maintaining
track switches, signals, gates, and train-related data. It allows users
to toggle maintenance mode, upload PLC files, and observe input/output
data in real time.
"""

#import tkinter and related libraries
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import json
import os
from datetime import datetime, timezone
from Green_Line_PLC_XandLup import process_states_green_xlup
import sw_wayside_controller
import sw_vital_check



class sw_wayside_controller_ui(tk.Tk):
    def __init__(self, controller):
        super().__init__()
    # Association
        self.controller = controller

    # Attributes
        self.toggle_maintenance_mode: bool = False
        self.selected_block: int = -1
        self.selected_block_data: dict = {}
        self.maintenance_frame: ttk.Frame = None
        self.input_frame: ttk.Frame = None
        self.all_blocks_frame: ttk.Frame = None
        self.map_frame: ttk.Frame = None
        self.selected_block_frame: ttk.Frame = None
        self.scrollable_frame: ttk.Frame = None

        #epty options for now
        self.switch_options: list = []
        self.state_options: list = ["0", "1"]
        self.selected_switch: tk.StringVar = tk.StringVar()


        # Configure grid layout
        self.columnconfigure(0, weight=1)  # Left column
        self.columnconfigure(1, weight=1)  # Middle column
        self.columnconfigure(2, weight=1)  # Right column
        self.rowconfigure(0, weight=1)  # Top row
        self.rowconfigure(1, weight=1)  # Bottom row

        # Add frames for each section
        # Define styles for the frames
        style = ttk.Style()
        style.configure("Maintenance.TFrame", background="lightgray")
        style.configure("Input.TFrame", background="white")
        style.configure("AllBlocks.TFrame", background="white")
        style.configure("Map.TFrame", background="white")
        style.configure("SelectedBlock.TFrame", background="white")

        # Create frames with ttk and apply styles
        self.maintenance_frame = ttk.Frame(self, style="Maintenance.TFrame")
        self.maintenance_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")

        self.input_frame = ttk.Frame(self, style="Input.TFrame")
        self.input_frame.grid(row=0, column=1, sticky="nsew")

        self.all_blocks_frame = ttk.Frame(self, style="AllBlocks.TFrame")
        self.all_blocks_frame.grid(row=1, column=1, sticky="nsew")

        self.map_frame = ttk.Frame(self, style="Map.TFrame")
        self.map_frame.grid(row=0, column=2, sticky="nsew")
        

        self.selected_block_frame = ttk.Frame(self, style="SelectedBlock.TFrame")
        self.selected_block_frame.grid(row=1, column=2, sticky="nsew")

        self.build_maintenance_frame()
        self.build_input_frame()
        self.build_all_blocks_frame()
        self.build_map_frame()
        self.build_selected_block_frame()

    

# Methods
    def set_light_state(self, block_id: int, state: int):
        self.controller.override_light(block_id, state)

    def set_gate_state(self, block_id: int, state: int):
        self.controller.override_gate(block_id, state)

    def set_switch_state(self, block_id: int, state: int):
        self.controller.override_switch(block_id, state)

    def set_plc(self):
        #ask for a python file
        filename = filedialog.askopenfilename(
            title="Select PLC File",
            filetypes=[("Python Files", "*.py"), ("All Files", "*.*")]
        )
        self.controller.load_plc(filename)

    def send_inputs(self, data: dict):
        #self.controller.load_inputs()
        pass

    def send_outputs(self, data: dict):
        pass

    def update_selected_file(self, filename: str):
        pass

    def select_block(self, block_id: int):
        #self.selected_block = block_id
        #self.selected_block_data = self.controller.get_block_data(block_id)
        pass

    def show_block_data(self, data: dict):
        pass

    def build_maintenance_frame(self):

        # Define a style for the maintenance frame widgets
        style = ttk.Style()
        style.configure("Maintenance.TLabel", font=("Arial", 16, "bold"), background="lightgray")
        style.configure("Maintenance.TCheckbutton", font=("Arial", 12, "bold"), background="lightgray")
        style.configure("display.TLabel", font=("Arial", 12), background="lightgray")

        # Title label
        title_label = ttk.Label(self.maintenance_frame, text="Maintenance", style="Maintenance.TLabel")
        title_label.pack(pady=10)

        # Toggle maintenance mode
        toggle_maintenance = ttk.Checkbutton(
            self.maintenance_frame,
            text="Toggle Maintenance",
            style="Maintenance.TCheckbutton",
            variable=self.toggle_maintenance_mode,
            command=self.toggle_maintenance,
        )
        toggle_maintenance.pack(pady=10)

        #switch selection
        switch_label = ttk.Label(self.maintenance_frame, text="Select Switch:", style="Maintenance.TLabel")
        switch_label.pack(pady=5)
        self.switch_menu = ttk.Combobox(
            self.maintenance_frame,
            textvariable=self.selected_switch,
            values=self.switch_options,
            state="disabled",
        )
        self.switch_menu.pack(pady=5)
        #show current state
        current_state_label = ttk.Label(self.maintenance_frame, text="Current Switch State: N/A", style="display.TLabel")
        current_state_label.pack(pady=(5,50))

        #switch state selection
        state_label = ttk.Label(self.maintenance_frame, text="Set Switch State:", style="Maintenance.TLabel")
        state_label.pack(pady=5)
        self.state_menu = ttk.Combobox(
            self.maintenance_frame,
            values=self.state_options,
            state="disabled",
        )
        self.state_menu.pack(pady=(5,80))

        #upload plc file

        plc_label = ttk.Label(self.maintenance_frame, text="Upload PLC File:", style="Maintenance.TLabel")
        plc_label.pack(pady=5)

        self.upload_button = ttk.Button(
            self.maintenance_frame,
            text="browse",
            command=self.set_plc,
            state="disabled",
            style="Maintenance.TButton"
        )
        self.upload_button.pack(pady=10)

        self.selected_file_str = tk.StringVar(value="N/A")

        self.selected_file_label = ttk.Label(self.maintenance_frame, text=f"currently selected file: {self.selected_file_str.get()}", style="display.TLabel", wraplength=200)
        self.selected_file_label.pack(pady=5)

    def build_input_frame(self):
        # Define a style for the input frame widgets
        style = ttk.Style()
        style.configure("Input.TLabel", font=("Arial", 16, "bold"), background="white")
        style.configure("smaller.TLabel", font=("Arial", 12), background="white")

        # Title label
        title_label = ttk.Label(self.input_frame, text="Active Train Data", style="Input.TLabel")
        title_label.pack(pady=10)

        # train data display (placeholder)
        io_data_label = ttk.Label(self.input_frame, text="Active train data will be displayed here.", style="smaller.TLabel")
        io_data_label.pack(pady=10)

    def build_all_blocks_frame(self):
        # Define a style for the all blocks frame widgets
        style = ttk.Style()
        style.configure("AllBlocks.TLabel", font=("Arial", 16, "bold"), background="white")
        style.configure("smaller.TLabel", font=("Arial", 12), background="white")

        # Title label
        title_label = ttk.Label(self.all_blocks_frame, text="All Blocks Status", style="AllBlocks.TLabel")
        title_label.pack(pady=10)

        #create grid to display all blocks
        container = ttk.Frame(self.all_blocks_frame)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, bg="white")
        scroller = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        #make scrollable frame self so it can be accessed later
        self.scrollable_frame = ttk.Frame(canvas, style = "smaller.TLabel")
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroller.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scroller.pack(side="right", fill="y")


        def on_scroll(self, event):
            event.widget.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_scroll)

        #message for start because no plc file loaded
        no_file_label = ttk.Label(self.scrollable_frame, text="No PLC file loaded", style="smaller.TLabel")
        no_file_label.grid(row=0, column=0, padx=10, pady=10)




        

    
    def build_map_frame(self):
        # Define a style for the map frame widgets
        style = ttk.Style()
        style.configure("Map.TLabel", font=("Arial", 16, "bold"), background="white")
        style.configure("smaller.TLabel", font=("Arial", 12), background="white")

        # Title label
        title_label = ttk.Label(self.map_frame, text="Track Map", style="Map.TLabel")
        title_label.pack(pady=10)

        # Track map display (placeholder)
        map_display_label = ttk.Label(self.map_frame, text="Track map will be displayed here.", style="smaller.TLabel")
        map_display_label.pack(pady=10)

        

    def build_selected_block_frame(self):
        # Define a style for the selected block frame widgets
        style = ttk.Style()
        style.configure("SelectedBlock.TLabel", font=("Arial", 16, "bold"), background="white")
        style.configure("smaller.TLabel", font=("Arial", 12), background="white")

        # Title label
        title_label = ttk.Label(self.selected_block_frame, text="Selected Block Info", style="SelectedBlock.TLabel")
        title_label.pack(pady=10)

        # Selected block info display (placeholder)
        self.block_info_label = ttk.Label(self.selected_block_frame, text="Selected block information will be displayed here.", style="smaller.TLabel")
        self.block_info_label.pack(pady=10)
    
    def toggle_maintenance(self):
        widgets = [self.switch_menu, self.state_menu, self.upload_button]

        if self.toggle_maintenance_mode.get():
            state = "readonly"
        else:
            state = "disabled"

        for widget in widgets:
            widget.config(state=state)

        

if __name__ == "__main__":


    vital = sw_vital_check.sw_vital_check()
    controller = sw_wayside_controller.sw_wayside_controller(vital)
    ui = sw_wayside_controller_ui(controller)
    #make it 1200x800
    ui.geometry("1200x800")
    ui.mainloop()