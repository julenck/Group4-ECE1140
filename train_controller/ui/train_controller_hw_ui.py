#Train Controller Hardware UI
#James Struyk test


#import tkinter and related libraries
import tkinter as tk
from tkinter import ttk
import os
import sys
import time

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

#import API
from api.train_controller_api import train_controller_api
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
        self.validators = [VitalValidatorFirst(), VitalValidatorSecond()] # instantiate validators

    def init_hardware(self):
        try:
            self.hardware = train_controller_hardware(
                ui = self,
                api = self.api,
                gpio_pins = self.GPIO_PINS,
                i2c_bus_number = self.i2c_bus_number,
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
            kp = state.get('kp', 0.0),
            ki = state.get('ki', 0.0),
            train_velocity = state.get('train_velocity', 0.0),
            driver_velocity = changes.get('driver_velocity', state.get('driver_velocity', 0.0)),
            emergency_brake = changes.get('emergency_brake', state.get('emergency_brake', False)),
            service_brake = changes.get('service_brake', state.get('service_brake', False)),
            power_command = state.get('power_command', 0.0),
            commanded_authority = state.get('commanded_authority', 0.0),
            speed_limit = state.get('speed_limit', 0.0)
        )

        for v in self.validators:
            ok, reason = v.validate(candidate)
            if not ok:
                print(f"Vital validation failed: {reason}")
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
        driver_velocity = state['set_speed']
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

    #not yet completed (still just a placeholder from it #2 feedback)
    def emergency_brake_activated(self):
        current_state = self.api.get_state()
        # if emergency brake is active, decreease speed to 0
        # another way to do this is when e brake is active, disable usage of set speed potentiometer
        if current_state['emergency_brake']:
            self.api.update_state({'driver_velocity': 0, 'emergency_brake': True})
        else:
            self.api.update_state({'emergency_brake': False})

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
           2) Apply service_brake when commanded_authority indicates stopping
           3) Non-vital controls remain unchanged
        """
        try:
            if not self.is_automatic_mode():
                return

            # 1) Ensure driver_velocity follows commanded_speed (vital change via validator)
            cmd_speed = float(state.get('commanded_speed', 0.0))
            # Use controller's vital path to update vitals safely
            self.vital_control_check_and_update({'driver_velocity': cmd_speed})

            # 2) If authority is depleted (<= 0) request full service brake, otherwise release
            cmd_auth = float(state.get('commanded_authority', 0.0))
            current_sb = int(state.get('service_brake', 0))
            if cmd_auth <= 0 and current_sb == 0:
                # request braking (100% service brake)
                self.vital_control_check_and_update({'service_brake': True})
            elif cmd_auth > 0 and current_sb > 0:
                # release service brake when authority available again
                self.vital_control_check_and_update({'service_brake': False})
        except Exception as e:
            print(f"apply_automatic_controls error: {e}")

    def detect_failure_mode(self, curr: vital_train_controls, prev: vital_train_controls, dt: float):
        """Detect engine, brake, or signal failure based on temporal behavior."""
        # Engine failure: commanded power but no acceleration
        if curr.power_command > 0 and (curr.current_velocity - prev.current_velocity)/dt < 0.05:
            return "ENGINE_FAILURE"

        # Brake failure: braking command but not decelerating
        if (curr.service_brake or curr.emergency_brake) and \
           (prev.current_velocity - curr.current_velocity)/dt < 0.05:
            return "BRAKE_FAILURE"

        # Signal failure: stale or inconsistent authority/commanded speed
        if curr.authority <= 0 and curr.power_command > 0:
            return "SIGNAL_FAILURE"

        return None
    
    def handle_failure_mode(self, mode):
        if mode == "ENGINE_FAILURE":
            self.api.update_state({"power_command": 0})
        elif mode == "BRAKE_FAILURE":
            self.api.update_state({"emergency_brake": True})
        elif mode == "SIGNAL_FAILURE":
            self.api.update_state({"authority": 0, "power_command": 0})
        self.log_event(f"Failure detected: {mode}")

class train_controller_ui(tk.Tk):

    def __init__(self):
        super().__init__()


        #set window title and size
        self.title("Train Controller - Hardware Driver Interface")
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

        # Initialize API
        self.api = train_controller_api()

        # Defining button colors
        self.active_color = "#ff4444"
        self.inactive_color = "#dddddd"

        # Hardware configuration (GPIO pin mapping)
        self.GPIO_PINS = {
            "exterior_lights_button": 4,
            "exterior_lights_status_led": 13,
            # "interior_lights_button": NEED TO ASSIGN GPIO PIN
            # "interior_lights_status_led": NEED TO ASSIGN GPIO PIN
            "left_door_button": 17,
            "left_door_status_led": 19,
            "right_door_button": 27,
            "right_door_status_led": 26,
            "announcement_button": 22,
            "announcement_status_led": 20,
            #"service_brake_button": NEED TO ASSIGN NEW GPIO PIN
            #"service_brake_status_led": NEED TO ASSIGN NEW GPIO PIN
            "emergency_brake_button": 6,
            "emergency_brake_status_led": 21,
            #"mode_button": NEED TO ASSIGN GPIO PIN
            #"mode_status_led": NEED TO ASSIGN GPIO PIN
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
            ("Power Availability", "", "W"),
            ("Cabin Temperature", "", "F°"),
            ("Station Side", "", "Left/Right"),
            ("Next Station", "", "Station"),
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
        statuses = ["Interior Lights", "Exterior Lights", "Left Door", "Right Door", "Announcement", "Service Brake", "Emergency Brake", "Mode"]

        button_frame = ttk.Frame(status_frame)
        button_frame.pack(fill="x", padx=4, pady=6)

        for idx, status in enumerate(statuses):
            r = idx // 3
            c = idx % 3
            b = tk.Button(button_frame, text=status, width=22, height=3, 
                           bg="#f0f0f0", command=lambda: None)
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

        # Create controller instance and hook apply button to controller method
        self.controller = train_controller(
            ui = self,
            api = self.api,
            gpio_pins = self.GPIO_PINS,
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
            state = self.api.get_state()

            # Read ADC (potentiometer inputs) and update driver_velocity, temperature, service_brake
            if hasattr(self, 'hardware') and self.hardware:
                try:
                    self.hardware.read_current_adc()
                except Exception as e:
                    print(f"ADC read/update error: {e}")
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
                elif param == "Power Availability":
                    self.info_treeview.set(iid, "value", f"{state['power_command']:.1f}")
                elif param == "Cabin Temperature":
                    self.info_treeview.set(iid, "value", f"{state.get('train_temperature', 0):.1f}")
                elif param == "Station Side":
                    self.info_treeview.set(iid, "value", state.get('station_side', ''))
                elif param == "Next Station":
                    self.info_treeview.set(iid, "value", state.get('next_stop', ''))
                elif param == "Mode":
                    self.info_treeview.set(iid, "value", state.get('mode', ''))
                elif param == "Failure(s)":
                    failures = []
                    if state.get('engine_failure', False):
                        failures.append("Engine")
                    if state.get('signal_failure', False):
                        failures.append("Signal")
                    if state.get('brake_failure', False):
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
        mapping = {
            "Interior Lights": bool(state.get('interior_lights', False)),
            "Exterior Lights": bool(state.get('exterior_lights', False)),
            "Left Door": bool(state.get('left_door', False)),
            "Right Door": bool(state.get('right_door', False)),
            "Announcement": bool(state.get('announcement', '')),
            "Service Brake": bool(state.get('service_brake', False)),
            "Emergency Brake": bool(state.get('emergency_brake', False)),
            "Mode": not bool(state.get('manual_mode', False))  # True if automatic mode
        }
        for name, val in mapping.items():
            entry = self.status_buttons.get(name)
            if not entry:
                continue
            entry["active"] = val
            btn = entry["button"]
            if val:
                btn.config(bg=self.active_color, fg="white")
            else:
                btn.config(bg=self.inactive_color, fg="black")
            # If gpiozero LEDs are present, mirror status to physical LED
            try:
                if GPIOZERO_AVAILABLE and hasattr(self, 'gpio_leds'):
                    key = name.lower().replace(' ', '_') + "_status_led"
                    led = self.gpio_leds.get(key)
                    if led is not None:
                        if val:
                            led.on()
                        else:
                            led.off()
            except Exception as e:
                print(f"LED update error for {name}: {e}")

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
            self.apply_button.configure(state="disabled")
            
        except ValueError:
            tk.messagebox.showerror("Error", "Kp and Ki must be valid numbers")

class vital_train_controls:
    kp: float = 0.0
    ki: float = 0.0
    train_velocity: float = 0.0
    driver_velocity: float = 0.0
    emergency_brake: bool = False
    service_brake: bool = False
    power_command: float = 0.0
    commanded_authority: float = 0.0
    speed_limit: float = 0.0

class vital_validator:
    def validate(self, candidate: vital_train_controls) -> (bool, str):
        """Validate the given vital train controls.
        
        Args:
            vital_controls (vital_train_controls): The vital controls to validate.
        
        Returns:
            (bool, str): Tuple of (is_valid, reason). is_valid is True if valid, False otherwise.
                         reason is a string explaining the validation result.
        """
        raise NotImplementedError("Subclasses must implement validate method.")

class vital_control_first_check:
    def validate(self, v):
        if v.velocity > v.speed_limit:
            return False
        if v.power_command < 0 or v.power_command > 120000:
            return False
        if v.service_brake and v.emergency_brake:
            return False
        if v.commanded_authority <= 0 and v.power_command > 0:
            return False
        return True

class vital_control_second_check:
    def validate(self, v):
        # maybe slightly different implementation or thresholding
        safe_speed = v.speed_limit * 1.02  # allows 2% margin
        return (
            v.velocity <= safe_speed and
            not (v.service_brake and v.emergency_brake) and
            (v.commanded_authority > 0 or v.power_command == 0)
        )

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
    app = train_controller_ui()
    app.mainloop()