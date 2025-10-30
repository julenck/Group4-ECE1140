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

class train_controller_hardware:

    def __init__(self, ui, api, gpio_pins, i2c_bus_num, i2c_address, controller=None):
        self.ui = ui
        self.api = api
        self.gpio_pins = gpio_pins
        self.i2c_bus_num = i2c_bus_num
        self.i2c_address = i2c_address
        self.controller = controller

        self.i2c_bus = None
        self.i2c_devices = {"lcd": False, "adc": False, "seven_segment": False}
        self.gpio_buttons = {}
        self.gpio_leds = {}
        self.seven_segment_present = False

        self.lcd_address = None
        self.lcd_backlight = 0x08
        self.lcd_rs = 0x01 # Register select bit
        self.lcd_rw = 0x02 # Read/Write bit
        self.lcd_enable = 0x04 # Enable bit

    def init_hardware(self):
        if GPIOZERO_AVAILABLE:
            try:
                for name, pin in self.GPIO_PINS.items():
                    if "button" in name:
                        button = Button(pin, pull_up=True)
                        # small hold to reduce bounce impact
                        button.when_pressed = lambda n=name: self.gpio_button_pressed(n)
                        self.gpio_buttons[name] = button
                    elif "status_led" in name:
                        led = LED(pin)
                        led.off()
                        self.gpio_leds[name] = led
            except Exception as e:
                print(f"gpiozero Initialization Error: {e}")
        else:
            print("gpiozero not available. Running in simulation mode.")

        if I2C_AVAILABLE:
            try:
                self.i2c_bus = SMBus(self.i2c_bus_num)
                for name, addr in self.i2c_address.items():
                    try:
                        self.i2c_bus.read_byte(addr)
                        self.i2c_devices[name] = True
                    except Exception:
                        self.i2c_devices[name] = False
                if self.i2c_devices.get("lcd", False) and self.i2c_bus:
                    self.lcd_address = self.i2c_address["lcd"]
                    self.lcd_backlight = 0x08
                    self.lcd_rs = 0x01
                    self.lcd_rw = 0x02
                    self.lcd_enable = 0x04
                    self.lcd_write_cmd(0x33) # Initialize
                    self.lcd_write_cmd(0x32) # Set to 4-bit mode
                    self.lcd_write_cmd(0x28) # 2 line, 5x7 matrix
                    self.lcd_write_cmd(0x0C) # Turn cursor off
                    self.lcd_write_cmd(0x06) # Shift cursor right
                    self.lcd_write_cmd(0x01) # Clear display
                if self.i2c_devices.get("seven_segment", False) and self.i2c_bus:
                    self.seven_segment_address = self.i2c_address["seven_segment"]
                    self.i2c_bus.write_byte(self.seven_segment_address, 0x21)
                    self.i2c_bus.write_byte(self.seven_segment_address, 0x81)
                    self.i2c_bus.write_byte(self.seven_segment_address, 0xE0 | 8)
                    self.seven_segment_present = True
                    try:
                        self.seven_segment_raw_write([0] * 16)
                        self.seven_segment_display_set_speed(0)
                    except Exception as e:
                        print(f"I2C 7-Segment Setup Error: {e}")
                else:
                    self.seven_segment_present = False
            except Exception as e:
                print(f"I2C Initialization Error: {e}")
        else:
            print("I2C library not available. Running in simulation mode.")

    def gpio_button_pressed(self, name):
        """Handle a gpiozero button press by logical name (e.g. 'lights_button')."""
        try:
            print(f"gpiozero Button pressed: {name}")
            # Handle toggle buttons directly via API
            if name in ("lights_button", "left_door_button", "right_door_button", "announcement_button"):
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
                    # Toggle announce_pressed boolean (like SW UI) and update announcement text
                    announce_flag = self.api.get_state().get('announce_pressed', False)
                    self.api.update_state({
                        'announce_pressed': not announce_flag,
                        'announcement': '' if announce_flag else 'Next station approaching'
                    })
                return
            # Handle vital buttons via controller
            if self.controller:
                if name == "service_brake_button":
                    current = self.api.get_state().get('service_brake', False)
                    self.controller.vital_control_check_and_update({'service_brake': not current})
                elif name == "emergency_brake_button":
                    self.controller.vital_control_check_and_update({'emergency_brake': True})
                    self.after(5000, lambda: self.controller.vital_control_check_and_update({'emergency_brake': False}))
        except Exception as e:
            print(f"GPIO Callback Error: {e}")

    # ---------------------------------------------------------------------------
    #                             ADC Reading
    # ---------------------------------------------------------------------------

    def read_current_adc(self):
        if (not I2C_AVAILABLE) or (not self.i2c_devices.get('adc', False)) or (not self.i2c_bus):
            return
        try:
            # Read each ADC channel through dedicated helpers
            set_speed = self.set_driver_velocity_adc()
            set_temp = self.set_temperature_adc()
            service_brake = self.set_service_brake_adc()

            # Build a tentative state for power calculation
            state = self.api.get_state()
            new_state = state.copy()
            new_state.update({
                'set_speed': set_speed,
                'set_temperature': set_temp,
                'service_brake': service_brake
            })

            # Prefer controller to compute power_command if available (controller coordinates vitals)
            if hasattr(self, "controller") and self.controller and hasattr(self.controller, "calculate_power_command"):
                power = self.controller.calculate_power_command(new_state)
            else:
                # Fallback: simple default or 0.0
                power = 0.0

            # Route vital changes via controller when present (safer)
            vital_changes = {'set_speed': set_speed, 'service_brake': service_brake, 'power_command': power}
            if self.controller:
                self.controller.vital_control_check_and_update(vital_changes)
            else:
                # Fallback to direct API update (less safe)
                self.api.update_state(vital_changes)

            # Non‑vital update (temperature) can be written directly
            try:
                self.api.update_state({'set_temperature': set_temp})
            except Exception:
                pass
        except Exception as e:
            print(f"ADC Read Error: {e}")

    # Helpers: split ADC channel handling into single-purpose functions
    def _read_ads1115_single_ended(self, address, channel, pga_bits=0x0200, fsr=4.096):
        OS_SINGLE = 0x8000
        MUX_BASE = {0: 0x4000, 1: 0x5000, 2: 0x6000, 3: 0x7000}
        MODE_SINGLE = 0x0100
        DR_128 = 0x0080
        COMP_QUE_DISABLE = 0x0003

        mux = MUX_BASE.get(channel, 0x4000)
        config = OS_SINGLE | mux | pga_bits | MODE_SINGLE | DR_128 | COMP_QUE_DISABLE
        hi = (config >> 8) & 0xFF
        lo = config & 0xFF
        self.i2c_bus.write_i2c_block_data(address, 0x01, [hi, lo])
        time.sleep(0.01)
        data = self.i2c_bus.read_i2c_block_data(address, 0x00, 2)
        raw = (data[0] << 8) | data[1]
        if raw & 0x8000:
            raw -= 1 << 16
        voltage = (raw / 32767.0) * fsr
        voltage = max(0.0, min(voltage, fsr))
        return voltage, raw

    def set_driver_velocity_adc(self) -> float:
        """Read ADC channel for set_speed pot and convert to mph.
        Current mapping: ratio * commanded_speed (keeps scale similar to previous impl).
        """
        address = self.i2c_address.get('adc')
        if not address:
            return 0.0
        V_POT = 3.3
        try:
            v0, _ = self._read_ads1115_single_ended(address, 0)
            ratio0 = max(0.0, min(1.0, v0 / V_POT))
            commanded_speed = self.api.get_state().get('commanded_speed', 0.0)
            return round(ratio0 * commanded_speed, 2)
        except Exception as e:
            print(f"set_driver_velocity_adc error: {e}")
            return 0.0

    def set_temperature_adc(self) -> int:
        """Read ADC channel for temperature pot and convert to set_temperature (°F)."""
        address = self.i2c_address.get('adc')
        if not address:
            return 55
        try:
            v1, _ = self._read_ads1115_single_ended(address, 1)
            ratio1 = max(0.0, min(1.0, v1 / 3.3))
            return int(round(55 + (ratio1 * 40)))
        except Exception as e:
            print(f"set_temperature_adc error: {e}")
            return 55

    def set_service_brake_adc(self) -> int:
        """Read ADC channel for service_brake pot and convert to 0-100%."""
        address = self.i2c_address.get('adc')
        if not address:
            return 0
        try:
            v3, _ = self._read_ads1115_single_ended(address, 3)
            ratio3 = max(0.0, min(1.0, v3 / 3.3))
            return int(round(ratio3 * 100))
        except Exception as e:
            print(f"set_service_brake_adc error: {e}")
            return 0

