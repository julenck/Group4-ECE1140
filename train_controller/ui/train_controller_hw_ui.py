#Train Controller Hardware UI
#James Struyk test


#import tkinter and related libraries
import tkinter as tk
from tkinter import ttk 
import os
import sys
import time
import argparse

try:
    from gpiozero import LED, Button # type: ignore
    GPIOZERO_AVAILABLE = True
except Exception:
    GPIOZERO_AVAILABLE = False

try:
    from smbus2 import SMBus # type: ignore
    I2C_AVAILABLE = True
except Exception:
    I2C_AVAILABLE = False

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# API imports will be done conditionally based on server_url parameter
#import hardware
from train_controller_hardware import train_controller_hardware

class train_controller:

    #define non-functional controls here, get them from the api with a function?!

    def __init__(self, ui, api, gpio_pins, i2c_bus_number, i2c_address):
        self.ui = ui
        self.api = api
        self.gpio_pins = gpio_pins
        self.i2c_bus_number = i2c_bus_number
        self.i2c_address = i2c_address
        self.hardware = None
        self.i2c_bus = None
        self.i2c_devices = {"lcd": False, "adc": False, "seven_segment": False}
        self.seven_segment_present = False
        self.gpio_leds = {}
        self.gpio_buttons = {}
        self.seven_segment_address = None
        self.lcd_address = None
        self.lcd_backlight = 0x08
        self.lcd_rs = 0x01
        self.lcd_rw = 0x02
        self.lcd_enable = 0x04
        self.validators = [vital_control_first_check(), vital_control_second_check()] # instantiate validators
        self._accumulated_error = 0  # PI controller accumulated error
        self._last_beacon_for_announcement = ""  # Track last beacon for auto-announcements

    def init_hardware(self):
        try:
            self.hardware = train_controller_hardware(
                ui = self.ui,
                api = self.api,
                gpio_pins = self.gpio_pins,
                i2c_bus_num = self.i2c_bus_number,
                i2c_address = self.i2c_address,
                controller = self # pass controller reference
            )
            self.hardware.init_hardware()

            self.i2c_bus = self.hardware.i2c_bus
            self.i2c_devices = self.hardware.i2c_devices
            self.seven_segment_present = getattr(self.hardware, 'seven_segment_present', False)
            self.gpio_leds = getattr(self.hardware, 'gpio_leds', {})
            self.gpio_buttons = getattr(self.hardware, 'gpio_buttons', {})
            self.seven_segment_address = getattr(self.hardware, 'seven_segment_address', None)
            self.lcd_address = getattr(self.hardware, 'lcd_address', None)
            self.lcd_backlight = getattr(self.hardware, 'lcd_backlight', 0x08)
            self.lcd_rs = getattr(self.hardware, 'lcd_rs', 0x01)
            self.lcd_rw = getattr(self.hardware, 'lcd_rw', 0x02)
            self.lcd_enable = getattr(self.hardware, 'lcd_enable', 0x04)
        except Exception as e:
            print(f"Hardware init error: {e}")

    def vital_control_check_and_update(self, changes: dict):
        """Run validators and apply vital changes to API only if accepted."""
        # build a vital_train_controls candidate from current state + changes
        state = self.api.get_state().copy()
        candidate = vital_train_controls(
            kp = changes.get('kp', state.get('kp', 0.0)),
            ki = changes.get('ki', state.get('ki', 0.0)),
            train_velocity = changes.get('train_velocity', state.get('train_velocity', 0.0)),
            driver_velocity = changes.get('driver_velocity', state.get('driver_velocity', 0.0)),
            emergency_brake = changes.get('emergency_brake', state.get('emergency_brake', False)),
            service_brake = changes.get('service_brake', state.get('service_brake', False)),
            power_command = changes.get('power_command', state.get('power_command', 0.0)),
            commanded_authority = changes.get('commanded_authority', state.get('commanded_authority', 0.0)),
            speed_limit = changes.get('speed_limit', state.get('speed_limit', 0.0))
        )

        for v in self.validators:
            if not v.validate(candidate):
                return False

        # validators passed -> commit only the requested vital fields
        self.api.update_state({k: v for k, v in changes.items()})
        return True
    
    # Control methods
    def calculate_power_command(self, state):
        """Calculate power command based on speed difference and Kp/Ki values.
        
        Implements PI control with:
        - Real-time accumulated error tracking
        - Anti-windup protection
        - Power limiting
        - Zero power when error is zero
        """
        # Get current values
        train_velocity = state['train_velocity']
        driver_velocity = state['driver_velocity']
        kp = state['kp']
        ki = state['ki']
        
        # Calculate speed error
        velocity_error = driver_velocity - train_velocity
        
        # If speed error is effectively zero (within small threshold), return zero power
        if abs(velocity_error) < 0.01:
            self._accumulated_error = 0
            return 0  # No power needed when at desired speed
        
        # Get current time
        current_time = time.time()  # WE MAY NEED VALUE FROM TIME CLASS HERE
        
        # Ensure time tracking variables exist
        if not hasattr(self, '_last_update_time'):
            self._last_update_time = current_time
        if not hasattr(self, '_accumulated_error'):
            self._accumulated_error = 0
            
        # Calculate real time step
        dt = current_time - self._last_update_time
        dt = max(0.001, min(dt, 1.0))  # Limit dt between 1ms and 1s for stability
        
        # Update accumulated error with anti-windup and scaling
        # Scale the error integration based on time step
        self._accumulated_error += velocity_error * dt
        
        # Anti-windup limits (scaled by ki to prevent excessive integral term)
        max_integral = 120000 / ki if ki != 0 else 0
        self._accumulated_error = max(-max_integral, min(max_integral, self._accumulated_error))
        
        # Calculate PI control output
        proportional = kp * velocity_error
        integral = ki * self._accumulated_error
        
        # Debug monitoring
        if hasattr(self, 'debug') and self.debug:
            print(f"Time: {current_time:.3f}, dt: {dt:.3f}")
            print(f"Speed Error: {velocity_error:.2f}, P: {proportional:.2f}, I: {integral:.2f}")
            print(f"Accumulated Error: {self._accumulated_error:.2f}")
        
        # Calculate total power command
        power = proportional + integral
        
        # Limit power
        power = max(0, min(power, 120000))  # 120kW max power
        
        # Anti-windup: adjust accumulated error when power saturates
        if power == 120000 and integral > 0:
            # Back-calculate integral term to match power limit
            self._accumulated_error = (120000 - proportional) / ki if ki != 0 else 0
        elif power == 0 and integral < 0:
            # Reset integral term when power is zero
            self._accumulated_error = -proportional / ki if ki != 0 else 0
        
        # Update last time for next iteration
        self._last_update_time = current_time
        
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

    def toggle_mode(self):
        """Flip manual/automatic mode flag in the API.

        - 'manual_mode' == True  -> manual
        - 'manual_mode' == False -> automatic
        """
        try:
            curr = self.api.get_state().get('manual_mode', False)
            new = not curr
            self.api.update_state({'manual_mode': new})
            print(f"Mode toggled: {'MANUAL' if new else 'AUTOMATIC'}")
            return new
        except Exception as e:
            print(f"toggle_mode error: {e}")
            return self.api.get_state().get('manual_mode', False)

    def is_automatic_mode(self) -> bool:
        """Return True when system is in automatic mode (manual_mode == False)."""
        try:
            return not bool(self.api.get_state().get('manual_mode', False))
        except Exception:
            return True

    def apply_automatic_controls(self, state: dict):
        """When in automatic mode:
           1) Use commanded_speed to set driver_velocity (vital)
           2) Regulate temperature to 70°F
           3) Auto-announce on beacon changes
        """
        try:
            updates = {}
            
            # Auto-set driver velocity to commanded speed
            if state['driver_velocity'] != state['commanded_speed']:
                updates['driver_velocity'] = state['commanded_speed']
            
            # Auto-regulate temperature to 70°F
            if state['set_temperature'] != 70.0:
                updates['set_temperature'] = 70.0
            
            # Apply updates if any
            if updates:
                self.api.update_state(updates)
                
        except Exception as e:
            print(f"apply_automatic_controls error: {e}")

    def calculate_power_command(self, state: dict) -> float:
        """Calculate power command using PI controller (same logic as SW controller)."""
        driver_velocity = state.get('driver_velocity', 0.0)
        current_velocity = state.get('train_velocity', 0.0)
        kp = state.get('kp', 5000.0)
        ki = state.get('ki', 500.0)
        
        error = driver_velocity - current_velocity
        self._accumulated_error += error * 0.5  # dt = 0.5 seconds
        
        # Anti-windup: limit accumulated error
        max_accumulated = 100.0
        self._accumulated_error = max(-max_accumulated, min(max_accumulated, self._accumulated_error))
        
        power = kp * error + ki * self._accumulated_error
        
        # Clamp power to valid range
        max_power = 120000.0  # 120 kW max
        power = max(0, min(max_power, power))
        
        return power

    def detect_and_respond_to_failures(self, state: dict):
        """Detect failures based on Train Model behavior and activate Train Controller failure flags.
        
        Logic:
        - Engine Failure: Only detected when power is applied but train doesn't accelerate
        - Signal Failure: Detected when beacon_read_blocked flag is set
        - Brake Failure: Only detected when service brake is pressed but train doesn't slow
        
        When detected, Train Controller activates corresponding train_controller_* flag and engages emergency brake.
        """
        updates = {}
        
        # Detect engine failure: Only when trying to apply power but train doesn't respond
        if state.get('train_model_engine_failure', False):
            # Detect if power command is significant (> 1000W) - driver is trying to accelerate
            power_applied = state.get('power_command', 0.0) > 1000.0
            
            if power_applied:
                if not state.get('train_controller_engine_failure', False):
                    print("[Train Controller] ENGINE FAILURE DETECTED - Power applied but train not responding! Engaging emergency brake")
                    updates['train_controller_engine_failure'] = True
        
        # Detect signal pickup failure: Only when Train Model blocks a beacon read
        if state.get('beacon_read_blocked', False):
            if not state.get('train_controller_signal_failure', False):
                print("[Train Controller] SIGNAL PICKUP FAILURE DETECTED - Failed to read beacon! Engaging emergency brake")
                updates['train_controller_signal_failure'] = True
                updates['beacon_read_blocked'] = False  # Clear the flag after detecting
        
        # Detect brake failure: Only detectable when service brake is pressed
        if state.get('train_model_brake_failure', False) and state.get('service_brake', False):
            if not state.get('train_controller_brake_failure', False):
                print("[Train Controller] BRAKE FAILURE DETECTED - Service brake not responding! Engaging emergency brake")
                updates['train_controller_brake_failure'] = True
                updates['emergency_brake'] = True  # Engage emergency brake immediately
        
        # Apply updates if any failures were detected/cleared
        if updates:
            self.api.update_state(updates)

