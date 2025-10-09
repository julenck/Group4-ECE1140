#Train Controller Hardware UI
#James Struyk


#import tkinter and related libraries
import tkinter as tk
from tkinter import ttk
import os
import sys
import time

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
            #"service_brake_button": 5, #temp replacement for pot issue
            #"service_brake_status_led": 16, #temp replacement for pot issue
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
        statuses = ["Lights", "Left Door", "Right Door", "Announcement", "Service Brake", "Emergency Brake"]

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
            # Initialize LCD if available    
            try:
                if self.i2c_devices.get('lcd', False) and self.i2c_bus:
                    self.lcd_address = self.i2c_address['lcd']
                    self.lcd_backlight = 0x08
                    self.LCD_RS = 0x01
                    self.LCD_RW = 0x02
                    self.LCD_EN = 0x04
                    self.lcd_write_cmd(0x33)
                    self.lcd_write_cmd(0x32)
                    self.lcd_write_cmd(0x28)
                    self.lcd_write_cmd(0x0C)
                    self.lcd_write_cmd(0x06)
                    self.lcd_write_cmd(0x01)
                    print("I2C LCD Initialized")
            except Exception as e:
                print(f"I2C LCD Initialization Error: {e}")
            # Initialize 4-Digit 7-segment display if available
            try:
                if self.i2c_devices.get('seven_segment', False) and self.i2c_bus:
                    self.seven_segment_address = self.i2c_address['seven_segment']
                    self.i2c_bus.write_byte(self.seven_segment_address, 0x21)
                    self.i2c_bus.write_byte(self.seven_segment_address, 0x81)
                    self.i2c_bus.write_byte(self.seven_segment_address, 0xE0 | 8)
                    self.seven_segment_present = True
                    print("I2C 7-Segment Display Initialized")
                else:
                    self.seven_segment_present = False
            except Exception as e:
                self.seven_segment_present = False
                print(f"I2C 7-Segment Initialization Error: {e}")
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
            elif name == "service_brake_button": #temp replacement for pot issue
                current = self.api.get_state().get('service_brake', False)
                self.api.update_state({'service_brake': not current})
            elif name == "emergency_brake_button":
                self.api.update_state({'emergency_brake': True})
                self.after(5000, lambda: self.api.update_state({'emergency_brake': False}))
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

            try:
                if I2C_AVAILABLE and self.i2c_devices.get('lcd', False) and self.i2c_bus:
                    cmd_speed = state.get('commanded_speed', 0.0)
                    cmd_auth = state.get('commanded_authority', 0.0)
                    line0 = f"CmdSped:{cmd_speed:5.1f}mph"
                    line1 = f"CmdAuth:{cmd_auth:5.1f}yds"
                    self.lcd_write_line(line0, line=0, width=16)
                    self.lcd_write_line(line1, line=1, width=16)
            except Exception as e:
                print(f"I2C LCD Update Error: {e}")

            try:
                if I2C_AVAILABLE and getattr(self, 'seven_segment_present', False) and self.i2c_bus:
                    self.seven_segment_display_set_speed(state.get('set_speed', 0))
            except Exception as e:
                print(f"I2C 7-Segment Update Error: {e}")

        except Exception as e:
            print(f"Periodic Update Error: {e}")
        finally:
            self.after(self.update_interval, self.periodic_update)

    def read_and_update_adc_api(self):
        if (not I2C_AVAILABLE) or (not self.i2c_devices.get('adc', False)) or (not self.i2c_bus):
            return
        try:
            addr = self.i2c_address['adc']

            def _read_ads1115_single_ended(channel, pga_bits=0x0200, fsr=4.096):
                """Single-shot read from ADS1115 single-ended channel.
                Returns (voltage, raw_code).
                pga_bits should be the PGA setting (bits shifted into bits 11:9).
                fsr is the full-scale range in volts corresponding to pga_bits.
                """
                OS_SINGLE = 0x8000
                MUX_BASE = {0: 0x4000, 1: 0x5000, 2: 0x6000, 3: 0x7000}
                MODE_SINGLE = 0x0100
                DR_128 = 0x0080
                COMP_QUE_DISABLE = 0x0003

                mux = MUX_BASE.get(channel, 0x4000)
                config = OS_SINGLE | mux | pga_bits | MODE_SINGLE | DR_128 | COMP_QUE_DISABLE
                hi = (config >> 8) & 0xFF
                lo = config & 0xFF
                self.i2c_bus.write_i2c_block_data(addr, 0x01, [hi, lo])
                # wait for conversion: 128SPS -> ~7.8ms
                time.sleep(0.01)
                data = self.i2c_bus.read_i2c_block_data(addr, 0x00, 2)
                raw = (data[0] << 8) | data[1]
                # convert to signed 16-bit (should be non-negative for single-ended)
                if raw & 0x8000:
                    raw -= 1 << 16
                # convert raw -> voltage using full-scale range
                voltage = (raw / 32767.0) * fsr
                # clamp to 0..fsr for safety
                voltage = max(0.0, min(voltage, fsr))
                return voltage, raw
            
            PGA_4_096_BITS = 0x0200
            FSR_4_096 = 4.096

            v0, raw0 = _read_ads1115_single_ended(0, pga_bits=PGA_4_096_BITS, fsr=FSR_4_096)
            v1, raw1 = _read_ads1115_single_ended(1, pga_bits=PGA_4_096_BITS, fsr=FSR_4_096)
            v3, raw3 = _read_ads1115_single_ended(3, pga_bits=PGA_4_096_BITS, fsr=FSR_4_096)

            # compute ratio relative to the actual pot supply (3.3V)
            V_POT = 3.3
            ratio0 = max(0.0, min(1.0, v0 / V_POT))
            ratio1 = max(0.0, min(1.0, v1 / V_POT))
            ratio3 = max(0.0, min(1.0, v3 / V_POT))

            state = self.api.get_state()
            commanded_speed = state.get('commanded_speed', 0.0)
            set_speed = round(ratio0 * commanded_speed, 2)
            set_temp = int(round(55 + (ratio1 * 40)))
            service_brake = int(round(ratio3 * 100))

            # build updated state and compute power using updated set_speed
            new_state = state.copy()
            new_state['set_speed'] = set_speed
            new_state['set_temperature'] = set_temp
            new_state['service_brake'] = service_brake

            power = self.calculate_power_command(new_state)

            self.api.update_state({
                'set_speed': set_speed,
                'set_temperature': set_temp,
                'service_brake': service_brake,
                'power_command': power
            })
        except Exception as e:
            print(f"ADC Read Error: {e}")

    def update_status_indicators(self, state):
        mapping = {
            "Lights": bool(state.get('lights', False)),
            "Left Door": bool(state.get('left_door', False)),
            "Right Door": bool(state.get('right_door', False)),
            "Announcement": bool(state.get('announcement', '')),
            "Service Brake": bool(state.get('service_brake', 0) > 0), #active if >0%
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
    
    def lcd_write_cmd(self, cmd):
        try:
            high = cmd & 0xF0
            low = (cmd << 4) & 0xF0
            self.lcd_write4bits(high)
            self.lcd_write4bits(low)
        except Exception as e:
            print(f"LCD Write Command Error: {e}")
    
    def lcd_write4bits(self, data):
        self.lcd_expander_write(data)
        self.lcd_pulse_enable(data)

    def lcd_expander_write(self, data):
        try:
            self.i2c_bus.write_byte(self.lcd_address, data | self.lcd_backlight)
        except Exception as e:
            print(f"LCD Expander Write Error: {e}")

    def lcd_pulse_enable(self, data):
        self.lcd_expander_write(data | self.LCD_EN)
        self.after(1, lambda: self.lcd_expander_write(data & ~self.LCD_EN))

    def lcd_write_char(self, char):
        try:
            val = ord(char)
            mode = self.LCD_RS
            high = (val & 0xF0) | mode
            low = (val << 4) & 0xF0 | mode
            self.lcd_write4bits(high)
            self.lcd_write4bits(low)
        except Exception as e:
            print(f"LCD Write Char Error: {e}")

    def lcd_clear(self):
        try:
            self.lcd_write_cmd(0x01)  # Clear display command
        except Exception as e:
            print(f"LCD Clear Error: {e}")

    def lcd_set_cursor(self, line):
        try:
            addr = 0x80 if line == 0 else 0xC0
            self.lcd_write_cmd(addr)
        except Exception as e:
            print(f"LCD Set Cursor Error: {e}")

    def lcd_write_line(self, text, line=0, width=16):
        try:
            s = str(text)[:width].ljust(width)
            self.lcd_set_cursor(line)
            for char in s:
                self.lcd_write_char(char)
        except Exception as e:
            print(f"LCD Write Line Error: {e}")

    def seven_segment_raw_write(self, data):
        try:
            if len(data) != 16:
                data = (data + [0]*16)[:16]
            self.i2c_bus.write_i2c_block_data(self.seven_segment_address, 0x00, data)
        except Exception as e:
            print(f"7-Segment Raw Write Error: {e}")

    def seven_segment_for_digit(self, ch):
        digits = {
            '0' : 0x3F, '1' : 0x06,
            '2' : 0x5B, '3' : 0x4F,
            '4' : 0x66, '5' : 0x6D,
            '6' : 0x7D, '7' : 0x07,
            '8' : 0x7F, '9' : 0x6F,
            '-' : 0x40, ' ' : 0x00
        }
        return digits.get(ch, 0x00)
    
    def seven_segment_display_digits(self, digits):
        data = [0] * 16
        for i in range(4):
            seg = self.seven_segment_for_digit(digits[i])
            data[i*2] = seg
        self.seven_segment_raw_write(data)

    def seven_segment_display_set_speed(self, speed):
        try:
            ival = int(round(speed))
        except Exception:
            ival = 0
        if ival > 9999:
            ival = 9999
        s = str(abs(ival)).rjust(4, ' ')
        if ival < 0:
            s = '-' + s[1:]
        self.seven_segment_display_digits(s)

    def seven_segment_clear(self):
        try:
            self.seven_segment_raw_write([0]*16)
        except Exception as e:
            print(f"7-Segment Clear Error: {e}")

if __name__ == "__main__":
    app = hw_train_controller_ui()
    app.mainloop()