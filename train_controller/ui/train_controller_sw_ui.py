"""Train Controller Software UI.

This module provides the driver interface for the Train Controller,
implementing the same functionality as the hardware version but in software.
Interfaces with the train_controller_api for state management and Train Model communication.

Author: Julen Coca-Knorr 
"""

import tkinter as tk 
from tkinter import ttk
import os
import sys
import time  # Add time module for real-time tracking

# Add parent directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Import API
from api.train_controller_api import train_controller_api


class beacon:
	"""Beacon information for station announcements.
	
	Stores information about the next station and which side doors should open.
	This information is received from the Train Model via the API.
	
	Attributes:
		next_stop: Name of the next station (string).
		station_side: Side where doors should open ('left' or 'right').
	"""
	
	def __init__(self, next_stop: str = "", station_side: str = ""):
		"""Initialize beacon with station information.
		
		Args:
			next_stop: Name of the next station.
			station_side: Side for door opening ('left' or 'right').
		"""
		self.next_stop = next_stop
		self.station_side = station_side
	
	def update_from_state(self, state: dict) -> None:
		"""Update beacon information from train state.
		
		Args:
			state: Train state dictionary containing beacon information.
		"""
		self.next_stop = state.get('next_stop', '')
		self.station_side = state.get('station_side', '')


class commanded_speed_authority:
	"""Commanded speed and authority from wayside/CTC.
	
	Stores the commanded speed and authority received from the wayside controller
	or CTC (Centralized Traffic Control) via the Train Model.
	
	Attributes:
		commanded_speed: Commanded speed in mph (int).
		commanded_authority: Commanded authority in yards (int).
	"""
	
	def __init__(self, commanded_speed: int = 0, commanded_authority: int = 0):
		"""Initialize with commanded speed and authority.
		
		Args:
			commanded_speed: Commanded speed in mph.
			commanded_authority: Commanded authority in yards.
		"""
		self.commanded_speed = commanded_speed
		self.commanded_authority = commanded_authority
	
	def update_from_state(self, state: dict) -> None:
		"""Update commanded values from train state.
		
		Args:
			state: Train state dictionary containing commanded values.
		"""
		self.commanded_speed = int(state.get('commanded_speed', 0))
		self.commanded_authority = int(state.get('commanded_authority', 0))


class vital_train_controls:
	"""Vital train controls for safety-critical operations.
	
	Stores safety-critical train parameters. Used as a candidate for validation
	before committing changes to the API.
	
	Attributes:
		kp: Proportional gain for PI controller (float).
		ki: Integral gain for PI controller (float).
		train_velocity: Current train velocity in mph (float).
		driver_velocity: Driver's set velocity in mph (float).
		emergency_brake: Emergency brake state (bool).
		service_brake: Service brake state (bool).
		power_command: Power command in Watts (float).
		commanded_authority: Commanded authority in yards (float).
		speed_limit: Current speed limit in mph (float).
	"""
	
	def __init__(self, kp: float = 0.0, ki: float = 0.0, train_velocity: float = 0.0,
	             driver_velocity: float = 0.0, emergency_brake: bool = False,
	             service_brake: bool = False, power_command: float = 0.0,
	             commanded_authority: float = 0.0, speed_limit: float = 0.0):
		"""Initialize vital train controls with given values.
		
		Args:
			kp: Proportional gain.
			ki: Integral gain.
			train_velocity: Current velocity.
			driver_velocity: Driver's set velocity.
			emergency_brake: Emergency brake state.
			service_brake: Service brake state.
			power_command: Power command.
			commanded_authority: Commanded authority.
			speed_limit: Speed limit.
		"""
		self.kp = kp
		self.ki = ki
		self.train_velocity = train_velocity
		self.driver_velocity = driver_velocity
		self.emergency_brake = emergency_brake
		self.service_brake = service_brake
		self.power_command = power_command
		self.commanded_authority = commanded_authority
		self.speed_limit = speed_limit
	
	def calculate_power_command(self, accumulated_error: float, last_update_time: float) -> tuple:
		"""Calculate power command based on speed difference and Kp/Ki values.
		
		Implements PI control with:
		- Real-time accumulated error tracking
		- Anti-windup protection
		- Power limiting
		- Zero power when error is zero or negative (train going too fast)
		
		Args:
			accumulated_error: Current accumulated error for integral term.
			last_update_time: Time of last calculation (seconds).
			
		Returns:
			Tuple of (power_command, new_accumulated_error, new_update_time).
		"""
		# Calculate speed error
		speed_error = self.driver_velocity - self.train_velocity
		
		# If speed error is zero or negative (train at or above target), return zero power
		if speed_error <= 0.01:  # Exact match or train too fast
			return (0.0, 0.0, time.time())  # Reset accumulated error and return 0 power
		
		# Get current time
		current_time = time.time()
		
		# Calculate real time step
		dt = current_time - last_update_time
		dt = max(0.001, min(dt, 1.0))  # Limit dt between 1ms and 1s for stability
		
		# Update accumulated error with anti-windup and scaling
		new_accumulated_error = accumulated_error + speed_error * dt
		
		# Anti-windup limits (scaled by ki to prevent excessive integral term)
		max_integral = 120000 / self.ki if self.ki != 0 else 0
		new_accumulated_error = max(-max_integral, min(max_integral, new_accumulated_error))
		
		# Calculate PI control output
		proportional = self.kp * speed_error
		integral = self.ki * new_accumulated_error
		
		# Calculate total power command
		power = proportional + integral
		
		# Limit power
		power = max(0, min(power, 120000))  # 120kW max power
		
		# Anti-windup: adjust accumulated error when power saturates
		if power == 120000 and integral > 0:
			# Back-calculate integral term to match power limit
			new_accumulated_error = (120000 - proportional) / self.ki if self.ki != 0 else 0
		elif power == 0 and integral < 0:
			# Reset integral term when power is zero
			new_accumulated_error = -proportional / self.ki if self.ki != 0 else 0
		
		return (power, new_accumulated_error, current_time)