class train_controller_ui(tk.Tk):

    def __init__(self, train_id=1, server_url=None, timeout=5.0):
        """Initialize the hardware driver interface.
        
        Args:
            train_id: Train ID for multi-train support. Defaults to 1.
            server_url: If provided, uses REST API client to connect to remote server.
                       If None, uses local file-based API (default).
                       Example: "http://192.168.1.100:5000"
            timeout: Network timeout in seconds for remote API (default: 5.0).
        """
        super().__init__()

        self.train_id = train_id
        self.server_url = server_url
        
        # Initialize API based on server_url parameter
        if server_url:
            # Remote mode - use client API
            from api.train_controller_api_client import train_controller_api_client
            self.api = train_controller_api_client(train_id=train_id, server_url=server_url, timeout=timeout)
            print(f"[HW UI] Using REMOTE API: {server_url} (timeout: {timeout}s)")
        else:
            # Local mode - use file-based API
            from train_controller.api.train_controller_api import train_controller_api
            self.api = train_controller_api(train_id=train_id)
            print(f"[HW UI] Using LOCAL API (file-based)")

        #set window title and size
        title = f"Train {train_id} - Hardware Controller" if train_id else "Train Controller - Hardware Driver Interface"
        if server_url:
            title += " [REMOTE]"
        self.title(title)
        self.geometry("1200x700")
        self.minsize(900, 600)

        # Setting font sizes for UI
        font_style = ("Sans Serif")
        tree_default_font = (font_style, 11)
        heading_font = (font_style, 15, "bold")
        tree_heading_font = (font_style, 13, "bold")

        style = ttk.Style(self)
        style.configure("TLabelframe.Label", font=heading_font)
        style.configure("Treeview.Heading", font=tree_heading_font)
        style.configure("Treeview", font=tree_default_font, rowheight=28)

        # Defining button colors
        self.active_color = "#ff4444"
        self.inactive_color = "#dddddd"

        # Hardware configuration (GPIO pin mapping)
        self.gpio_pins = {
            "exterior_lights_button": 4,
            "exterior_lights_status_led": 13,
            "interior_lights_button": 17,
            "interior_lights_status_led": 19,
            "left_door_button": 27,
            "left_door_status_led": 26,
            "right_door_button": 22,
            "right_door_status_led": 20,
            "announcement_button": 5,
            "announcement_status_led": 16,
            "service_brake_button": 25,
            "service_brake_status_led": 12,
            "emergency_brake_button": 6,
            "emergency_brake_status_led": 21, 
            "mode_button": 24, #need to wire
            "mode_status_led": 23 #need to wire
        }

        # I2C configuration
        self.i2c_bus_number = 1
        self.i2c_address = {
            "lcd": 0x27,
            "adc": 0x48,
            "seven_segment": 0x70
        }

        #main frame which shows important train information panel
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=6)

        info_panel_frame = ttk.LabelFrame(main_frame, text="Train Information Panel", padding=(8,8))
        info_panel_frame.pack(fill="both", expand=True, padx=(0,8))

        columns = ("parameter", "value", "unit")
        self.info_treeview = ttk.Treeview(info_panel_frame, columns=columns, show="headings")
        self.info_treeview.heading("parameter", text="Parameter")
        self.info_treeview.heading("value", text="Value")
        self.info_treeview.heading("unit", text="Unit")
        self.info_treeview.column("parameter", anchor="w", width=320)
        self.info_treeview.column("value", anchor="center", width=120)
        self.info_treeview.column("unit", anchor="center", width=80)
        self.info_treeview.pack(fill="both", expand=True)

        self.important_parameters = [
            ("Commanded Speed", "", "mph"),
            ("Commanded Authority", "", "yards"),
            ("Speed Limit", "", "mph"),
            ("Current Speed", "", "mph"),
            ("Driver Set Speed", "", "mph"),  # Add driver_velocity display
            ("Power Availability", "", "W"),
            ("Cabin Temperature", "", "F°"),
            ("Set Temperature", "", "F°"),  # Add set_temperature display
            ("Station Side", "", "Left/Right"),
            ("Next Station", "", "Station"),
            ("Announcement", "", ""),  # Add announcement row
            ("Failure(s)", "", "Type(s)"),
            ("Mode", "", "")
        ]
        for param, val, unit in self.important_parameters:
            self.info_treeview.insert("", "end", values=(param, val, unit))

        #bottom left frame with status indicators
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill="x", padx=10, pady=(0,10))

        status_frame = ttk.Frame(bottom_frame)
        status_frame.pack(side="left", fill="both", expand=True)

        self.status_buttons = {}
        statuses = ["Exterior Lights", "Interior Lights", "Left Door", "Right Door", "Announcement", "Service Brake", "Emergency Brake", "Mode"]

        button_frame = ttk.Frame(status_frame)
        button_frame.pack(fill="x", padx=4, pady=6)

        for idx, status in enumerate(statuses):
            r = idx // 3
            c = idx % 3
            # Create read-only display buttons (no command - hardware controlled)
            b = tk.Button(button_frame, text=status, width=22, height=3, 
                           bg="#f0f0f0", state="disabled", relief="raised")
            b.grid(row=r, column=c, padx=10, pady=8, sticky="nsew")
            button_frame.grid_columnconfigure(c, weight=1)
            self.status_buttons[status] = {"button": b, "active": False}

        #bottom right frame engineering panel
        engineering_frame = ttk.LabelFrame(bottom_frame, text="Engineering Panel", padding=(8,8))
        engineering_frame.pack(side="right", fill="y", ipadx=6)

        ttk.Label(engineering_frame, text="Kp:").grid(row=0, column=0, sticky="w", pady=(2,6))
        self.kp_var = tk.StringVar(value="0.0")
        self.kp_entry = ttk.Entry(engineering_frame, textvariable=self.kp_var, width=20)
        self.kp_entry.grid(row=0, column=1, pady=(2,6))

        ttk.Label(engineering_frame, text="Ki:").grid(row=1, column=0, sticky="w", pady=(2,6))
        self.ki_var = tk.StringVar(value="0.0")
        self.ki_entry = ttk.Entry(engineering_frame, textvariable=self.ki_var, width=20)
        self.ki_entry.grid(row=1, column=1, pady=(2,6))

        # Create controller instance and hook apply button to controller method
        self.controller = train_controller(
            ui = self,
            api = self.api,
            gpio_pins = self.gpio_pins,
            i2c_bus_number = self.i2c_bus_number,
            i2c_address = self.i2c_address
        )

        # setting apply button to only be applied once
        self.apply_button = ttk.Button(engineering_frame, text="Apply", command=self.lock_engineering_values)
        self.apply_button.grid(row=2, column=0, columnspan=2, pady=(8,2), sticky="ew")

        # make layout responsive
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        try:
            self.controller.init_hardware()
        except Exception as e:
            print(f"Controller hardware init error: {e}")

        self.update_interval = 500  # 500ms = 0.5 seconds
        self.after(self.update_interval, self.periodic_update)

    def periodic_update(self):
        try:
            # Only read from train_data.json in local mode (not when using remote server)
            if not self.server_url:
                self.api.update_from_train_data()
            
            state = self.api.get_state()
            
            # Detect failures based on Train Model behavior
            self.controller.detect_and_respond_to_failures(state)
            
            # Reload state after failure detection updates
            state = self.api.get_state()
            
            # Handle automatic vs manual mode behaviors
            manual_mode = state.get('manual_mode', False)
            
            if not manual_mode:  # Automatic mode
                # Auto-set driver velocity to commanded speed
                if state['driver_velocity'] != state['commanded_speed']:
                    self.api.update_state({'driver_velocity': state['commanded_speed']})
                    state = self.api.get_state()
                
                # Auto-regulate temperature to 70°F
                if state['set_temperature'] != 70.0:
                    self.api.update_state({'set_temperature': 70.0})
                    state = self.api.get_state()
                
                # Auto-announcement when beacon changes
                current_station = state.get('current_station', '')
                if current_station and current_station != self.controller._last_beacon_for_announcement:
                    # Beacon changed - make announcement
                    next_stop = state.get('next_stop', '')
                    if next_stop:
                        announcement = f"Next stop: {next_stop}"
                        self.api.update_state({'announcement': announcement})
                    self.controller._last_beacon_for_announcement = current_station
            else:  # Manual mode
                # Update beacon tracking even in manual mode
                current_station = state.get('current_station', '')
                if current_station:
                    self.controller._last_beacon_for_announcement = current_station
            
            # Auto-release emergency brake when velocity reaches 0
            if state['emergency_brake'] and state['train_velocity'] == 0.0:
                print("[Train Controller] Train stopped - Releasing emergency brake")
                self.controller.set_emergency_brake(False)
                state = self.api.get_state()
            
            # Check for critical failures that require emergency brake
            critical_failure = (state.get('train_controller_engine_failure', False) or 
                              state.get('train_controller_signal_failure', False) or 
                              state.get('train_controller_brake_failure', False))
            
            if critical_failure and not state['emergency_brake']:
                # Automatically engage emergency brake on critical failure
                self.controller.set_emergency_brake(True)
                state = self.api.get_state()

            # Read ADC (potentiometer inputs) ONLY in manual mode
            # In automatic mode, the controller sets these values automatically
            hw = getattr(self.controller, 'hardware', None)
            if manual_mode and hw and hw.i2c_devices.get('adc', False):
                try:
                    hw.read_current_adc()
                except Exception as e:
                    print(f"ADC read/update error: {e}")
            
            # Recalculate power command based on current state
            if (not state['emergency_brake'] and 
                state['service_brake'] == 0 and 
                not critical_failure):
                power = self.controller.calculate_power_command(state)
                if power != state['power_command']:
                    self.controller.vital_control_check_and_update({'power_command': power})
            else:
                # Reset accumulated error when brakes are active
                self.controller._accumulated_error = 0
                # No power when brakes are active or failures present
                self.controller.vital_control_check_and_update({
                    'power_command': 0,
                    'driver_velocity': 0
                })
            # try:
            # # Recalculate power command based on current state
            #     if not state['emergency_brake'] and state['service_brake'] == 0:
            #         power = self.calculate_power_command(state)
            #         if power != state['power_command']:
            #             self.api.update_state({'power_command': power})
            #     else:
            #         # No power when brakes are active
            #         self.api.update_state({'power_command': 0})
            # except Exception as e:
            #     print(f"Power command calculation error: {e}")

            # Reload state one final time before display to ensure all updates are reflected
            state = self.api.get_state()

            # Update important parameters in the treeview
            children = self.info_treeview.get_children()
            for iid in children:
                param = self.info_treeview.item(iid)["values"][0]
                if param == "Commanded Speed":
                    self.info_treeview.set(iid, "value", f"{state.get('commanded_speed', 0):.1f}")
                elif param == "Commanded Authority":
                    self.info_treeview.set(iid, "value", f"{state['commanded_authority']:.1f}")
                elif param == "Speed Limit":
                    self.info_treeview.set(iid, "value", f"{state['speed_limit']:.1f}")
                elif param == "Current Speed":
                    self.info_treeview.set(iid, "value", f"{state['train_velocity']:.1f}")
                elif param == "Driver Set Speed":
                    self.info_treeview.set(iid, "value", f"{state.get('driver_velocity', 0):.1f}")
                elif param == "Power Availability":
                    self.info_treeview.set(iid, "value", f"{state['power_command']:.1f}")
                elif param == "Cabin Temperature":
                    self.info_treeview.set(iid, "value", f"{state.get('train_temperature', 0):.1f}")
                elif param == "Set Temperature":
                    self.info_treeview.set(iid, "value", f"{state.get('set_temperature', 0):.1f}")
                elif param == "Station Side":
                    self.info_treeview.set(iid, "value", state.get('station_side', ''))
                elif param == "Next Station":
                    self.info_treeview.set(iid, "value", state.get('next_stop', ''))
                elif param == "Announcement":
                    # Display the announcement text
                    announcement = state.get('announcement', '')
                    display_text = announcement if announcement else "None"
                    self.info_treeview.set(iid, "value", display_text)
                elif param == "Mode":
                    mode_text = "Manual" if state.get('manual_mode', False) else "Automatic"
                    self.info_treeview.set(iid, "value", mode_text)
                elif param == "Failure(s)":
                    failures = []
                    if state.get('train_controller_engine_failure', False):
                        failures.append("Engine")
                    if state.get('train_controller_signal_failure', False):
                        failures.append("Signal")
                    if state.get('train_controller_brake_failure', False):
                        failures.append("Brake")
                    self.info_treeview.set(iid, "value", ", ".join(failures) if failures else "None")

            self.update_status_indicators(state)

            try:
                hw = getattr(self.controller, 'hardware', None)
                if I2C_AVAILABLE and hw and hw.i2c_devices.get('lcd', False) and hw.i2c_bus:
                    cmd_speed = state.get('commanded_speed', 0.0)
                    cmd_auth = state.get('commanded_authority', 0.0)
                    line0 = f"CmdSped:{cmd_speed:5.1f}mph"
                    line1 = f"CmdAuth:{cmd_auth:5.1f}yds"
                    hw.lcd_write_line(line0, line=0, width=16)
                    hw.lcd_write_line(line1, line=1, width=16)
            except Exception as e:
                print(f"I2C LCD Update Error: {e}")

            try:
                if I2C_AVAILABLE and hw and hw.i2c_devices.get('seven_segment', False) and hw.i2c_bus:
                    hw.seven_segment_display_set_speed(state.get('train_velocity', 0))
            except Exception as e:
                print(f"I2C 7-Segment Update Error: {e}")

        except Exception as e:
            print(f"Periodic Update Error: {e}")
        finally:
            self.after(self.update_interval, self.periodic_update)

    def update_status_indicators(self, state):
        # Get manual mode to determine button states
        manual_mode = state.get('manual_mode', False)
        emergency_brake_active = state.get('emergency_brake', False)
        
        # In automatic mode, all control buttons (except emergency brake and mode) are disabled
        # This matches the SW controller behavior exactly
        button_state_auto_disable = 'disabled' if not manual_mode else 'normal'
        
        mapping = {
            "Exterior Lights": bool(state.get('exterior_lights', False)),
            "Interior Lights": bool(state.get('interior_lights', False)),
            "Left Door": bool(state.get('left_door', False)),
            "Right Door": bool(state.get('right_door', False)),
            "Announcement": bool(state.get('announce_pressed', False)),
            "Service Brake": bool(state.get('service_brake', False)),
            "Emergency Brake": emergency_brake_active,
            "Mode": manual_mode  # True if manual mode
        }
        
        # Note: UI buttons are display-only (hardware GPIO buttons control the actual functions)
        # They stay disabled - only colors change to show state
        for name, val in mapping.items():
            entry = self.status_buttons.get(name)
            if not entry:
                continue
            entry["active"] = val
            btn = entry["button"]
            
            # Update colors to show state (buttons remain disabled - display only)
            if val:
                btn.config(bg=self.active_color, fg="white", disabledforeground="white")
            else:
                btn.config(bg=self.inactive_color, fg="black", disabledforeground="black")
            
            # Update Mode button text
            if name == "Mode":
                mode_text = "Manual" if manual_mode else "Automatic"
                btn.config(text=mode_text)
            # If gpiozero LEDs are present, mirror status to physical LED
            try:
                if GPIOZERO_AVAILABLE:
                    gpio_leds = getattr(self.controller, 'gpio_leds', {}) or {}
                    key = name.lower().replace(' ', '_') + "_status_led"
                    led = gpio_leds.get(key)
                    if led is not None:
                        if val:
                            led.on()
                        else:
                            led.off()
            except Exception as e:
                print(f"LED update error for {name}: {e}")

    def lock_engineering_values(self):
        """Lock Kp and Ki values - called when Apply button is pressed."""
        try:
            kp = float(self.kp_entry.get())
            ki = float(self.ki_entry.get())
            
            # Update API state with new values
            self.api.update_state({
                'kp': kp,
                'ki': ki,
                'engineering_panel_locked': True
            })
            
            # Disable inputs after locking
            self.kp_entry.configure(state="disabled")
            self.ki_entry.configure(state="disabled")
            self.apply_button.configure(state="disabled")
            
            print(f"[Engineering Panel] Locked - Kp={kp}, Ki={ki}")
            
        except ValueError:
            print("[Engineering Panel] Error: Kp and Ki must be valid numbers")

