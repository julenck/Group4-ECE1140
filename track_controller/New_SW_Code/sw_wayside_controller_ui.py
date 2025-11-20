


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
#from .Green_Line_PLC_XandLup import process_states_green_xlup
#from .Green_Line_PLC_XandLdown import process_states_green_xldown
from track_controller.New_SW_Code import sw_wayside_controller
from track_controller.New_SW_Code import sw_vital_check



class sw_wayside_controller_ui(tk.Tk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    

    # Attributes
        self.toggle_maintenance_mode: tk.BooleanVar = tk.BooleanVar(value=False)
        self.selected_block: int = -1
        self.selected_block_data: dict = {}
        self.maintenance_frame: ttk.Frame = None
        self.input_frame: ttk.Frame = None
        self.all_blocks_frame: ttk.Frame = None
        self.map_frame: ttk.Frame = None
        self.selected_block_frame: ttk.Frame = None
        self.scrollable_frame: ttk.Frame = None
        self.blocks_with_switches: list = [13,28,57,63,77,85]
        self.blocks_with_lights: list = [0,3,7,29,58,62,76,86,100,101,150,151]
        self.blocks_with_gates: list = [19,108]

        self.block_labels: dict = {}


        #epty options for now
        self.switch_options: list = []
        self.state_options: list = []
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

        self.start_plc: str = controller.get_start_plc()
        self.selected_file_str = tk.StringVar(value="N/A")
        self.selected_file_str.set(self.start_plc)

        self.train_data_labels: dict = {}

        self.build_maintenance_frame()
        self.build_input_frame()
        self.build_all_blocks_frame()
        self.build_map_frame()
        self.build_selected_block_frame()

        self.update_block_labels()
    

    def on_close(self):
         # Stop the PLC loop and all background timers
        if hasattr(self, "controller") and self.controller is not None:
            self.controller.stop()

        # Destroy the UI window cleanly
        self.destroy()

        # End Tkinter’s mainloop completely if no other windows remain
        if not any(isinstance(w, tk.Tk) and w.winfo_exists() for w in tk._default_root.children.values()):
            self.quit()

    

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
        file = self.controller.load_plc(filename)

        self.update_selected_file(file)

    def send_inputs(self, data: dict):
        #self.controller.load_inputs()
        pass

    def send_outputs(self, data: dict):
        pass

    def update_selected_file(self, filename: str):
        self.selected_file_str.set(filename)
        self.selected_file_label.config(text=f"currently selected file: {os.path.basename(self.selected_file_str.get())}")
        self.build_all_blocks_frame()

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

        

        self.selected_file_label = ttk.Label(self.maintenance_frame, text=f"currently selected file: {self.selected_file_str.get()}", style="display.TLabel", wraplength=200)
        self.selected_file_label.pack(pady=5)

    def build_input_frame(self):
        # Define a style for the input frame widgets
        style = ttk.Style()
        style.configure("Input.TLabel", font=("Arial", 16, "bold"), background="white")
        style.configure("smaller.TLabel", font=("Arial", 5), background="gray")

        # Title label
        title_label = ttk.Label(self.input_frame, text="Active Train Data", style="Input.TLabel")
        title_label.pack(pady=10)

        # #sub frame for train data
        # self.train_data_frame = ttk.Frame(self.input_frame)
        # self.train_data_frame.pack(fill="both", expand=True, padx=10, pady=10)
        # #read in cmd train data from controller
        # train_data = self.controller.get_active_trains()
        # if train_data == {}:
        #     no_train_label = ttk.Label(self.train_data_frame, text="No active trains", style="smaller.TLabel")
        #     no_train_label.pack(pady=10)
        # else:
        #     i=0
        #     for train in train_data:
        #     #if on first wayside
        #         if self.selected_file_str.get() == "Green_Line_PLC_XandLup.py":
        #             if train_data[train]["pos"] <= 73 or train_data[train]["pos"] >= 144:
        #                 train_label = ttk.Label(self.train_data_frame, text=f"Train {train}:", style="smaller.TLabel")
        #                 train_label.grid(row=int(train[-1])-1, column=0, padx=5, pady=5, sticky="w")
        #                 speed_label = ttk.Label(self.train_data_frame, text=f"  Commanded Speed: {train_data[train]['cmd speed']} m/s", style="smaller.TLabel")
        #                 speed_label.grid(row=int(train[-1])-1, column=1, padx=5, pady=5, sticky="w")
        #                 auth_label = ttk.Label(self.train_data_frame, text=f"  Commanded Authority: {train_data[train]['cmd auth']} m", style="smaller.TLabel" )
        #                 auth_label.grid(row=int(train[-1])-1, column=2, padx=5, pady=5, sticky="w")
        #                 pos_label = ttk.Label(self.train_data_frame, text=f"  Position: {train_data[train]['pos']}", style="smaller.TLabel")
        #                 pos_label.grid(row=int(train[-1])-1, column=3, padx=5, pady=5, sticky="w")

        #         self.train_data_labels[i] = {
        #                             "train": train_label,
        #                             "speed": speed_label,
        #                             "auth": auth_label,
        #                             "pos": pos_label
        #                         }
        #         i+=1      
        #self.update_train_data_labels()
            

        

    def build_all_blocks_frame(self):
        #clear frame first
        for widget in self.all_blocks_frame.winfo_children():
            widget.destroy()
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


        def on_scroll(event):
            event.widget.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_scroll)

        #message for start because no plc file loaded
        if self.selected_file_str.get() == "N/A":
            no_file_label = ttk.Label(self.scrollable_frame, text="No PLC file loaded", style="smaller.TLabel")
            no_file_label.grid(row=0, column=0, padx=10, pady=10)

        else:

            #grid headers:
            ttk.Label(self.scrollable_frame, text="Block", style="smaller.TLabel").grid(row=0, column=1, padx=5, pady=5)
            ttk.Label(self.scrollable_frame, text="Occupied", style="smaller.TLabel").grid(row=0, column=2, padx=5, pady=5)
            ttk.Label(self.scrollable_frame, text="Switch", style="smaller.TLabel").grid(row=0, column=3, padx=5, pady=5)
            ttk.Label(self.scrollable_frame, text="Light", style="smaller.TLabel").grid(row=0, column=4, padx=5, pady=5)
            ttk.Label(self.scrollable_frame, text="Gate", style="smaller.TLabel").grid(row=0, column=5, padx=5, pady=5)
            ttk.Label(self.scrollable_frame, text="Failure", style="smaller.TLabel").grid(row=0, column=6, padx=5, pady=5)

            if (os.path.basename(self.selected_file_str.get()) == "Green_Line_PLC_XandLup.py"):
                #build grid for 80 blocks
                #self.block_vars = {}

                #block for Enter track from yard
                check_box = ttk.Checkbutton(self.scrollable_frame,
                                            variable=self.selected_block,
                                            onvalue=152,
                                            offvalue=-1,
                                            command=lambda idx=152: self.on_block_selected(idx))

                check_box.grid(row=1, column=0, padx=5, pady=5)
                block_label = ttk.Label(
                    self.scrollable_frame,
                    text="Leave Yard",
                    style="smaller.TLabel"
                )
                block_label.grid(row=1, column=1, padx=5, pady=5)
                #get yard data
                desired = self.controller.get_block_data(0)
                occupied_label = ttk.Label(self.scrollable_frame, text=f"{desired["occupied"]}", style="smaller.TLabel")
                occupied_label.grid(row=1, column=2, padx=5, pady=5)
                switch_label = ttk.Label(self.scrollable_frame, text=f"{desired["switch_state"]}", style="smaller.TLabel")
                switch_label.grid(row=1, column=3, padx=5, pady=5)
                light_label = ttk.Label(self.scrollable_frame, text=f"{desired["light_state"]}", style="smaller.TLabel")
                light_label.grid(row=1, column=4, padx=5, pady=5)
                gate_label = ttk.Label(self.scrollable_frame, text=f"{desired["gate_state"]}", style="smaller.TLabel")
                gate_label.grid(row=1, column=5, padx=5, pady=5)
                failure_label = ttk.Label(self.scrollable_frame, text=f"{desired["Failure"]}", style="smaller.TLabel")
                failure_label.grid(row=1, column=6, padx=5, pady=5)


                self.block_labels[0] = {
                    "occupied": occupied_label,
                    "switch": switch_label,
                    "light": light_label,
                    "gate": gate_label,
                    "failure": failure_label
                }
                for i in range(80):

                    
                    #self.block_vars[i] = check_box


                    if i <73:
                        block_num = i + 1
                    else:
                        block_num = i + 71
                    section_letter = self.get_section_letter(block_num)

                    check_box = ttk.Checkbutton(self.scrollable_frame,
                                                variable=self.selected_block, 
                                                onvalue=i,
                                                offvalue=-1,
                                                command=lambda idx=i: self.on_block_selected(idx))

                    block_label = ttk.Label(
                        self.scrollable_frame,
                        text=f"{section_letter}{block_num}",
                        style="smaller.TLabel"
                    )

                    check_box.grid(row=i+2, column=0, padx=5, pady=5)
                    block_label.grid(row=i + 2, column=1, padx=5, pady=5)

                    desired = self.controller.get_block_data(block_num)
                    occupied_label = ttk.Label(self.scrollable_frame, text=f"{desired["occupied"]}", style="smaller.TLabel")
                    occupied_label.grid(row=i+2, column=2, padx=5, pady=5)  
                    switch_label = ttk.Label(self.scrollable_frame, text=f"{desired["switch_state"]}", style="smaller.TLabel")
                    switch_label.grid(row=i+2, column=3, padx=5, pady= 5)
                    light_label = ttk.Label(self.scrollable_frame, text=f"{desired["light_state"]}", style="smaller.TLabel")
                    light_label.grid(row=i+2, column=4, padx=5, pady=5)
                    gate_label = ttk.Label(self.scrollable_frame, text=f"{desired["gate_state"] }", style="smaller.TLabel")
                    gate_label.grid(row=i+2, column=5, padx=5, pady=5)
                    failure_label = ttk.Label(self.scrollable_frame, text=f"{desired["Failure"]}", style="smaller.TLabel")  
                    failure_label.grid(row=i+2, column=6, padx=5, pady=5)

                    self.block_labels[block_num] = {
                        "occupied": occupied_label,
                        "switch": switch_label,
                        "light": light_label,
                        "gate": gate_label,
                        "failure": failure_label
                    }
                
                    #block for Enter yard from track
                check_box = ttk.Checkbutton(self.scrollable_frame,
                                            variable=self.selected_block,
                                            onvalue=151,
                                            offvalue=-1,
                                            command=lambda idx=151: self.on_block_selected(idx))
                check_box.grid(row=82, column=0, padx=5, pady=5)
                block_label = ttk.Label(
                    self.scrollable_frame,
                    text="Enter Yard",
                    style="smaller.TLabel"
                )
                block_label.grid(row=82, column=1, padx=5, pady=5)

                desired = self.controller.get_block_data(151)
                occupied_label = ttk.Label(self.scrollable_frame, text=f"{desired["occupied"]}", style="smaller.TLabel")
                occupied_label.grid(row=82, column=2, padx=5, pady=5)
                switch_label = ttk.Label(self.scrollable_frame, text=f"{desired["switch_state"]}", style="smaller.TLabel")
                switch_label.grid(row=82, column=3, padx=5, pady=5)
                light_label = ttk.Label(self.scrollable_frame, text=f"{desired["light_state"]}", style="smaller.TLabel")
                light_label.grid(row=82, column=4, padx=5, pady=5)
                gate_label = ttk.Label(self.scrollable_frame, text=f"{desired["gate_state"]}", style="smaller.TLabel")
                gate_label.grid(row=82, column=5, padx=5, pady=5)
                failure_label = ttk.Label(self.scrollable_frame, text=f"{desired["Failure"]}", style="smaller.TLabel")
                failure_label.grid(row=82, column=6, padx=5, pady=5)

                self.block_labels[151] = {
                    "occupied": occupied_label,
                    "switch": switch_label,
                    "light": light_label,
                    "gate": gate_label,
                    "failure": failure_label
                }
            
            elif (os.path.basename(self.selected_file_str.get()) == "Green_Line_PLC_XandLdown.py"):
                #build for 77 blocks

                for i in range(77):
                    block_num = i + 70
                    section_letter = self.get_section_letter(block_num)
                    check_box = ttk.Checkbutton(self.scrollable_frame,
                                                variable=self.selected_block, 
                                                onvalue=i,
                                                offvalue=-1,
                                                command=lambda idx=i: self.on_block_selected(idx))
                    check_box.grid(row=i+1, column=0, padx=5, pady=5)

                    block_label = ttk.Label(
                        self.scrollable_frame,
                        text=f"{section_letter}{block_num}",
                        style="smaller.TLabel"
                    )
                    block_label.grid(row=i + 1, column=1, padx=5, pady=5)
                    desired = self.controller.get_block_data(block_num)
                    occupied_label = ttk.Label(self.scrollable_frame, text=f"{desired["occupied"]}", style="smaller.TLabel")
                    occupied_label.grid(row=i+1, column=2, padx=5, pady=5)  
                    switch_label = ttk.Label(self.scrollable_frame, text=f"{desired["switch_state"]}", style="smaller.TLabel")  
                    switch_label.grid(row=i+1, column=3, padx=5, pady= 5)
                    light_label = ttk.Label(self.scrollable_frame, text=f"{desired["light_state"]}", style="smaller.TLabel")
                    light_label.grid(row=i+1, column=4, padx=5, pady=5)
                    gate_label = ttk.Label(self.scrollable_frame, text=f"{desired["gate_state"] }", style="smaller.TLabel")
                    gate_label.grid(row=i+1, column=5, padx=5, pady=5)
                    failure_label = ttk.Label(self.scrollable_frame, text=f"{desired["Failure"]}", style="smaller.TLabel")  
                    failure_label.grid(row=i+1, column=6, padx=5, pady=5)

                    self.block_labels[block_num] = {
                        "occupied": occupied_label,
                        "switch": switch_label,
                        "light": light_label,
                        "gate": gate_label,
                        "failure": failure_label
                    }

    #def update_train_data_labels(self):
        #for train, labels in self.train_data_labels.items():
            #data = self.controller.get_active_trains().get(train, {})
            #if data!={}:  # Ensure data exists for the train
                #labels["speed"].config(text=f"  Commanded Speed: {data.get('cmd speed', 'N/A')} m/s")
                #labels["auth"].config(text=f"  Commanded Authority: {data.get('cmd auth', 'N/A')} m")
                #labels["pos"].config(text=f"  Position: {data.get('pos', 'N/A')}")
            
        #self.after(200, self.update_train_data_labels)  # Update every second

    def update_block_labels(self):
        for block_id, labels in self.block_labels.items():
            data = self.controller.get_block_data(block_id)
            labels["occupied"].config(text=f"{data['occupied']}")
            labels["switch"].config(text=f"{data['switch_state']}")
            labels["light"].config(text=f"{data['light_state']}")
            labels["gate"].config(text=f"{data['gate_state']}")
            labels["failure"].config(text=f"{data['Failure']}")
        
        if self.selected_block != -1:
            self.build_selected_block_frame()

        self.after(200, self.update_block_labels)  # Update every second

    def on_block_selected(self, idx: int):
        # If user clicks the same checkbox again, deselect it
        if idx==0:
            self.selected_block = 0
        
        elif self.selected_block == idx:
            self.selected_block = -1
        else:
            self.selected_block = idx

        # Update the right-side info frame
        #self.build_selected_block_frame()
    
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
        #clear frame first
        for widget in self.selected_block_frame.winfo_children():
            widget.destroy()
        # Define a style for the selected block frame widgets
        style = ttk.Style()
        style.configure("SelectedBlock.TLabel", font=("Arial", 16, "bold"), background="white")
        style.configure("smaller.TLabel", font=("Arial", 12), background="white")

        # Title label
        title_label = ttk.Label(self.selected_block_frame, text="Selected Block Info", style="SelectedBlock.TLabel")
        title_label.pack(pady=10)

        # Selected block info display (placeholder)
        if self.selected_block == -1:
            self.block_info_label = ttk.Label(self.selected_block_frame, text="Selected block information will be displayed here.", style="smaller.TLabel")
            self.block_info_label.pack(pady=10)
        elif os.path.basename(self.selected_file_str.get()) == "Green_Line_PLC_XandLup.py":
            if self.selected_block <= 79:
                block = self.selected_block + 1 if self.selected_block < 73 else self.selected_block + 71
                sec = self.get_section_letter(block)
                self.selected_block_data = self.controller.get_block_data(block)  
            elif self.selected_block == 151:
                block=151
                self.selected_block_data = self.controller.get_block_data(block)
                
            elif self.selected_block == 152:
                block=0
                self.selected_block_data = self.controller.get_block_data(block)
            
            id = self.selected_block_data["block_id"]
            occupied = self.selected_block_data["occupied"]
            switch_state_enum = self.selected_block_data["switch_state"]
            light_state_enum = self.selected_block_data["light_state"]
            gate_state_enum = self.selected_block_data["gate_state"]
            failure_enum = self.selected_block_data["Failure"]

            switch_state, light_state, gate_state, failure = self.get_all_strings(switch_state_enum, light_state_enum, gate_state_enum, failure_enum,id)

            if self.selected_block <=79:
                id_label = ttk.Label(self.selected_block_frame, text=f"Block ID: {sec}{block}", style="smaller.TLabel")
            elif self.selected_block ==151:
                id_label = ttk.Label(self.selected_block_frame, text=f"Block ID: Enter Yard(151)", style="smaller.TLabel")
            elif self.selected_block ==152:
                id_label = ttk.Label(self.selected_block_frame, text=f"Block ID: Leave Yard(0)", style="smaller.TLabel")
            id_label.pack(pady=5)
            occupied_label = ttk.Label(self.selected_block_frame, text=f"Occupied: {occupied}", style="smaller.TLabel")
            occupied_label.pack(pady=5)
            switch_label = ttk.Label(self.selected_block_frame, text=f"Switch State: {switch_state}", style="smaller.TLabel")
            switch_label.pack(pady=5)
            light_label = ttk.Label(self.selected_block_frame, text=f"Light State: {light_state}", style="smaller.TLabel")
            light_label.pack(pady=5)
            gate_label = ttk.Label(self.selected_block_frame, text=f"Gate State: {gate_state}", style="smaller.TLabel")
            gate_label.pack(pady=5)
            failure_label = ttk.Label(self.selected_block_frame, text=f"Failure: {failure}", style="smaller.TLabel")
            failure_label.pack(pady=5)

        elif os.path.basename(self.selected_file_str.get()) == "Green_Line_PLC_XandLdown.py":
            block = self.selected_block + 70
            sec = self.get_section_letter(block)
            self.selected_block_data = self.controller.get_block_data(block)  

            id = block
            occupied = self.selected_block_data["occupied"]
            switch_state_enum = self.selected_block_data["switch_state"]
            light_state_enum = self.selected_block_data["light_state"]
            gate_state_enum = self.selected_block_data["gate_state"]
            failure_enum = self.selected_block_data["Failure"]

            switch_state, light_state, gate_state, failure = self.get_all_strings(switch_state_enum, light_state_enum, gate_state_enum, failure_enum,id)    

            id_label = ttk.Label(self.selected_block_frame, text=f"Block ID: {sec}{block}", style="smaller.TLabel")
            id_label.pack(pady=5)
            occupied_label = ttk.Label(self.selected_block_frame, text=f"Occupied: {occupied}", style="smaller.TLabel")
            occupied_label.pack(pady=5)
            switch_label = ttk.Label(self.selected_block_frame, text=f"Switch State: {switch_state}", style="smaller.TLabel")
            switch_label.pack(pady=5)
            light_label = ttk.Label(self.selected_block_frame, text=f"Light State: {light_state}", style="smaller.TLabel")
            light_label.pack(pady=5)
            gate_label = ttk.Label(self.selected_block_frame, text=f"Gate State: {gate_state}", style="smaller.TLabel")
            gate_label.pack(pady=5)
            failure_label = ttk.Label(self.selected_block_frame, text=f"Failure: {failure}", style="smaller.TLabel")
            failure_label.pack(pady=5)



                
    
    def toggle_maintenance(self):
        widgets = [self.switch_menu, self.state_menu, self.upload_button]

        if self.toggle_maintenance_mode.get():
            state = "readonly"
        else:
            state = "disabled"

        for widget in widgets:
            widget.config(state=state)

    def get_section_letter(self, block_num: int):
        block_num -= 1  # Adjust for 0-based index
        if block_num == 151:
            return 'Enter Yard'
        elif block_num == 152:
            return 'Leave Yard'
        if block_num < 3:
            return 'A'
        elif block_num < 6:
            return 'B'
        elif block_num < 12:
            return 'C'
        elif block_num < 16:
            return 'D'
        elif block_num < 20:
            return 'E'
        elif block_num < 28:
            return 'F'
        elif block_num < 32:
            return 'G'
        elif block_num < 35:
            return 'H'
        elif block_num < 57:
            return 'I'
        elif block_num < 62:
            return 'J'
        elif block_num < 68:
            return 'K'
        elif block_num < 73:
            return 'L'
        elif block_num < 76:
            return 'm'
        elif block_num < 85:
            return 'N'
        elif block_num < 88:
            return 'O'
        elif block_num < 97:
            return 'P'
        elif block_num < 100:
            return 'Q'
        elif block_num == 100:
            return 'R'
        elif block_num < 104:
            return 'S'
        elif block_num < 109:
            return 'T'
        elif block_num < 115:
            return 'U'
        elif block_num < 121:   
            return 'V'
        elif block_num < 143:
            return 'W'
        elif block_num < 146:
            return 'X'
        elif block_num < 149:
            return 'Y'  
        else:
            return 'Z'
    
    def get_all_strings(self,switch_state_enum, light_state_enum, gate_state_enum, failure_enum,id):

        if id in [13,28,57,63,77,85]:
            if id == 13 and switch_state_enum == 0:
                switch_state = "D13->A1"
            elif id == 13 and switch_state_enum == 1:
                switch_state = "D13->C12"
            elif id == 28 and switch_state_enum == 0:
                switch_state = "F28->G29"
            elif id == 28 and switch_state_enum == 1:
                switch_state = "F28->Z150"
            elif id == 57 and switch_state_enum == 0:
                switch_state = "I57->Yard"
            elif id == 57 and switch_state_enum == 1:
                switch_state = "I57->J58"
            elif id == 63 and switch_state_enum == 0:
                switch_state = "K63->J62"
            elif id == 63 and switch_state_enum == 1:
                switch_state = "K63-Yard"
            elif id == 77 and switch_state_enum == 0:
                switch_state = "N77->M76"
            elif id == 77 and switch_state_enum == 1:
                switch_state = "N77->R101"
            elif id == 85 and switch_state_enum == 0:
                switch_state = "N85->O86"
            elif id == 85 and switch_state_enum == 1:
                switch_state = "N85->Q100"
        else: 
            switch_state = "N/A"
        if id in [0,3,7,29,58,62,76,86,100,101,150,151]:
            #make sure is a string 
            
            
            if light_state_enum == "00":
                light_state = "Super Green"
            elif light_state_enum == "01":
                light_state = "Green"
            elif light_state_enum == "10":
                light_state = "Yellow"
            elif light_state_enum == "11":
                light_state = "Red"
        else:
            light_state = "N/A"
        #if id == 0:
            #light_state = "Green"
        if id in [19,108]:
            if gate_state_enum == 0:
                gate_state = "Down"
            elif gate_state_enum == 1:
                gate_state = "Up"
        else:
            gate_state = "N/A"
        if failure_enum == 0:
            failure = "No Failure"
        elif failure_enum == 1:
            failure = "Broken Track"
        elif failure_enum == 2:
            failure = "Power Failure"
        elif failure_enum == 3:
            failure = "Circuit Failure"
        
        return switch_state, light_state, gate_state, failure



def main():
    # Create first UI window (still a Tk)
    vital1 = sw_vital_check.sw_vital_check()
    controller1 = sw_wayside_controller.sw_wayside_controller(vital1, "Green_Line_PLC_XandLup.py")
    ui1 = sw_wayside_controller_ui(controller1)
    ui1.title("Wayside Controller 1")
    ui1.geometry("1200x800")

    # Create second UI window (another Tk)
    vital2 = sw_vital_check.sw_vital_check()
    controller2 = sw_wayside_controller.sw_wayside_controller(vital2, "Green_Line_PLC_XandLdown.py")
    #ui2 = sw_wayside_controller_ui(controller2)
    #ui2.title("Wayside Controller 2")
    #ui2.geometry("1200x800")

    # Bring both windows to front
    #ui1.lift()
    #ui2.lift()

    # Run *one* mainloop (both Tk windows share it)
    tk.mainloop()


if __name__ == "__main__":
    main()