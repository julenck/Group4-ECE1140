#Train Controller Hardware UI
#James Struyk


#import tkinter and related libraries
import tkinter as tk
from tkinter import ttk
import os
import sys

try:
    from gpiozero import LED, Button
    GPIOZERO_AVAILABLE = True
except Exception:
    GPIOZERO_AVAILABLE = False

try:
    from smbus2 import SMBus
    I2C_AVAILABLE = True
except Exception:
    I2C_AVAILABLE = False

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

#import API
from api.train_controller_api import train_controller_api

class hw_train_controller_ui(tk.Tk):

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
            "lights_button": 4,
            "lights_status_led": 13,
            "left_door_button": 17,
            "left_door_status_led": 19,
            "right_door_button": 27,
            "right_door_status_led": 26,
            "announcement_button": 22,
            "announcement_status_led": 20,
            "horn_button": 5,
            "horn_status_led": 16,
            "emergency_brake_button": 6,
            "emergency_brake_status_led": 21,
        }

        # I2C configuration
        self.i2c_bus_number = 1
        self.i2c_address = {
            "lcd": 0x27,
            "adc": 0x48,
            "seven_segment": 0x70
        }

        self.i2c_bus = None
        self.i2c_devices = {
            "lcd": False,
            "adc": False,
            "seven_segment": False
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
        ]
        for param, val, unit in self.important_parameters:
            self.info_treeview.insert("", "end", values=(param, val, unit))

        #bottom left frame with status indicators
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill="x", padx=10, pady=(0,10))

        status_frame = ttk.Frame(bottom_frame)
        status_frame.pack(side="left", fill="both", expand=True)

        self.status_buttons = {}
        statuses = ["Lights", "Left Door", "Right Door", "Announcement", "Horn", "Emergency Brake"]

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

        # setting apply button to only be applied once
        self.apply_button = ttk.Button(engineering_frame, text="Apply", command=self.lock_engineering_values)
        self.apply_button.grid(row=2, column=0, columnspan=2, pady=(8,2), sticky="ew")

        # make layout responsive
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.init_hardware()

        self.update_interval = 500  # 500ms = 0.5 seconds
        self.after(self.update_interval, self.periodic_update)

    def init_hardware(self):
        if GPIOZERO_AVAILABLE:
            try:
                print("gpiozero initialization")
                # store gpiozero objects
                self.gpio_buttons = {}
                self.gpio_leds = {}
                for name, pin in self.GPIO_PINS.items():
                    if "button" in name:
                        btn = Button(pin, pull_up=True)
                        # small hold to reduce bounce impact
                        btn.when_pressed = lambda n=name: self.gpio_button_pressed(n)
                        self.gpio_buttons[name] = btn
                    elif "status_led" in name:
                        led = LED(pin)
                        led.off()
                        self.gpio_leds[name] = led
                print("gpiozero Initialized")
            except Exception as e:
                print(f"gpiozero Initialization Error: {e}")
        else:
            print("gpiozero not available. Running in simulation mode.")

        if I2C_AVAILABLE:
            try:
                self.i2c_bus = SMBus(self.i2c_bus_number)
                for name, addr in self.i2c_address.items():
                    try:
                        self.i2c_bus.read_byte(addr)
                        self.i2c_devices[name] = True
                        print(f"I2C Device {name} found at address {hex(addr)}")
                    except Exception:
                        self.i2c_devices[name] = False
                        print(f"I2C Device {name} NOT found at address {hex(addr)}")
                print("I2C Initialized")
            except Exception as e:
                print(f"I2C Initialization Error: {e}")
        else:
            print("I2C library not available. Running in simulation mode.")

    def gpio_button_pressed(self, name):
        """Handle a gpiozero button press by logical name (e.g. 'lights_button')."""
        try:
            print(f"gpiozero Button pressed: {name}")
            if name == "lights_button":
                current = self.api.get_state().get('lights', False)
                self.api.update_state({'lights': not current})
            elif name == "left_door_button":
                current = self.api.get_state().get('left_door', False)
                self.api.update_state({'left_door': not current})
            elif name == "right_door_button":
                current = self.api.get_state().get('right_door', False)
                self.api.update_state({'right_door': not current})
            elif name == "announcement_button":
                current = self.api.get_state().get('announcement', '')
                self.api.update_state({'announcement': '' if current else 'Next station approaching'})
            elif name == "horn_button":
                current = self.api.get_state().get('horn', False)
                self.api.update_state({'horn': not current})
            elif name == "emergency_brake_button":
                self.api.update_state({'emergency_brake': True})
        except Exception as e:
            print(f"GPIO Callback Error: {e}")

    def periodic_update(self):
        try:
            state = self.api.get_state()

            # Read ADC (potentiometer inputs) and update set_speed, temperature, service_brake
            self.read_and_update_adc_api()

            # Recalculate power command based on current state
            if not state['emergency_brake'] and state['service_brake'] == 0:
                power = self.calculate_power_command(state)
                if power != state['power_command']:
                    self.api.update_state({'power_command': power})
            else:
                # No power when brakes are active
                self.api.update_state({'power_command': 0})

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
                    self.info_treeview.set(iid, "value", f"{state['velocity']:.1f}")
                elif param == "Power Availability":
                    self.info_treeview.set(iid, "value", f"{state['power_command']:.1f}")
                elif param == "Cabin Temperature":
                    self.info_treeview.set(iid, "value", f"{state.get('train_temperature', 0):.1f}")
                elif param == "Station Side":
                    self.info_treeview.set(iid, "value", state.get('station_side', ''))
                elif param == "Next Station":
                    self.info_treeview.set(iid, "value", state.get('next_stop', ''))
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

        except Exception as e:
            print(f"Periodic Update Error: {e}")
        finally:
            self.after(self.update_interval, self.periodic_update)

    def read_and_update_adc_api(self):
        if (not I2C_AVAILABLE) or (not self.i2c_devices.get('adc', False)) or (not self.i2c_bus):
            return
        try:
            address = self.i2c_address['adc']
            try:
                data = self.i2c_bus.read_i2c_block_data(address, 0, 3)
                a0, a4, a7 = data[0], data[1], data[2]
                # Set speed bounded within 0 to commanded speed (max)
                state = self.api.get_state()
                commanded_speed = state.get('commanded_speed', 0)
                set_speed = round((a0 / 255.00) * commanded_speed, 2)
                power = self.calculate_power_command(state)
                self.api.update_state({
                    'set_speed': set_speed,
                    'power_command': power
                })
                # Temperature bounded within 55 to 95 F (honestly dont know what range to use, probably wrong)
                set_temp = int(55 + (a4 / 255.00) * 40)
                # Service brake bounded from 0% to 100%
                service_brake = int((a7 / 255.00) * 100)
                self.api.update_state({
                    'set_speed': set_speed,
                    'set_temperature': set_temp,
                    'service_brake': service_brake
                })
            except Exception:
                return
        except Exception as e:
            print(f"ADC Read Error: {e}")

    def update_status_indicators(self, state):
        mapping = {
            "Lights": bool(state.get('lights', False)),
            "Left Door": bool(state.get('left_door', False)),
            "Right Door": bool(state.get('right_door', False)),
            "Announcement": bool(state.get('announcement', '')),
            "Horn": bool(state.get('horn', False)),
            "Emergency Brake": bool(state.get('emergency_brake', False))
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
                    # map UI name to gpio_led key
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

    def calculate_power_command(self, state):
        """Calculate power command based on speed difference and Kp/Ki values."""
        # Get current values
        current_speed = state['velocity']
        driver_set_speed = state['set_speed']
        kp = state['kp']
        ki = state['ki']
        
        # Calculate speed error
        speed_error = driver_set_speed - current_speed
        
        # Calculate power command using PI control
        # P = Kp * error + Ki * ∫error dt
        # For simplicity, we're using a basic implementation
        power = (kp * speed_error) + (ki * speed_error * 0.5)  # 0.5 is dt
        
        # Ensure power is non-negative and within limits
        power = max(0, min(power, 120000))  # 120kW max power
        
        return power

if __name__ == "__main__":
    app = hw_train_controller_ui()
    app.mainloop()