class vital_validator_first_check:
	"""First validator for vital train controls (hard safety rules).
	
	Performs hard safety checks that must never be violated.
	"""
	
	def validate(self, v: vital_train_controls) -> bool:
		"""Validate vital train controls (first check - hard rules).
		
		Args:
			v: The vital train controls to validate.
			
		Returns:
			True if validation passes, False otherwise.
		"""
		# Check 1: Velocity must not exceed speed limit (if speed limit is set)
		# Allow power=0 or braking even when speeding (to slow down)
		if v.speed_limit > 0 and v.train_velocity > v.speed_limit:
			# Only reject if trying to apply MORE power when already speeding
			if v.power_command > 0:
				print(f"VALIDATION FAILED: Velocity {v.train_velocity} exceeds speed limit {v.speed_limit} and trying to apply power {v.power_command}")
				return False
		
		# Check 2: Power command must be within valid range (0-120000W)
		if v.power_command < 0 or v.power_command > 120000:
			print(f"VALIDATION FAILED: Power command {v.power_command} out of range [0, 120000]")
			return False
		
		# Check 3: Cannot have both service and emergency brake active
		if v.service_brake and v.emergency_brake:
			print("VALIDATION FAILED: Both service brake and emergency brake are active")
			return False
		
		# Check 4: Cannot have power when authority is depleted
		if v.commanded_authority <= 0 and v.power_command > 0:
			print(f"VALIDATION FAILED: Power command {v.power_command} with no authority")
			return False
		
		return True


class vital_validator_second_check:
	"""Second validator for vital train controls (soft safety rules with margin).
	
	Provides a second validation layer with slight margins for realistic operation.
	"""
	
	def validate(self, v: vital_train_controls) -> bool:
		"""Validate vital train controls (second check - with margin).
		
		Args:
			v: The vital train controls to validate.
			
		Returns:
			True if validation passes, False otherwise.
		"""
		# Check 1: Allow 2% margin over speed limit for realistic deceleration (if speed limit is set)
		if v.speed_limit > 0:
			safe_speed = v.speed_limit * 1.02
			if v.train_velocity > safe_speed:
				print(f"VALIDATION FAILED: Velocity {v.train_velocity} exceeds safe speed {safe_speed}")
				return False
		
		# Check 2: Cannot have both brakes active
		if v.service_brake and v.emergency_brake:
			print("VALIDATION FAILED: Both brakes active (second check)")
			return False
		
		# Check 3: Authority check
		if v.commanded_authority > 0 or v.power_command == 0:
			return True
		else:
			print("VALIDATION FAILED: No authority but power commanded (second check)")
			return False


