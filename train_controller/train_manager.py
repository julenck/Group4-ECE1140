"""Train Manager Module

This module manages multiple trains, where each train consists of:
- One TrainModel instance (physics simulation)
- One train_controller instance (control logic)

The TrainManager coordinates multiple trains, assigns unique IDs,
and manages their state in the shared train_states.json file.

Author: Julen Coca-Knorr
"""

import os
import sys
import json
import tkinter as tk
from tkinter import ttk

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
sys.path.append(parent_dir)

# Import TrainModel
train_model_dir = os.path.join(parent_dir, "Train Model")
sys.path.append(train_model_dir)

# Import required classes
from api.train_controller_api import train_controller_api


class TrainPair:
    """Represents a paired TrainModel and train_controller instance with UIs.
    
    Attributes:
        train_id: Unique identifier for this train.
        model: TrainModel instance for physics simulation.
        controller: train_controller instance for control logic.
        model_ui: TrainModelUI instance (UI window for train model).
        controller_ui: train_controller_ui instance (UI window for train controller).
    """
    
    def __init__(self, train_id: int, model, controller, model_ui=None, controller_ui=None):
        """Initialize a train pair.
        
        Args:
            train_id: Unique identifier for this train.
            model: TrainModel instance.
            controller: train_controller instance.
            model_ui: TrainModelUI instance (optional).
            controller_ui: train_controller_ui instance (optional).
        """
        self.train_id = train_id
        self.model = model
        self.controller = controller
        self.model_ui = model_ui
        self.controller_ui = controller_ui


