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

        self.debounce_time = 50 # milliseconds
        self.last_button_press = {}

    def init_hardware(self):
        if GPIOZERO_AVAILABLE:
            try:
                for name, pin in self.gpio_pins.items():
                    # convention: *_button and *_status_led keys in gpio_pins
                    if name.endswith("_status_led"):
                        try:
                            self.gpio_leds[name] = LED(pin)
                        except Exception as e:
                            print(f"Failed to create LED for {name} pin {pin}: {e}")
                    elif name.endswith("_button"):
                        try:
                            btn = Button(pin)
                            # store and wire press to debounced handler
                            self.gpio_buttons[name] = btn
                            btn.when_pressed = lambda n=name: self._debounced_button(n)
                        except Exception as e:
                            print(f"Failed to create Button for {name} pin {pin}: {e}")
                print("GPIO init complete. Buttons:", list(self.gpio_buttons.keys()), "LEDs:", list(self.gpio_leds.keys()))
            except Exception as e:
                print(f"gpiozero Initialization Error: {e}")
        else:
            print("gpiozero not available. Running in simulation mode.")

        if I2C_AVAILABLE:
            try:
                self.i2c_bus = SMBus(self.i2c_bus_num)
                # simple device presence assumption based on provided addresses
                if self.i2c_address.get("adc"):
                    self.i2c_devices["adc"] = True
                if self.i2c_address.get("lcd"):
                    self.i2c_devices["lcd"] = True
                if self.i2c_address.get("seven_segment"):
                    self.i2c_devices["seven_segment"] = True

                self.lcd_address = self.i2c_address.get("lcd")
                self.seven_segment_address = self.i2c_address.get("seven_segment")
                print("I2C init complete. Devices:", self.i2c_devices)
            except Exception as e:
                print(f"I2C Initialization Error: {e}")
        else:
            print("I2C library not available. Running in simulation mode.")

    def _debounced_button(self, name: str):
        """Software debounce guard: ignore button events within _debounce_ms of the last one."""
        try:
            now = time.time()
            last = self.last_button_press.get(name, 0.0)
            if (now - last) * 1000.0 < self.debounce_time:
                # ignored as bounce
                # optional: print for debug
                # print(f"Debounced press ignored: {name}")
                return
            self.last_button_press[name] = now
            # forward to main handler
            self.gpio_button_pressed(name)
        except Exception as e:
            print(f"_debounced_button error for {name}: {e}")

    def gpio_button_pressed(self, name):
        """Handle a gpiozero button press by logical name (e.g. 'exterior_lights_button')."""
        try:
            print(f"gpiozero Button pressed: {name}")
            # map button key to API state key (strip _button suffix)
            api_key = name.replace("_button", "")
            # special handling for vital buttons
            if api_key in ("service_brake", "emergency_brake"):
                # toggle current value via controller's vital path if controller present
                curr = bool(self.api.get_state().get(api_key, False))
                new_val = not curr
                if self.controller and hasattr(self.controller, "vital_control_check_and_update"):
                    # send via controller's validator path
                    ok = self.controller.vital_control_check_and_update({api_key: new_val})
                    if not ok:
                        print(f"Vital update rejected for {api_key}")
                else:
                    self.api.update_state({api_key: new_val})
            elif api_key == "mode":
                # let controller toggle mode (keeps consistent)
                if self.controller and hasattr(self.controller, "toggle_mode"):
                    self.controller.toggle_mode()
                else:
                    curr = bool(self.api.get_state().get("manual_mode", False))
                    self.api.update_state({"manual_mode": not curr})
            else:
                # non-vital toggles: update API directly
                curr = bool(self.api.get_state().get(api_key, False))
                self.api.update_state({api_key: not curr})

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

            # Build a tentative state for power calculation
            state = self.api.get_state()
            new_state = state.copy()
            new_state.update({
                'driver_velocity': set_speed,
                'set_temperature': set_temp
            })

            # Prefer controller to compute power_command if available (controller coordinates vitals)
            if hasattr(self, "controller") and self.controller and hasattr(self.controller, "calculate_power_command"):
                power = self.controller.calculate_power_command(new_state)
            else:
                # Fallback: simple default or 0.0
                power = 0.0

            # Route vital changes via controller when present (safer)
            vital_changes = {'driver_velocity': set_speed, 'power_command': power}
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
        try:
            self.lcd_expander_write(data | self.lcd_enable)
            if hasattr(self, 'ui') and getattr(self, 'ui', None) is not None:
                try:
                    # schedule on the UI thread if possible (non-blocking)
                    self.ui.after(1, lambda: self.lcd_expander_write(data & ~self.lcd_enable))
                    return
                except Exception:
                    # fall through to blocking sleep fallback
                    pass
            # fallback: tiny sleep then clear (safe for simple I2C timing)
            time.sleep(0.001)
            self.lcd_expander_write(data & ~self.lcd_enable)
        except Exception as e:
            print(f"LCD Pulse Enable Error: {e}")

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