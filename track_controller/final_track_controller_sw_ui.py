
#final_track_controller_sw_ui.py
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
try:
    from zoneinfo import ZoneInfo
    EASTERN = ZoneInfo("America/New_York")
except Exception:
    EASTERN = None
#import plc_parser
WIN_WIDTH = 1500
WIN_HEIGHT = 800

class sw_track_controller_ui(tk.Tk):
    """User interface for the Wayside Track Controller.

	Provides frames for maintenance, input/output data, PLC file upload,
	track map, and status updates. Periodically refreshes inputs and outputs
	from JSON files and PLC logic.
	"""
    def __init__(self,master=None):
        if master is None:
            super().__init__()
        else:
            super().__init__()
            self.master = master

        self.title("Track Controller Software Module")
        self.geometry(f"{WIN_WIDTH}x{WIN_HEIGHT}")

        #variables
        self.file_path_var = tk.StringVar(value="blue_line_config.json")
        self.maintenance_mode = tk.BooleanVar(value=False)
        self.selected_switch = tk.StringVar()
        self.select_state = tk.StringVar()
        self.selected_block = tk.StringVar()
        self.switch_options = []
        self.state_options = []

        
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

        self.update_clock()
        self.after(200, self.load_inputs_outputs())


    




    def load_inputs_outputs(self):
        style = ttk.Style()
        style.configure("grid.TLabel", font=("Arial", 8), background="white")
        style.configure("grid.TCheckbutton", font=("Arial", 8), background="white")
        blocks = 20

        # Clear current grid
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Create a variable to store the selected block number
        self.selected_block_number = tk.IntVar(value=-1)

        # Update grid with block information
        for block in range(blocks):
            def select_block(block=block):
                self.selected_block_number.set(block)
                self.show_selected_block()

            block_selection = ttk.Radiobutton(
            self.scrollable_frame,
            text=f"Block {block}",
            style="grid.TCheckbutton",
            variable=self.selected_block_number,
            value=block,
            command=select_block
            )
            block_gate = ttk.Label(self.scrollable_frame, text="Gate: N/A", style="grid.TLabel")
            block_signal = ttk.Label(self.scrollable_frame, text="Signal: N/A", style="grid.TLabel")
            block_switch = ttk.Label(self.scrollable_frame, text="Switch: N/A", style="grid.TLabel")
            block_occupancy = ttk.Label(self.scrollable_frame, text="Occupancy: N/A", style="grid.TLabel")
            block_failure = ttk.Label(self.scrollable_frame, text="Failure: N/A", style="grid.TLabel")

            block_selection.grid(row=block, column=0, padx=5, pady=5)
            block_gate.grid(row=block, column=1, padx=5, pady=5)
            block_signal.grid(row=block, column=2, padx=5, pady=5)
            block_switch.grid(row=block, column=3, padx=5, pady=5)
            block_occupancy.grid(row=block, column=4, padx=5, pady=5)
            block_failure.grid(row=block, column=5, padx=5, pady=5)

            

    def show_selected_block(self):
        selected = self.selected_block_number.get()
        if selected != -1:
            self.block_info_label.config(text=f"Selected Block Info: Block {selected}")
        else:
            self.block_info_label.config(text="Selected Block Info: None")

            

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
            variable=self.maintenance_mode,
            command=self.toggle_maintenance_mode,
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
            command=self.upload_plc_file,
            state="disabled",
            style="Maintenance.TButton"
        )
        self.upload_button.pack(pady=10)

        self.selected_file_str = tk.StringVar(value="N/A")

        self.selected_file_label = ttk.Label(self.maintenance_frame, text=f"currently selected file: {self.selected_file_str.get()}", style="display.TLabel", wraplength=200)
        self.selected_file_label.pack(pady=5)


        # Time display
        self.time_label = ttk.Label(self.maintenance_frame, style="Maintenance.TLabel",text=f"Time (EST): {self._get_est_time_str()}")
        self.time_label.pack(pady=(200,0))

    def build_input_frame(self):
        # Define a style for the input frame widgets
        style = ttk.Style()
        style.configure("Input.TLabel", font=("Arial", 16, "bold"), background="white")
        style.configure("smaller.TLabel", font=("Arial", 12), background="white")

        # Title label
        title_label = ttk.Label(self.input_frame, text="Input/Output Data", style="Input.TLabel")
        title_label.pack(pady=10)

        # Input/Output data display (placeholder)
        io_data_label = ttk.Label(self.input_frame, text="Input/Output data will be displayed here.", style="smaller.TLabel")
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

        

    

    def toggle_maintenance_mode(self):
        widgets = [self.switch_menu, self.state_menu, self.upload_button]

        if self.maintenance_mode.get():
            state = "readonly"
        else:
            state = "disabled"

        for widget in widgets:
            widget.config(state=state)

    def upload_plc_file(self):

            self.selected_file_label.config(text="Selected File: None")



    def update_clock(self):
        self.time_label.config(text=f"Time (EST): {self._get_est_time_str()}")
        # update every second
        self.after(1000, self.update_clock)

    def _get_est_time_str(self):
        now = datetime.now(timezone.utc)
        if EASTERN:
            try:
                now_est = now.astimezone(EASTERN)
            except Exception:
                now_est = now
        else:
            # best-effort fallback (local time)
            now_est = now.astimezone()
        # Format: MM/DD/YYYY h:mmAM/PM (no leading zeros on hour)
        return now_est.strftime("%m/%d/%Y %-I:%M:%S%p") if os.name != "nt" else now_est.strftime("%m/%d/%Y %#I:%M:%S%p")


#main to test setup 
if __name__ == "__main__":
    app = sw_track_controller_ui()
    app.mainloop()