class train_controller:
	"""Train controller logic and calculations.
	
	Handles all train control logic including power calculations, speed management,
	brake control, and state management. All vital changes go through validation.
	
	Attributes:
		api: train_controller_api instance for state management.
		beacon_info: beacon instance storing station information.
		cmd_speed_auth: commanded_speed_authority instance.
		validators: List of validators for vital controls.
		_accumulated_error: Accumulated speed error for integral control.
		_last_update_time: Last update time for power calculation.
	"""
	
	def __init__(self, api: train_controller_api):
		"""Initialize train controller with API reference.
		
		Args:
			api: Shared train_controller_api instance.
		"""
		self.api = api
		self._accumulated_error = 0.0
		self._last_update_time = time.time()
		
		# Create instances for beacon and commanded speed/authority 
		self.beacon_info = beacon()
		self.cmd_speed_auth = commanded_speed_authority()
		
		# Create validators
		self.validators = [vital_validator_first_check(), vital_validator_second_check()]
	
	def update_from_train_model(self) -> None:
		"""Update beacon and commanded speed/authority from Train Model.
		
		Call this periodically to sync with Train Model data from train_data.json.
		"""
		# Sync from train_data.json to train_states.json inputs
		self.api.update_from_train_data()
		
		# Update local beacon and commanded speed/authority from synced state
		state = self.api.get_state()
		self.beacon_info.update_from_state(state)
		self.cmd_speed_auth.update_from_state(state)
	
	def vital_control_check_and_update(self, changes: dict) -> bool:
		"""Run validators and apply vital changes to API only if accepted.
		
		Args:
			changes: Dictionary of vital control changes to apply.
			
		Returns:
			True if validation passed and changes applied, False otherwise.
		"""
		# Build a vital_train_controls candidate from current state + changes 
		state = self.api.get_state().copy()
		candidate = vital_train_controls(
			kp=changes.get('kp', state.get('kp', 0.0)),
			ki=changes.get('ki', state.get('ki', 0.0)),
			train_velocity=changes.get('train_velocity', state.get('train_velocity', 0.0)),
			driver_velocity=changes.get('driver_velocity', state.get('driver_velocity', 0.0)),
			emergency_brake=changes.get('emergency_brake', state.get('emergency_brake', False)),
			service_brake=changes.get('service_brake', state.get('service_brake', 0)),
			power_command=changes.get('power_command', state.get('power_command', 0.0)),
			commanded_authority=changes.get('commanded_authority', state.get('commanded_authority', 0.0)),
			speed_limit=changes.get('speed_limit', state.get('speed_limit', 0.0))
		)
		
		# Run through all validators
		for validator in self.validators:
			if not validator.validate(candidate):
				print(f"Vital validation failed - change rejected: {changes}")
				return False
		
		# All validators passed - commit changes to API
		self.api.update_state({k: v for k, v in changes.items()})
		return True
	
	def calculate_power_command(self, state: dict) -> float:
		"""Calculate power command using vital_train_controls.
		
		Args:
			state: Current train state dictionary.
			
		Returns:
			Power command in Watts (0-120000). Returns 0 if kp/ki not set or velocity exceeds speed limit.
		"""
		# If kp or ki are not set, train cannot move
		if 'kp' not in state or 'ki' not in state or state['kp'] is None or state['ki'] is None:
			return 0.0
		
		# Create a vital_train_controls instance with current state
		controls = vital_train_controls(
			kp=state['kp'],
			ki=state['ki'],
			train_velocity=state['train_velocity'],
			driver_velocity=state['driver_velocity'],
			emergency_brake=state['emergency_brake'],
			service_brake=state['service_brake'],
			power_command=state['power_command'],
			commanded_authority=state['commanded_authority'],
			speed_limit=state['speed_limit']
		)
		
		# Calculate power using vital_train_controls method
		power, new_error, new_time = controls.calculate_power_command(
			self._accumulated_error, 
			self._last_update_time
		)
		
		# Update internal tracking variables
		self._accumulated_error = new_error
		self._last_update_time = new_time
		
		return power
	
	def set_emergency_brake(self, activate: bool) -> None:
		"""Set emergency brake state through vital validation.
		
		Args:
			activate: True to activate emergency brake, False to release.
		"""
		changes = {
			'emergency_brake': activate,
			'driver_velocity': 0 if activate else self.api.get_state()['driver_velocity'],
			'power_command': 0 if activate else self.api.get_state()['power_command']
		}
		self.vital_control_check_and_update(changes)
	
	def set_service_brake(self, activate: bool) -> None:
		"""Set service brake state through vital validation.
		
		Args:
			activate: True to activate service brake, False to release.
		"""
		changes = {
			'service_brake': activate,
			'power_command': 0 if activate else self.api.get_state()['power_command']
		}
		self.vital_control_check_and_update(changes)
	
	def adjust_temperature(self, increase: bool) -> None:
		"""Adjust temperature setpoint.
		
		Args:
			increase: True to increase temperature, False to decrease.
		"""
		current_state = self.api.get_state()
		set_temp = current_state['set_temperature']
		
		if increase and set_temp < 95:
			self.api.update_state({
				'set_temperature': set_temp + 1,
				'temperature_up': True,
				'temperature_down': False
			})
		elif not increase and set_temp > 55:
			self.api.update_state({
				'set_temperature': set_temp - 1,
				'temperature_up': False,
				'temperature_down': True
			})
	
	def toggle_door(self, side: str) -> None:
		"""Toggle door state.
		
		Args:
			side: Door side ('left' or 'right').
		"""
		state = self.api.get_state()
		door_key = f'{side}_door'
		self.api.update_state({door_key: not state[door_key]})
	
	def toggle_interior_lights(self) -> None:
		"""Toggle interior lights state."""
		state = self.api.get_state()
		self.api.update_state({'interior_lights': not state['interior_lights']})
	
	def toggle_exterior_lights(self) -> None:
		"""Toggle exterior lights state."""
		state = self.api.get_state()
		self.api.update_state({'exterior_lights': not state['exterior_lights']})
	
	def set_announcement(self, active: bool) -> None:
		"""Set announcement state and generate announcement text.
		
		Args:
			active: True to activate announcement, False to deactivate.
		"""
		state = self.api.get_state()
		
		if active:
			# Generate announcement based on next station
			next_stop = self.beacon_info.next_stop
			station_side = self.beacon_info.station_side
			
			if next_stop:
				announcement = f"Next stop: {next_stop}. Doors will open on the {station_side.lower()} side."
			else:
				announcement = "Welcome aboard!"
			
			self.api.update_state({
				'announce_pressed': True,
				'announcement': announcement
			})
		else:
			self.api.update_state({
				'announce_pressed': False,
				'announcement': ''
			})
	
	def toggle_manual_mode(self) -> None:
		"""Toggle between manual and automatic mode."""
		state = self.api.get_state()
		self.api.update_state({'manual_mode': not state['manual_mode']})
	
	def update_speed(self, increase: bool) -> None:
		"""Update driver set speed through vital validation.
		
		Args:
			increase: True to increase speed, False to decrease.
		"""
		state = self.api.get_state()
		current_set_speed = state['driver_velocity']
		
		if increase:
			commanded_speed = self.cmd_speed_auth.commanded_speed
			speed_limit = state['speed_limit']
			
			# In manual mode or if commanded_speed is 0, only limit by speed_limit
			# In automatic mode, limit by both commanded_speed and speed_limit
			if state.get('manual_mode', False) or commanded_speed == 0:
				max_allowed_speed = speed_limit if speed_limit > 0 else 100  # Default max 100 mph
			else:
				max_allowed_speed = min(commanded_speed, speed_limit) if speed_limit > 0 else commanded_speed
			
			new_speed = min(max_allowed_speed, current_set_speed + 1)
		else:
			new_speed = max(0, current_set_speed - 1)
		
		# Calculate new power command with new speed
		state_copy = state.copy()
		state_copy['driver_velocity'] = new_speed
		power = self.calculate_power_command(state_copy)
		
		# Apply changes through vital validation
		self.vital_control_check_and_update({
			'driver_velocity': new_speed,
			'power_command': power
		})
	
	def detect_failure_mode(self) -> None:
		"""Detect failure modes in the system.
		
		TODO: Implement failure detection logic.
		"""
		pass
	
	def handle_failure_mode(self, mode: str) -> None:
		"""Handle detected failure mode.
		
		Args:
			mode: Type of failure mode detected.
			
		TODO: Implement failure handling logic.
		"""
		pass


