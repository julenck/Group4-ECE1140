"""
Minimal 16x2 I²C LCD helper for Raspberry Pi (PCF8574 backpacks at 0x27).
Fails soft on non-Pi so dev laptops can run without hardware.
"""

from __future__ import annotations

import os
import time
import logging

LOG = logging.getLogger("lcd_i2c")

# Allow tuning init/write delays via env for stubborn hardware
_LCD_DELAY = float(os.getenv("LCD_INIT_DELAY", "0.01"))
try:
    from smbus2 import SMBus
except Exception:  # not on a Pi or smbus2 not installed
    SMBus = None  # type: ignore


class I2CLcd:
    def __init__(self, bus: int = 1, addr: int = 0x27):
        self.addr = addr
        self.bus = None
        self.backlight = 0x08  # backlight on
        if SMBus:
            try:
                self.bus = SMBus(bus)
                # Try a robust init sequence; catch failures and fail soft
                try:
                    self._init()
                    LOG.info("I2C LCD initialized at 0x%02x on bus %s", addr, bus)
                except Exception as e:
                    LOG.warning("LCD init failed: %s", e)
                    # if init failed, mark as not present to avoid later errors
                    self.bus = None
            except Exception:
                self.bus = None  # fail soft

    # ---------------- LCD low-level (HD44780 4-bit) ----------------

    def _write4(self, data: int, rs: int):
        if not self.bus:
            return
        en = 0x04
        packet = (data & 0xF0) | rs | self.backlight
        self.bus.write_byte(self.addr, packet | en)
        self.bus.write_byte(self.addr, packet)
        # small pause to avoid garbled output on slow backpacks
        time.sleep(max(0.001, _LCD_DELAY))

    def _send(self, value: int, rs: int):
        self._write4(value, rs)
        self._write4(value << 4, rs)

    def _command(self, cmd: int):
        self._send(cmd, rs=0)

    def _char(self, ch: int):
        self._send(ch, rs=1)

    def _init(self):
        # init sequence for 4-bit mode
        # Common robust sequence: send 0x03/0x03/0x02 then function set
        # (many HD44780 guides use 0x33/0x32 but we use nibble writes here)
        self._write4(0x03 << 4, rs=0)
        time.sleep(_LCD_DELAY * 5)
        self._write4(0x03 << 4, rs=0)
        time.sleep(_LCD_DELAY * 5)
        self._write4(0x02 << 4, rs=0)  # set 4-bit mode
        time.sleep(_LCD_DELAY * 2)
        self._command(0x28)       # 2 lines, 5x8 font
        time.sleep(_LCD_DELAY)
        self._command(0x0C)       # display on, cursor off
        time.sleep(_LCD_DELAY)
        self._command(0x06)       # entry mode set
        time.sleep(_LCD_DELAY)
        self.clear()
        time.sleep(_LCD_DELAY)

    # ---------------- Friendly API ----------------

    def present(self) -> bool:
        return bool(self.bus)

    def clear(self):
        self._command(0x01)

    def set_cursor(self, row: int, col: int):
        row = 0 if row <= 0 else 1
        addr = 0x80 + (0x40 * row) + col
        self._command(addr)

    def write_line(self, row: int, text: str):
        text = (text or "")[:16].ljust(16)
        self.set_cursor(row, 0)
        for c in text:
            self._char(ord(c))

    def show_speed_auth(self, block_id: str, speed_mph: float, auth_yds: float):
        l1 = f"Blk {str(block_id):<3} Spd {int(speed_mph):>2} mph"
        l2 = f"Auth {int(auth_yds):>3} yd"
        self.write_line(0, l1)
        self.write_line(1, l2)