class vital_train_controls:
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
        self.velocity = train_velocity  # Alias for validators
        self.driver_velocity = driver_velocity
        self.emergency_brake = emergency_brake
        self.service_brake = service_brake
        self.power_command = power_command
        self.commanded_authority = commanded_authority
        self.speed_limit = speed_limit

class vital_control_first_check:
    def validate(self, v: vital_train_controls) -> bool:
        """Validate vital train controls (first check - hard rules).
        
        Args:
            v: The vital train controls to validate.
            
        Returns:
            True if validation passes, False otherwise.
        """
        # Check 1: Velocity must not exceed speed limit (if speed limit is set)
        if v.speed_limit > 0 and v.velocity > v.speed_limit:
            print(f"VALIDATION FAILED: Velocity {v.velocity} exceeds speed limit {v.speed_limit}")
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

class vital_control_second_check:
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
            if v.velocity > safe_speed:
                print(f"VALIDATION FAILED: Velocity {v.velocity} exceeds safe speed {safe_speed}")
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

class beacon:
    #define beacon attributes here, get them from the api with a function?!
    def __init__(self):
        self.next_stop = 'next_stop'
        self.station_side = 'station_side'

    def get_beacon_info_from_api(self):
        pass

class commanded_speed_authority:
    def __init__(self):
        self.commanded_speed = 'commanded_speed'
        self.commanded_authority = 'commanded_authority'

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Train Controller Hardware UI")
    parser.add_argument("--train-id", type=int, default=1, 
                       help="Train ID to control (default: 1)")
    parser.add_argument("--server", type=str, default=None,
                       help="Server URL for remote API (e.g., http://192.168.1.100:5000). If not provided, uses local file-based API.")
    parser.add_argument("--timeout", type=float, default=5.0,
                       help="Network timeout in seconds for remote API (default: 5.0)")
    args = parser.parse_args()
    
    print("=" * 70)
    print("  HARDWARE TRAIN CONTROLLER UI")
    print("=" * 70)
    print(f"  Train ID: {args.train_id}")
    if args.server:
        print(f"  Mode: REMOTE (Raspberry Pi)")
        print(f"  Server: {args.server}")
        print(f"  Timeout: {args.timeout}s")
    else:
        print(f"  Mode: LOCAL (file-based)")
    print("=" * 70)
    print()
    
    # Create and run app
    app = train_controller_ui(train_id=args.train_id, server_url=args.server, timeout=args.timeout)
    app.mainloop()