class train_controller_ui(tk.Tk):
    """Train controller user interface.
    
    Provides UI for train driver control including:
        - Speed control and display
        - Authority and commanded speed display
        - Door controls
        - Light controls
        - Temperature controls
        - Brake controls
        - Engineering panel with Kp/Ki settings
    
    This class handles only the view layer. All control logic is delegated to
    the train_controller instance. Both classes share the same train_controller_api
    instance for state management and communication with the Train Model.
    
    Attributes:
        controller: train_controller instance for logic operations.
        api: train_controller_api instance for state management (shared with controller).
        emergency_brake_release_timer: Timer ID for emergency brake auto-release.
    """
    
    def __init__(self, train_id=None):
        """Initialize the driver interface.
        
        Args:
            train_id: Optional train ID for multi-train support. If None, uses root level (legacy).
        """
        super().__init__()
        
        self.train_id = train_id
        
        # Initialize API with train_id
        self.api = train_controller_api(train_id=train_id)
        
        # Create controller instance with shared API
        self.controller = train_controller(self.api)
        
        # UI-specific tracking
        self.emergency_brake_release_timer = None
        
        # Track last beacon info to detect when passing new beacons
        self._last_beacon_station = None
        self._last_beacon_for_announcement = None  # For automatic announcements
        
        # Configure window
        title = f"Train {train_id} - Train Controller" if train_id else "Train Controller - Driver Interface"
        self.title(title)
        self.geometry("1200x800")
        self.configure(bg='lightgray')
        
        # Define colors for buttons
        self.active_color = '#ff4444'
        self.normal_color = 'lightgray'
        
        # Main layout configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=3)  # More space for top section
        self.grid_rowconfigure(1, weight=2)  # Space for controls
        self.grid_rowconfigure(2, weight=1)  # Less space for engineering panel
        
        # Create main container frames with proper weights
        self.top_frame = ttk.Frame(self)
        self.top_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        self.top_frame.grid_columnconfigure(0, weight=1)
        self.top_frame.grid_columnconfigure(1, weight=1)
        
        self.control_frame = ttk.Frame(self)
        self.control_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        
        self.engineering_frame = ttk.Frame(self)
        self.engineering_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        
        # Create UI sections in new layout
        self.create_speed_section()     # Left side of top frame
        self.create_info_table()        # Right side of top frame
        self.create_control_section()    # Middle frame
        self.create_engineering_panel()  # Bottom frame
        
        # Start periodic updates
        self.update_interval = 500  # 500ms = 0.5 seconds
        self.periodic_update()
    
    def create_speed_section(self):
        """Create speed control and display section."""
        speed_frame = ttk.LabelFrame(self.top_frame, text="Speed Control")
        speed_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
        
        # Current speed display (large and centered)
        speed_display_frame = ttk.Frame(speed_frame)
        speed_display_frame.pack(expand=True, fill="both", pady=20)
        
        ttk.Label(speed_display_frame, text="Current Speed", font=('Arial', 14)).pack()
        self.speed_display = ttk.Label(speed_display_frame, text="0 MPH", font=('Arial', 36, 'bold'))
        self.speed_display.pack(pady=10)
        
        # Driver set speed input
        set_speed_frame = ttk.Frame(speed_frame)
        set_speed_frame.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(set_speed_frame, text="Set Driver Speed (mph):").pack()
        
        # Entry and button in a horizontal frame
        input_frame = ttk.Frame(set_speed_frame)
        input_frame.pack(pady=5)
        
        self.speed_entry = ttk.Entry(input_frame, width=10, font=('Arial', 14))
        self.speed_entry.pack(side="left", padx=5)
        self.speed_entry.insert(0, "0")
        self.speed_entry.bind('<Return>', lambda e: self.set_driver_speed())  # Press Enter to set speed
        
        self.set_speed_btn = ttk.Button(input_frame, text="Set Speed", command=self.set_driver_speed)
        self.set_speed_btn.pack(side="left", padx=5)
        
        # Display current set speed
        self.set_speed_label = ttk.Label(set_speed_frame, text="Current Set: 0 MPH", font=('Arial', 12, 'bold'))
        self.set_speed_label.pack(pady=5)
    
    def create_info_table(self):
        """Create the information table displaying train status and inputs from Train Model."""
        table_frame = ttk.LabelFrame(self.top_frame, text="Train Information")
        table_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        
        # Create a treeview for the table
        self.info_table = ttk.Treeview(table_frame, columns=("Name", "Value", "Unit"), show="headings", height=10)
        self.info_table.heading("Name", text="Parameter")
        self.info_table.heading("Value", text="Value")
        self.info_table.heading("Unit", text="Unit")
        
        # Configure column widths
        self.info_table.column("Name", width=200)
        self.info_table.column("Value", width=150)
        self.info_table.column("Unit", width=100)
        
        # Add rows with initial values - (Name, Value, Unit)
        self.info_table.insert("", "end", "commanded_speed", values=("Commanded Speed", "0", "mph"))
        self.info_table.insert("", "end", "speed_limit", values=("Speed Limit", "0", "mph"))
        self.info_table.insert("", "end", "authority", values=("Commanded Authority", "0", "yds"))
        self.info_table.insert("", "end", "temperature", values=("Train Temperature", "70", "°F"))
        self.info_table.insert("", "end", "current_station", values=("Current Station", "--", "Name"))
        self.info_table.insert("", "end", "next_stop", values=("Next Stop", "--", "Name"))
        self.info_table.insert("", "end", "power", values=("Power Command", "0", "W"))
        self.info_table.insert("", "end", "station_side", values=("Station Side", "--", "right/left"))
        self.info_table.insert("", "end", "failures", values=("System Failures", "None", ""))
        
        # Add explanatory text
        ttk.Label(table_frame, text="*Values shown are inputs from Train Model", 
                 font=('Arial', 8, 'italic')).pack(side="bottom", pady=5)
        
        self.info_table.pack(padx=5, pady=5, expand=True, fill="both")
    
    def create_control_section(self):
        """Create control buttons section."""
        controls_label_frame = ttk.LabelFrame(self.control_frame, text="Train Controls")
        controls_label_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create a frame for all buttons
        button_frame = ttk.Frame(controls_label_frame)
        button_frame.pack(expand=True, fill="both", padx=5, pady=5)
        
        # Configure grid for button layout
        for i in range(3):  # 3 rows
            button_frame.grid_rowconfigure(i, weight=1)
        for i in range(4):  # 4 columns (exterior lights, interior lights, left door, right door)
            button_frame.grid_columnconfigure(i, weight=1)
        
        # Create all buttons with consistent size and spacing
        button_width = 15
        button_height = 2
        padding = 5
        
        # Row 1
        self.exterior_lights_btn = tk.Button(button_frame, text="Exterior Lights", command=self.toggle_exterior_lights,
                                  bg=self.normal_color, width=button_width, height=button_height)
        self.exterior_lights_btn.grid(row=0, column=0, padx=padding, pady=padding)
        
        self.interior_lights_btn = tk.Button(button_frame, text="Interior Lights", command=self.toggle_interior_lights,
                                  bg=self.normal_color, width=button_width, height=button_height)
        self.interior_lights_btn.grid(row=0, column=1, padx=padding, pady=padding)
        
        self.left_door_btn = tk.Button(button_frame, text="Left Door", command=self.toggle_left_door,
                                     bg=self.normal_color, width=button_width, height=button_height)
        self.left_door_btn.grid(row=0, column=2, padx=padding, pady=padding)
        
        self.right_door_btn = tk.Button(button_frame, text="Right Door", command=self.toggle_right_door,
                                      bg=self.normal_color, width=button_width, height=button_height)
        self.right_door_btn.grid(row=0, column=3, padx=padding, pady=padding)
        
        # Row 2 (Brake Controls)

        # Announcement button
        self.announce_btn = tk.Button(button_frame, text="Announcement", command=self.toggle_announcement,
                                   bg=self.normal_color, width=button_width, height=button_height)
        self.announce_btn.grid(row=1, column=0, padx=padding, pady=padding)

        self.service_brake_btn = tk.Button(button_frame, text="Service Brake", 
                                         command=self.toggle_service_brake,
                                         bg=self.normal_color, width=button_width, height=button_height)
        self.service_brake_btn.grid(row=1, column=1, padx=padding, pady=padding)
        
        self.emergency_brake_btn = tk.Button(button_frame, text="Emergency Brake", 
                                           command=self.emergency_brake,
                                           bg=self.normal_color, width=button_width, height=button_height)
        self.emergency_brake_btn.grid(row=1, column=2, padx=padding, pady=padding)
        
        # Manual Mode button
        self.manual_mode_btn = tk.Button(button_frame, text="Manual Mode", 
                                        command=self.toggle_manual_mode,
                                        bg=self.normal_color, width=button_width, height=button_height,
                                        state='normal')  # Explicitly set to normal at creation
        self.manual_mode_btn.grid(row=1, column=3, padx=padding, pady=padding)
        print(f"[DEBUG] Manual mode button created with state: {self.manual_mode_btn['state']}")

                
        # Row 3 (Temperature Controls)
        temperature_frame = ttk.LabelFrame(button_frame, text="Temperature Control")
        temperature_frame.grid(row=2, column=0, columnspan=1, padx=padding, pady=padding, sticky="nsew")
        
        # Set temperature display
        ttk.Label(temperature_frame, text="Set Temperature:").grid(row=0, column=0, padx=5, pady=2)
        self.set_temp_label = ttk.Label(temperature_frame, text="70°F", font=('Arial', 12))
        self.set_temp_label.grid(row=0, column=1, padx=5, pady=2)
        
        # Current temperature display
        ttk.Label(temperature_frame, text="Current Temp:").grid(row=1, column=0, padx=5, pady=2)
        self.current_temp_label = ttk.Label(temperature_frame, text="70°F", font=('Arial', 12))
        self.current_temp_label.grid(row=1, column=1, padx=5, pady=2)
        
        # Temperature control buttons
        self.temp_up_btn = ttk.Button(temperature_frame, text="↑", command=self.temp_up)
        self.temp_up_btn.grid(row=0, column=2, padx=5, pady=2)
        self.temp_down_btn = ttk.Button(temperature_frame, text="↓", command=self.temp_down)
        self.temp_down_btn.grid(row=1, column=2, padx=5, pady=2)

        
    def create_engineering_panel(self):
        """Create engineering control panel."""
        eng_frame = ttk.LabelFrame(self.engineering_frame, text="Engineering Panel")
        eng_frame.pack(fill="x", expand=True, padx=10, pady=5)
        
        # Kp and Ki inputs
        ttk.Label(eng_frame, text="Kp:").grid(row=0, column=0, padx=5, pady=5)
        self.kp_entry = ttk.Entry(eng_frame)
        self.kp_entry.grid(row=0, column=1, padx=5, pady=5)
        self.kp_entry.insert(0, "1500.0")  # Balanced Kp for quick response without saturation
        
        ttk.Label(eng_frame, text="Ki:").grid(row=0, column=2, padx=5, pady=5)
        self.ki_entry = ttk.Entry(eng_frame)
        self.ki_entry.grid(row=0, column=3, padx=5, pady=5)
        self.ki_entry.insert(0, "50.0")  # Ki for eliminating steady-state error
        
        self.lock_btn = ttk.Button(eng_frame, text="Lock Values", command=self.lock_engineering_values)
        self.lock_btn.grid(row=0, column=4, padx=20, pady=5)
    
    def detect_and_respond_to_failures(self, state: dict):
        """Detect failures based on Train Model behavior and activate Train Controller failure flags.
        
        Logic:
        - Engine Failure: Only detected when power is applied but train doesn't accelerate
        - Signal Failure: Detected immediately when train_model_signal_failure is active
        - Brake Failure: Only detected when service brake is pressed but train doesn't slow
        
        When detected, Train Controller activates corresponding train_controller_* flag and engages emergency brake.
        """
        updates = {}
        
        # Detect engine failure: Only when trying to apply power but train doesn't respond
        # Engine failure is latent until driver tries to accelerate
        if state.get('train_model_engine_failure', False):
            # Detect if power command is significant (> 1000W) - driver is trying to accelerate
            power_applied = state.get('power_command', 0.0) > 1000.0
            
            # Engine failure detected when significant power is applied
            # The train won't accelerate properly (Train Model blocks acceleration)
            if power_applied:
                if not state.get('train_controller_engine_failure', False):
                    print("[Train Controller] ENGINE FAILURE DETECTED - Power applied but train not responding! Engaging emergency brake")
                    updates['train_controller_engine_failure'] = True
        
        # Detect signal pickup failure: Only when Train Model blocks a beacon read
        # Train Model sets beacon_read_blocked=True when it encounters a new beacon but can't read it
        if state.get('beacon_read_blocked', False):
            if not state.get('train_controller_signal_failure', False):
                print("[Train Controller] SIGNAL PICKUP FAILURE DETECTED - Failed to read beacon! Engaging emergency brake")
                updates['train_controller_signal_failure'] = True
                updates['beacon_read_blocked'] = False  # Clear the flag after detecting
        
        # Detect brake failure: Only detectable when service brake is pressed
        # Train Model activates train_model_brake_failure, but driver only knows when they try to brake
        # Once detected, train_controller_brake_failure stays set until manually cleared
        if state.get('train_model_brake_failure', False) and state.get('service_brake', False):
            if not state.get('train_controller_brake_failure', False):
                print("[Train Controller] BRAKE FAILURE DETECTED - Service brake not responding! Engaging emergency brake")
                updates['train_controller_brake_failure'] = True
                updates['emergency_brake'] = True  # Engage emergency brake immediately
        
        # Apply updates if any failures were detected/cleared
        if updates:
            self.api.update_state(updates)
    
    def periodic_update(self):
        """Update display every update_interval milliseconds."""
        try:
            # Read inputs from train_data.json (written by Test UI or Train Model)
            self.api.update_from_train_data()
            
            # Sync beacon and commanded speed/authority from Train Model
            self.controller.update_from_train_model()
            
            current_state = self.api.get_state()
            
            # Detect failures based on Train Model behavior
            self.detect_and_respond_to_failures(current_state)
            
            # Reload state after failure detection updates
            current_state = self.api.get_state()
            
            # Handle automatic vs manual mode behaviors
            manual_mode = current_state.get('manual_mode', False)
            
            if not manual_mode:  # Automatic mode
                # Auto-set driver velocity to commanded speed
                if current_state['driver_velocity'] != current_state['commanded_speed']:
                    self.api.update_state({'driver_velocity': current_state['commanded_speed']})
                    current_state = self.api.get_state()
                
                # Auto-regulate temperature to 70°F
                if current_state['set_temperature'] != 70.0:
                    self.api.update_state({'set_temperature': 70.0})
                    current_state = self.api.get_state()
                
                # Auto-announcement when beacon changes
                current_station = current_state.get('current_station', '')
                if current_station and current_station != self._last_beacon_for_announcement:
                    # Beacon changed - make announcement
                    next_stop = current_state.get('next_stop', '')
                    if next_stop:
                        announcement = f"Next stop: {next_stop}"
                        self.api.update_state({'announcement': announcement})
                    self._last_beacon_for_announcement = current_station
            else:  # Manual mode
                # Update beacon tracking even in manual mode
                current_station = current_state.get('current_station', '')
                if current_station:
                    self._last_beacon_for_announcement = current_station
            
            # Enable/disable buttons based on mode
            self.update_button_enabled_states(manual_mode, current_state['emergency_brake'])
            
            # Check for critical failures that require emergency brake
            critical_failure = (current_state.get('train_controller_engine_failure', False) or 
                              current_state.get('train_controller_signal_failure', False) or 
                              current_state.get('train_controller_brake_failure', False))
            
            if critical_failure and not current_state['emergency_brake']:
                # Automatically engage emergency brake on critical failure
                self.controller.set_emergency_brake(True)
                
            # Recalculate power command based on current state
            if (not current_state['emergency_brake'] and 
                not current_state['service_brake'] and 
                not critical_failure):
                power = self.controller.calculate_power_command(current_state)
                print(f"[DEBUG POWER] train_vel={current_state['train_velocity']:.2f}, driver_vel={current_state['driver_velocity']:.2f}, calculated_power={power:.2f}")
                # Always update power command even if same to ensure it's written
                self.controller.vital_control_check_and_update({'power_command': power})
            else:
                # Reset accumulated error when brakes are active
                self.controller._accumulated_error = 0
                # Set power to 0 when brakes are active or failures present
                self.controller.vital_control_check_and_update({
                    'power_command': 0
                })
            
            # Update current speed display
            self.speed_display.config(text=f"{current_state['train_velocity']:.1f} MPH")
            
            # Update information table with values (Name column stays constant)
            self.info_table.set("commanded_speed", column="Value", value=f"{current_state['commanded_speed']:.1f}")
            self.info_table.set("speed_limit", column="Value", value=f"{current_state['speed_limit']:.1f}")
            self.info_table.set("authority", column="Value", value=f"{current_state['commanded_authority']:.1f}")
            self.info_table.set("temperature", column="Value", value=f"{int(round(current_state['train_temperature']))}")
            self.info_table.set("current_station", column="Value", value=current_state.get('current_station', '--'))
            self.info_table.set("next_stop", column="Value", value=current_state['next_stop'])
            self.info_table.set("power", column="Value", value=f"{current_state['power_command']:.1f}")
            self.info_table.set("station_side", column="Value", value=current_state['station_side'])
            
            # Update failures in table with color
            failures = []
            has_failures = False
            if current_state.get('train_controller_engine_failure', False):
                failures.append("Engine")
                has_failures = True
            if current_state.get('train_controller_signal_failure', False):
                failures.append("Signal")
                has_failures = True
            if current_state.get('train_controller_brake_failure', False):
                failures.append("Brake")
                has_failures = True
            failure_text = ", ".join(failures) if failures else "None"
            
            # Update failure text and color
            self.info_table.set("failures", column="Value", value=failure_text)
            # Change text color based on failure state
            self.info_table.tag_configure("failure_tag", foreground="red")
            self.info_table.tag_configure("normal_tag", foreground="black")
            if has_failures:
                self.info_table.item("failures", tags=("failure_tag",))
            else:
                self.info_table.item("failures", tags=("normal_tag",))
            
            # Update speed displays
            self.speed_display.config(text=f"{current_state['train_velocity']:.1f} MPH")
            self.set_speed_label.config(text=f"Current Set: {current_state['driver_velocity']:.1f} MPH")
            
            # Update speed entry if user is not currently typing (check if entry has focus)
            if self.speed_entry.focus_get() != self.speed_entry:
                current_entry = self.speed_entry.get()
                try:
                    if float(current_entry) != current_state['driver_velocity']:
                        self.speed_entry.delete(0, tk.END)
                        self.speed_entry.insert(0, f"{current_state['driver_velocity']:.1f}")
                except ValueError:
                    # If entry is invalid, update it with current value
                    self.speed_entry.delete(0, tk.END)
                    self.speed_entry.insert(0, f"{current_state['driver_velocity']:.1f}")
            
            # Update temperature displays
            self.set_temp_label.config(text=f"{int(round(current_state['set_temperature']))}°F")
            self.current_temp_label.config(text=f"{int(round(current_state['train_temperature']))}°F")
            
            # Update control button states
            self.update_button_states(current_state)
            
        except Exception as e:
            print(f"Update error: {e}")
        finally:
            # Always schedule next update
            self.after(self.update_interval, self.periodic_update)
    
    def update_failure_indicator(self, label, system, failed):
        """Update a failure indicator label."""
        label.config(
            text=f"{system}: {'FAILED' if failed else 'OK'}",
            foreground="red" if failed else "green"
        )
    
    def update_button_enabled_states(self, manual_mode, emergency_brake_active):
        """Enable/disable buttons based on manual vs automatic mode."""
        # In automatic mode, disable all control buttons except manual mode toggle and emergency brake
        button_state = 'normal' if manual_mode else 'disabled'
        
        # Control buttons that should be disabled in automatic mode
        self.left_door_btn.configure(state=button_state)
        self.right_door_btn.configure(state=button_state)
        self.announce_btn.configure(state=button_state)
        self.exterior_lights_btn.configure(state=button_state)
        self.interior_lights_btn.configure(state=button_state)
        self.temp_up_btn.configure(state=button_state)
        self.temp_down_btn.configure(state=button_state)
        self.service_brake_btn.configure(state=button_state)
        self.speed_entry.configure(state=button_state)
        self.set_speed_btn.configure(state=button_state)
        
        # Emergency brake: ALWAYS enabled (can press in any mode), disabled only after activation
        if emergency_brake_active:
            self.emergency_brake_btn.configure(state='disabled')
        else:
            self.emergency_brake_btn.configure(state='normal')
        
        # Manual mode button is ALWAYS enabled so driver can switch modes
        mode_text = "Manual Mode: ON" if manual_mode else "Automatic Mode"
        self.manual_mode_btn.configure(state='normal', text=mode_text)
        print(f"[DEBUG update_button_enabled_states] Manual mode button set to: state='normal', text='{mode_text}'")
    
    def update_button_states(self, state):
        """Update button colors based on their states."""
        # Door buttons
        self.left_door_btn.configure(bg=self.active_color if state['left_door'] else self.normal_color)
        self.right_door_btn.configure(bg=self.active_color if state['right_door'] else self.normal_color)
        
        # Announcement button
        self.announce_btn.configure(bg=self.active_color if state['announce_pressed'] else self.normal_color)
        
        # Lights buttons
        self.exterior_lights_btn.configure(bg=self.active_color if state['exterior_lights'] else self.normal_color)
        self.interior_lights_btn.configure(bg=self.active_color if state['interior_lights'] else self.normal_color)
        
        # Manual mode button - Only update color, state is handled in update_button_enabled_states
        bg_color = self.active_color if state['manual_mode'] else self.normal_color
        self.manual_mode_btn.configure(bg=bg_color)
        current_state = self.manual_mode_btn['state']
        print(f"[DEBUG update_button_states] Manual mode button: bg={bg_color}, current state={current_state}")
        
        # Brake buttons - Only update colors, states are handled in update_button_enabled_states
        self.service_brake_btn.configure(bg=self.active_color if state['service_brake'] > 0 else self.normal_color)
        self.emergency_brake_btn.configure(bg=self.active_color if state['emergency_brake'] else self.normal_color)
    
    # Control methods
    def set_driver_speed(self):
        """Set driver speed from text input."""
        try:
            desired_speed = float(self.speed_entry.get())
            
            # Get current state for limits
            state = self.api.get_state()
            commanded_speed = self.controller.cmd_speed_auth.commanded_speed
            speed_limit = state['speed_limit']
            
            # Apply same limiting logic as update_speed
            if state.get('manual_mode', False) or commanded_speed == 0:
                max_allowed_speed = speed_limit if speed_limit > 0 else 100
            else:
                max_allowed_speed = min(commanded_speed, speed_limit) if speed_limit > 0 else commanded_speed
            
            # Clamp the speed to valid range
            new_speed = max(0, min(max_allowed_speed, desired_speed))
            
            # Calculate new power command with new speed
            state_copy = state.copy()
            state_copy['driver_velocity'] = new_speed
            power = self.controller.calculate_power_command(state_copy)
            
            # Apply changes through vital validation
            self.controller.vital_control_check_and_update({
                'driver_velocity': new_speed,
                'power_command': power
            })
            
            # Update the entry to show the actual set value (in case it was clamped)
            self.speed_entry.delete(0, tk.END)
            self.speed_entry.insert(0, f"{new_speed:.1f}")
            
        except ValueError:
            # If invalid input, reset to current driver velocity
            state = self.api.get_state()
            self.speed_entry.delete(0, tk.END)
            self.speed_entry.insert(0, f"{state['driver_velocity']:.1f}")
    
    def toggle_left_door(self):
        """Toggle left door state."""
        self.controller.toggle_door('left')
    
    def toggle_right_door(self):
        """Toggle right door state."""
        self.controller.toggle_door('right')
    
    def toggle_exterior_lights(self):
        """Toggle exterior lights state."""
        self.controller.toggle_exterior_lights()
    
    def toggle_interior_lights(self):
        """Toggle interior lights state."""
        self.controller.toggle_interior_lights()
    
    def toggle_announcement(self):
        """Toggle announcement state."""
        state = self.api.get_state()
        self.controller.set_announcement(not state['announce_pressed'])
    
    def toggle_manual_mode(self):
        """Toggle manual/automatic mode."""
        print("[UI] Manual mode button clicked!")
        current_state = self.api.get_state()
        print(f"[UI] Current manual_mode state: {current_state.get('manual_mode', False)}")
        self.controller.toggle_manual_mode()
        new_state = self.api.get_state()
        print(f"[UI] New manual_mode state: {new_state.get('manual_mode', False)}")
        
    def temp_up(self):
        """Increase desired temperature setpoint."""
        self.controller.adjust_temperature(increase=True)
    
    def temp_down(self):
        """Decrease desired temperature setpoint."""
        self.controller.adjust_temperature(increase=False)
    
    def toggle_service_brake(self):
        """Toggle service brake state."""
        state = self.api.get_state()
        self.controller.set_service_brake(state['service_brake'] == 0)
    
    def emergency_brake(self):
        """Toggle emergency brake on/off."""
        state = self.api.get_state()
        current_brake_state = state.get('emergency_brake', False)
        self.controller.set_emergency_brake(not current_brake_state)
    
    def release_emergency_brake(self):
        """Manually release the emergency brake."""
        self.controller.set_emergency_brake(False)
    
    def lock_engineering_values(self):
        """Lock Kp and Ki values."""
        try:
            kp = float(self.kp_entry.get())
            ki = float(self.ki_entry.get())
            
            self.api.update_state({
                'kp': kp,
                'ki': ki,
                'engineering_panel_locked': True
            })
            
            # Disable inputs
            self.kp_entry.configure(state="disabled")
            self.ki_entry.configure(state="disabled")
            self.lock_btn.configure(state="disabled")
            
        except ValueError:
            tk.messagebox.showerror("Error", "Kp and Ki must be valid numbers")

if __name__ == "__main__":
    app = train_controller_ui()
    app.mainloop()



