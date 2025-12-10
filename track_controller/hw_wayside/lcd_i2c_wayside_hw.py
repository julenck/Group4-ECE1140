"""
Minimal 16x2 I²C LCD helper for Raspberry Pi.

Fails soft on non-Pi so dev laptops can run without hardware.

Author: Oliver Kettleson-Belinkie, 2025
"""

from __future__ import annotations

import os
import time
import logging

LOG = logging.getLogger("lcd_i2c")

# Allow delays to avoid issues with lag
_LCD_DELAY = float(os.getenv("LCD_INIT_DELAY", "0.01"))
try:
    from smbus2 import SMBus
except Exception:  # not on a Pi
    SMBus = None

class I2CLcd:
    def __init__(self, bus: int = 1, addr: int = 0x27):     # default I2C address 0x27

        self.addr = addr
        self.bus = None
        self.backlight = 0x08 

        if SMBus:
            try:
                self.bus = SMBus(bus)
            
                try:
                    self._init()
                    LOG.info("I2C LCD initialized at 0x%02x on bus %s", addr, bus)

                except Exception as e:
                    LOG.warning("LCD init failed: %s", e)
                    self.bus = None     # fail soft if init fails

            except Exception:
                self.bus = None  # fail soft

    def _write4(self, data: int, rs: int):

        if not self.bus:
            return
        
        en = 0x04
        packet = (data & 0xF0) | rs | self.backlight
        self.bus.write_byte(self.addr, packet | en)
        self.bus.write_byte(self.addr, packet)
        
        time.sleep(max(0.001, _LCD_DELAY))

    def _send(self, value: int, rs: int):

        self._write4(value, rs)
        self._write4(value << 4, rs)

    def _command(self, cmd: int):

        self._send(cmd, rs=0)

    def _char(self, ch: int):

        self._send(ch, rs=1)

    def _init(self):
        
        self._write4(0x03 << 4, rs=0)
        time.sleep(_LCD_DELAY * 5)
        self._write4(0x03 << 4, rs=0)
        time.sleep(_LCD_DELAY * 5)
        self._write4(0x02 << 4, rs=0)   # Set 4-bit mode
        time.sleep(_LCD_DELAY * 2)
        self._command(0x28)             # 2 lines, 5x8 font
        time.sleep(_LCD_DELAY)
        self._command(0x0C)             # Display on, cursor off
        time.sleep(_LCD_DELAY)
        self._command(0x06)             # Entry mode set
        time.sleep(_LCD_DELAY)
        self.clear()
        time.sleep(_LCD_DELAY)

    def present(self) -> bool:      # Check if LCD is present
        
        return self.bus is not None

    def clear(self):                # Clear display
       
        self._command(0x01)

    def set_cursor(self, row: int, col: int):       # Set cursor position
       
        row = 0 if row <= 0 else 1
        addr = 0x80 + (0x40 * row) + col
        self._command(addr)

    def write_line(self, row: int, text: str):      # Write text to a specific line
    
        text = (text or "")[:16].ljust(16)
        self.set_cursor(row, 0)

        for c in text:
            self._char(ord(c))

    def show_speed_auth(self, block_id: str, speed_mph: float, auth_yds: float):
        
        # Format: Line1: "B77 10mph A:100yd"
        block_str = str(block_id)[:3]
        line1 = f"B{block_str} {int(speed_mph):2}mph A:{int(auth_yds):3}y"
        line2 = f"Auth:{int(auth_yds):>4} yards"

        self.write_line(0, line1[:16])
        self.write_line(1, line2[:16])