# ---------------------------------------------------------------------------
#                                   LCD Helpers
# ---------------------------------------------------------------------------

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
        self.lcd_expander_write(data | self.lcd_enable)
        self.after(1, lambda: self.lcd_expander_write(data & ~self.lcd_enable))

    def lcd_write_char(self, char):
        try:
            val = ord(char)
            mode = self.lcd_rs
            high = (val & 0xF0) | mode
            low = (val << 4) & 0xF0 | mode
            self.lcd_write4bits(high)
            self.lcd_write4bits(low)
        except Exception as e:
            print(f"LCD Write Char Error: {e}")

    def lcd_clear(self):
        self.lcd_write_cmd(0x01)

    def lcd_set_cursor(self, line):
        address = 0x80 if line == 0 else 0xC0
        self.lcd_write_cmd(address)

    def lcd_write_line(self, text, line=0, width=16):
        try:
            s = str(text)[:width].ljust(width)
            self.lcd_set_cursor(line)
            for char in s:
                self.lcd_write_char(char)
        except Exception as e:
            print(f"LCD Write Line Error: {e}")

# ---------------------------------------------------------------------------
#                             7-Segment Helpers
# ---------------------------------------------------------------------------

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
        try:
            data = [0] * 16
            positions = [0, 2, 6, 8]
            s = str(digits).rjust(4)[:4]
            for i in range(4):
                ch = s[i]
                seg = self.seven_segment_for_digit(ch)
                data[positions[i]] = seg
            data[4] = data[4] & ~0x02
            self.seven_segment_raw_write(data)
        except Exception as e:
            print(f"7-Segment Display Digits Error: {e}")

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