class TrainManager:
    """Manages multiple trains (TrainModel + train_controller pairs).
    
    The TrainManager creates and coordinates multiple trains, each with its own
    TrainModel (physics) and train_controller (logic). Each train has a unique ID
    and its own section in the train_states.json file.
    
    Attributes:
        trains: Dictionary mapping train_id to TrainPair instances.
        next_train_id: Next available train ID.
        state_file: Path to the shared train_states.json file.
    """
    
    def __init__(self, state_file: str = None):
        """Initialize the TrainManager.
        
        Args:
            state_file: Path to train_states.json. If None, uses default location.
        """
        self.trains = {}  # Dictionary of train_id -> TrainPair
        self.next_train_id = 1
        
        # Set state file path
        if state_file is None:
            data_dir = os.path.join(current_dir, "data")
            self.state_file = os.path.join(data_dir, "train_states.json")
        else:
            self.state_file = state_file

        # Extra paths for train_data.json and track model inputs
        self.train_data_file = os.path.join(train_model_dir, "train_data.json")
        self.track_model_file = os.path.join(parent_dir, "Track_Model", "track_model_Train_Model.json")
        
        # Ensure state file exists
        self._initialize_state_file()
    
    def _initialize_state_file(self):
        """Initialize the train_states.json file if it doesn't exist."""
        if not os.path.exists(self.state_file):
            # Create empty state file
            with open(self.state_file, 'w') as f:
                json.dump({}, f, indent=4)
    
    def add_train(self, train_specs: dict = None, create_uis: bool = True, use_hardware: bool = False) -> int:
        """Add a new train (TrainModel + train_controller pair with UIs).
        
        Creates a new TrainModel and train_controller instance, assigns a unique ID,
        and initializes their state in the train_states.json file. Optionally creates
        UI windows for both the Train Model and Train Controller.
        
        Args:
            train_specs: Dictionary of train specifications for TrainModel.
                        If None, uses default specifications.
            create_uis: If True, creates UI windows for this train (default: True).
            use_hardware: If True, uses hardware controller UI instead of software (default: False).
        
        Returns:
            The train_id of the newly created train.
        """
        # Import TrainModel and TrainModelUI
        try:
            from train_model_ui import TrainModel, TrainModelUI
        except ImportError:
            # Try alternate import path
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "train_model_ui",
                os.path.join(train_model_dir, "train_model_ui.py")
            )
            train_model_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(train_model_module)
            TrainModel = train_model_module.TrainModel
            TrainModelUI = train_model_module.TrainModelUI
        
        # Import appropriate controller based on hardware flag
        if use_hardware:
            from ui.train_controller_hw_ui import train_controller, train_controller_ui
            print(f"Using HARDWARE controller for train {self.next_train_id}")
        else:
            from ui.train_controller_sw_ui import train_controller, train_controller_ui
            print(f"Using SOFTWARE controller for train {self.next_train_id}")
        
        # Get train ID
        train_id = self.next_train_id
        self.next_train_id += 1
        
        # Default train specifications if not provided
        if train_specs is None:
            train_specs = {
                "length_ft": 66.0,
                "width_ft": 10.0,
                "height_ft": 11.5,
                "mass_lbs": 90100,
                "max_power_hp": 161,
                "max_accel_ftps2": 1.64,
                "service_brake_ftps2": -3.94,
                "emergency_brake_ftps2": -8.86,
                "capacity": 222,
                "crew_count": 2
            }
        
        # Create TrainModel instance
        model = TrainModel(train_specs)
        
        # NOTE: For hardware controller, the API and controller are created inside train_controller_ui
        # For software controller, we create them here
        if not use_hardware:
            # Create train_controller_api instance for this train
            api = train_controller_api(train_id=train_id)
            
            # Create train_controller instance
            controller = train_controller(api)
        else:
            # Hardware controller creates its own API and controller internally
            api = None
            controller = None
        
        # Create UI instances if requested
        model_ui = None
        controller_ui = None
        
        if create_uis:
            # Create Train Model UI with train_id
            model_ui = TrainModelUI(train_id=train_id)
            # Position window based on train_id to avoid overlap
            x_offset = 50 + (train_id - 1) * 60
            y_offset = 50 + (train_id - 1) * 60
            model_ui.geometry(f"1450x900+{x_offset}+{y_offset}")
            
            # Create Train Controller UI with train_id
            controller_ui = train_controller_ui(train_id=train_id)
            # Position controller UI to the right of model UI
            controller_ui.geometry(f"600x800+{x_offset + 1460}+{y_offset}")
            
            # For hardware controller, get the controller and API references from the UI
            if use_hardware:
                controller = controller_ui.controller
                api = controller_ui.api
            
            print(f"Train {train_id} UIs created (Model and Controller windows)")
        
        # Create TrainPair
        train_pair = TrainPair(train_id, model, controller, model_ui, controller_ui)
        
        # Store in dictionary
        self.trains[train_id] = train_pair
        
        # Initialize state in JSON file
        self._initialize_train_state(train_id)

        # NEW: Initialize Train Model/train_data.json entry using track model data (index = train_id - 1)
        try:
            self._initialize_train_data_entry(train_id, index=train_id - 1)
        except Exception as e:
            print(f"Warning: failed to initialize train_data.json for train {train_id}: {e}")
        
        print(f"Train {train_id} created successfully")
        return train_id
    
    def _initialize_train_state(self, train_id: int):
        """Initialize state for a train in the JSON file.
        
        Args:
            train_id: ID of the train to initialize.
        """
        # Read current state file
        with open(self.state_file, 'r') as f:
            try:
                all_states = json.load(f)
            except json.JSONDecodeError:
                all_states = {}
        
        # Create state key for this train
        train_key = f"train_{train_id}"
        
        # Default state for new train
        all_states[train_key] = {
            "train_id": train_id,
            "commanded_speed": 60.0,
            "commanded_authority": 1000.0,
            "speed_limit": 60.0,
            "train_velocity": 0.0,
            "next_stop": "Station A",
            "station_side": "Right",
            "train_temperature": 68.0,
            "engine_failure": False,
            "signal_failure": False,
            "brake_failure": False,
            "manual_mode": False,
            "driver_velocity": 0.0,
            "service_brake": False,
            "right_door": False,
            "left_door": False,
            "interior_lights": True,
            "exterior_lights": True,
            "set_temperature": 70.0,
            "temperature_up": False,
            "temperature_down": False,
            "announcement": "",
            "announce_pressed": False,
            "emergency_brake": False,
            "kp": 0,
            "ki": 0,
            "engineering_panel_locked": False,
            "power_command": 0.0
        }
        
        # Write back to file
        with open(self.state_file, 'w') as f:
            json.dump(all_states, f, indent=4)

    # --- NEW: helpers to sync train_data.json with track model inputs ---
    def _safe_read_json(self, path: str) -> dict:
        try:
            with open(path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}

    def _safe_write_json(self, path: str, data: dict):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

    def _initialize_train_data_entry(self, train_id: int, index: int):
        """Create/initialize Train Model/train_data.json section for this train_id using track model data."""
        # Read source data
        track = self._safe_read_json(self.track_model_file)
        train_data = self._safe_read_json(self.train_data_file)

        block = track.get("block", {})
        beacon = track.get("beacon", {})
        train_sec = track.get("train", {})

        def pick(lst, idx, default=0):
            try:
                return lst[idx]
            except Exception:
                return default

        cmd_speeds = block.get("commanded speed", []) or []
        cmd_auths = block.get("commanded authority", []) or []
        boarding = train_sec.get("passengers_boarding_", []) or []

        inputs = {
            "commanded speed": float(pick(cmd_speeds, index, 0.0)),
            "commanded authority": float(pick(cmd_auths, index, 0.0)),
            "speed limit": float(beacon.get("speed limit", 30.0)),
            "current station": beacon.get("current station", "Unknown"),
            "next station": beacon.get("next station", "Unknown"),
            "side_door": beacon.get("side_door", "Right"),
            "passengers_boarding": int(pick(boarding, index, 0)),
            # default controller-related flags
            "engine_failure": False,
            "signal_failure": False,
            "brake_failure": False,
            "emergency_brake": False
        }

        # Ensure root has specs if missing (do not overwrite existing)
        if "specs" not in train_data:
            train_data["specs"] = {
                "length_ft": 66.0,
                "width_ft": 10.0,
                "height_ft": 11.5,
                "mass_lbs": 90100,
                "max_power_hp": 161,
                "max_accel_ftps2": 1.64,
                "service_brake_ftps2": -3.94,
                "emergency_brake_ftps2": -8.86,
                "capacity": 222,
                "crew_count": 2
            }

        train_key = f"train_{train_id}"
        # Initialize a per-train entry alongside the original root sections
        train_data[train_key] = {
            "inputs": inputs,
            "outputs": {
                "velocity_mph": 0.0,
                "acceleration_ftps2": 0.0,
                "position_yds": 0.0,
                "authority_yds": float(inputs["commanded authority"]),
                "station_name": inputs["current station"],
                "next_station": inputs["next station"],
                "left_door_open": False,
                "right_door_open": False,
                "temperature_F": 68.0,
                "door_side": inputs["side_door"],
                "passengers_onboard": 0,
                "passengers_boarding": inputs["passengers_boarding"],
                "passengers_disembarking": 0
            }
        }

        self._safe_write_json(self.train_data_file, train_data)

    def _update_train_data_outputs(self, train_id: int, outputs: dict, state: dict):
        """Update the per-train outputs in Train Model/train_data.json with latest model values."""
        train_data = self._safe_read_json(self.train_data_file)
        train_key = f"train_{train_id}"
        if train_key not in train_data:
            # If missing, initialize with index = train_id-1
            self._initialize_train_data_entry(train_id, max(0, train_id - 1))
            train_data = self._safe_read_json(self.train_data_file)

        entry = train_data.get(train_key, {})
        entry_outputs = entry.get("outputs", {})

        # Map outputs we have
        entry_outputs.update({
            "velocity_mph": outputs.get("velocity_mph", 0.0),
            "acceleration_ftps2": outputs.get("acceleration_ftps2", 0.0),
            "position_yds": outputs.get("position_yds", 0.0),
            "authority_yds": outputs.get("authority_yds", 0.0),
            "station_name": outputs.get("station_name", entry_outputs.get("station_name", "Unknown")),
            "next_station": outputs.get("next_station", entry_outputs.get("next_station", "Unknown")),
            "left_door_open": outputs.get("left_door_open", False),
            "right_door_open": outputs.get("right_door_open", False),
            "temperature_F": outputs.get("temperature_F", entry_outputs.get("temperature_F", 68.0)),
            "door_side": state.get("station_side", entry_outputs.get("door_side", "Right")),
            # keep boarding/passengers counts if you manage elsewhere
        })

        entry["outputs"] = entry_outputs
        train_data[train_key] = entry
        self._safe_write_json(self.train_data_file, train_data)
    
    def remove_train(self, train_id: int) -> bool:
        """Remove a train from the manager.
        
        Args:
            train_id: ID of the train to remove.
        
        Returns:
            True if train was removed, False if train_id not found.
        """
        if train_id not in self.trains:
            print(f"Train {train_id} not found")
            return False
        
        # Close UI windows if they exist
        train_pair = self.trains[train_id]
        if train_pair.model_ui:
            try:
                train_pair.model_ui.destroy()
                print(f"Train {train_id} Model UI closed")
            except:
                pass  # Window may already be closed
        
        if train_pair.controller_ui:
            try:
                train_pair.controller_ui.destroy()
                print(f"Train {train_id} Controller UI closed")
            except:
                pass  # Window may already be closed
        
        # Remove from dictionary
        del self.trains[train_id]
        
        # Remove from state file
        with open(self.state_file, 'r') as f:
            all_states = json.load(f)
        
        train_key = f"train_{train_id}"
        if train_key in all_states:
            del all_states[train_key]
        
        with open(self.state_file, 'w') as f:
            json.dump(all_states, f, indent=4)
        
        print(f"Train {train_id} removed successfully")
        return True
    
    def get_train(self, train_id: int) -> TrainPair:
        """Get a train pair by ID.
        
        Args:
            train_id: ID of the train to retrieve.
        
        Returns:
            TrainPair instance, or None if not found.
        """
        return self.trains.get(train_id, None)
    
    def get_all_train_ids(self) -> list:
        """Get list of all active train IDs.
        
        Returns:
            List of train IDs.
        """
        return list(self.trains.keys())
    
    def get_train_count(self) -> int:
        """Get the number of active trains.
        
        Returns:
            Number of trains currently managed.
        """
        return len(self.trains)
    
    def update_train(self, train_id: int, state_updates: dict) -> bool:
        """Update a specific train's state.
        
        Args:
            train_id: ID of the train to update.
            state_updates: Dictionary of state values to update.
        
        Returns:
            True if update successful, False if train not found.
        """
        if train_id not in self.trains:
            print(f"Train {train_id} not found")
            return False
        
        # Read state file
        with open(self.state_file, 'r') as f:
            all_states = json.load(f)
        
        train_key = f"train_{train_id}"
        if train_key in all_states:
            all_states[train_key].update(state_updates)
        
        # Write back
        with open(self.state_file, 'w') as f:
            json.dump(all_states, f, indent=4)
        
        return True
    
    def get_train_state(self, train_id: int) -> dict:
        """Get a specific train's state from the JSON file.
        
        Args:
            train_id: ID of the train.
        
        Returns:
            Dictionary of train state, or None if not found.
        """
        with open(self.state_file, 'r') as f:
            all_states = json.load(f)
        
        train_key = f"train_{train_id}"
        return all_states.get(train_key, None)
    
    def update_all_trains(self):
        """Update physics and control for all trains.
        
        This method should be called periodically (e.g., by a timer) to update
        the simulation for all active trains.
        """
        for train_id, train_pair in self.trains.items():
            # Get current state for this train
            state = self.get_train_state(train_id)
            
            if state is None:
                continue
            
            # Update controller from state (beacon, commanded speed/authority)
            train_pair.controller.update_from_train_model()
            
            # Calculate power command
            power = train_pair.controller.calculate_power_command(state)
            
            # Update model with inputs
            outputs = train_pair.model.update(
                commanded_speed=state.get("commanded_speed", 0),
                commanded_authority=state.get("commanded_authority", 0),
                speed_limit=state.get("speed_limit", 30),
                current_station=state.get("next_stop", "Unknown"),
                next_station=state.get("next_stop", "Unknown"),
                side_door=state.get("station_side", "Right"),
                power_command=power,
                emergency_brake=state.get("emergency_brake", False),
                service_brake=state.get("service_brake", False),
                set_temperature=state.get("set_temperature", 70.0),
                left_door=state.get("left_door", False),
                right_door=state.get("right_door", False)
            )
            
            # Write outputs back to state
            self.update_train(train_id, {
                "train_velocity": outputs['velocity_mph'],
                "train_temperature": outputs['temperature_F'],
                "power_command": power
            })

            # NEW: Mirror outputs into Train Model/train_data.json under train_{id}
            try:
                self._update_train_data_outputs(train_id, outputs, state)
            except Exception as e:
                print(f"Warning: failed to update train_data.json for train {train_id}: {e}")


class TrainManagerUI(tk.Tk):
    """UI for managing multiple trains.
    
    Provides a control panel for:
    - Adding new trains
    - Removing trains
    - Viewing active trains
    - Starting/stopping simulation updates
    """
    
    def __init__(self):
        """Initialize the Train Manager UI."""
        super().__init__()
        
        self.title("Train Manager - System Control")
        self.geometry("400x600+50+50")
        
        # Create train manager backend
        self.manager = TrainManager()
        
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        # Create UI panels
        self.create_header()
        self.create_train_list()
        self.create_control_buttons()
        self.create_status_bar()
        
        # Update the train list initially
        self.update_train_list()
        
        # Set up update timer (500ms like the train UIs)
        self.update_timer_active = False
        self.start_simulation()
    
    def create_header(self):
        """Create header section with title and info."""
        header_frame = tk.Frame(self, bg="#2c3e50", height=80)
        header_frame.grid(row=0, column=0, sticky="EW", padx=0, pady=0)
        header_frame.columnconfigure(0, weight=1)
        
        title = tk.Label(
            header_frame,
            text="Train Manager",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title.grid(row=0, column=0, pady=(10, 0))
        
        subtitle = tk.Label(
            header_frame,
            text="Multi-Train System Control",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="#bdc3c7"
        )
        subtitle.grid(row=1, column=0, pady=(0, 10))
    
    def create_train_list(self):
        """Create scrollable list of active trains."""
        list_frame = tk.LabelFrame(self, text="Active Trains", font=("Arial", 11, "bold"))
        list_frame.grid(row=1, column=0, sticky="NSEW", padx=10, pady=10)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Create scrollbar
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.grid(row=0, column=1, sticky="NS")
        
        # Create listbox
        self.train_listbox = tk.Listbox(
            list_frame,
            font=("Courier", 10),
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE,
            height=15
        )
        self.train_listbox.grid(row=0, column=0, sticky="NSEW", padx=5, pady=5)
        scrollbar.config(command=self.train_listbox.yview)
        
        # Bind double-click to show train info
        self.train_listbox.bind("<Double-Button-1>", self.show_train_info)
    
    def create_control_buttons(self):
        """Create control buttons for train management."""
        button_frame = tk.Frame(self)
        button_frame.grid(row=2, column=0, sticky="EW", padx=10, pady=(0, 10))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        
        # Controller type selection
        type_frame = tk.LabelFrame(button_frame, text="Controller Type", font=("Arial", 10, "bold"))
        type_frame.grid(row=0, column=0, columnspan=2, sticky="EW", pady=(0, 10))
        
        self.controller_type_var = tk.StringVar(value="software")
        
        hw_radio = tk.Radiobutton(
            type_frame,
            text="🔧 Hardware (Raspberry Pi)",
            variable=self.controller_type_var,
            value="hardware",
            font=("Arial", 10),
            cursor="hand2"
        )
        hw_radio.pack(anchor="w", padx=10, pady=5)
        
        sw_radio = tk.Radiobutton(
            type_frame,
            text="💻 Software (UI Only)",
            variable=self.controller_type_var,
            value="software",
            font=("Arial", 10),
            cursor="hand2"
        )
        sw_radio.pack(anchor="w", padx=10, pady=5)
        
        # Add Train button (prominent green)
        self.add_button = tk.Button(
            button_frame,
            text="➕ Add New Train",
            font=("Arial", 12, "bold"),
            bg="#27ae60",
            fg="white",
            activebackground="#2ecc71",
            activeforeground="white",
            command=self.add_train,
            height=2,
            cursor="hand2"
        )
        self.add_button.grid(row=1, column=0, columnspan=2, sticky="EW", pady=(0, 10))
        
        # Remove Train button
        self.remove_button = tk.Button(
            button_frame,
            text="Remove Selected",
            font=("Arial", 10),
            bg="#e74c3c",
            fg="white",
            activebackground="#c0392b",
            activeforeground="white",
            command=self.remove_selected_train,
            cursor="hand2"
        )
        self.remove_button.grid(row=2, column=0, sticky="EW", padx=(0, 5))
        
        # Update All button
        self.update_button = tk.Button(
            button_frame,
            text="Update All Trains",
            font=("Arial", 10),
            bg="#3498db",
            fg="white",
            activebackground="#2980b9",
            activeforeground="white",
            command=self.update_all_trains,
            cursor="hand2"
        )
        self.update_button.grid(row=2, column=1, sticky="EW", padx=(5, 0))
    
    def create_status_bar(self):
        """Create status bar at bottom."""
        status_frame = tk.Frame(self, bg="#34495e", height=30)
        status_frame.grid(row=3, column=0, sticky="EW")
        
        self.status_label = tk.Label(
            status_frame,
            text="Ready - No trains active",
            font=("Arial", 9),
            bg="#34495e",
            fg="white",
            anchor="w"
        )
        self.status_label.pack(side="left", padx=10, pady=5)
    
    def add_train(self):
        """Add a new train with UIs."""
        try:
            # Get selected controller type from radio buttons
            use_hardware = (self.controller_type_var.get() == "hardware")
            
            train_id = self.manager.add_train(create_uis=True, use_hardware=use_hardware)
            self.update_train_list()
            
            controller_type = "HARDWARE" if use_hardware else "SOFTWARE"
            self.update_status(f"Train {train_id} added with {controller_type} controller")
            print(f"Train {train_id} created with {controller_type} controller and UI windows")
        except Exception as e:
            self.update_status(f"Error adding train: {str(e)}")
            print(f"Error adding train: {e}")
    
    def remove_selected_train(self):
        """Remove the selected train from the list."""
        selection = self.train_listbox.curselection()
        if not selection:
            self.update_status("No train selected")
            return
        
        # Get train ID from selection
        selected_text = self.train_listbox.get(selection[0])
        try:
            # Extract train ID from text like "Train 1 - Model: <obj>, Controller: <obj>"
            train_id = int(selected_text.split()[1])
            
            if self.manager.remove_train(train_id):
                self.update_train_list()
                self.update_status(f"Train {train_id} removed")
                print(f"Train {train_id} removed")
            else:
                self.update_status(f"Failed to remove Train {train_id}")
        except Exception as e:
            self.update_status(f"Error removing train: {str(e)}")
            print(f"Error removing train: {e}")
    
    def show_train_info(self, event):
        """Show detailed info about a train (double-click handler)."""
        selection = self.train_listbox.curselection()
        if not selection:
            return
        
        selected_text = self.train_listbox.get(selection[0])
        try:
            train_id = int(selected_text.split()[1])
            train = self.manager.get_train(train_id)
            
            if train:
                info = f"Train {train_id} Details:\n"
                info += f"Model: {train.model}\n"
                info += f"Controller: {train.controller}\n"
                info += f"Model UI: {'Active' if train.model_ui else 'None'}\n"
                info += f"Controller UI: {'Active' if train.controller_ui else 'None'}"
                
                # Create info popup
                popup = tk.Toplevel(self)
                popup.title(f"Train {train_id} Info")
                popup.geometry("400x200")
                
                info_label = tk.Label(popup, text=info, font=("Courier", 10), justify="left")
                info_label.pack(padx=20, pady=20)
                
                close_btn = tk.Button(popup, text="Close", command=popup.destroy)
                close_btn.pack(pady=(0, 10))
        except Exception as e:
            print(f"Error showing train info: {e}")
    
    def update_train_list(self):
        """Update the listbox with current trains."""
        self.train_listbox.delete(0, tk.END)
        
        train_ids = self.manager.get_all_train_ids()
        if not train_ids:
            self.train_listbox.insert(tk.END, "  No trains active")
            self.train_listbox.config(fg="gray")
        else:
            self.train_listbox.config(fg="black")
            for train_id in train_ids:
                train = self.manager.get_train(train_id)
                ui_status = "✓ UIs" if train.model_ui and train.controller_ui else "⚠ No UIs"
                
                # Determine controller type by checking which UI class is used
                controller_type = "HW" if hasattr(train.controller_ui, 'gpio_leds') else "SW"
                
                self.train_listbox.insert(tk.END, f"Train {train_id} [{controller_type}] - {ui_status}")
        
        # Update status
        count = self.manager.get_train_count()
        if count == 0:
            self.update_status("Ready - No trains active")
        elif count == 1:
            self.update_status(f"Managing 1 train")
        else:
            self.update_status(f"Managing {count} trains")
    
    def update_all_trains(self):
        """Manually trigger update for all trains."""
        try:
            self.manager.update_all_trains()
            self.update_status(f"Updated {self.manager.get_train_count()} trains")
        except Exception as e:
            self.update_status(f"Error updating trains: {str(e)}")
            print(f"Error updating trains: {e}")
    
    def update_status(self, message: str):
        """Update the status bar message.
        
        Args:
            message: Status message to display.
        """
        self.status_label.config(text=message)
    
    def start_simulation(self):
        """Start the periodic simulation updates."""
        self.update_timer_active = True
        self.simulation_loop()
    
    def simulation_loop(self):
        """Periodic update loop for all trains."""
        if self.update_timer_active:
            try:
                # Update all trains
                if self.manager.get_train_count() > 0:
                    self.manager.update_all_trains()
            except Exception as e:
                print(f"Simulation loop error: {e}")
            
            # Schedule next update (500ms)
            self.after(500, self.simulation_loop)
    
    def stop_simulation(self):
        """Stop the periodic simulation updates."""
        self.update_timer_active = False


# Example usage
if __name__ == "__main__":
    import tkinter as tk
    
    # Create and run the Train Manager UI
    app = TrainManagerUI()
    app.mainloop()
