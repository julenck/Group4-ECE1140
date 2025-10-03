#Train Controller Hardware Inputs
#James Struyk


#import related libraries
import RPi.GPIO as GPIO
import spidev
import time


class hardware_inputs:
    def __init__(self):
        #setup GPIO mode
        GPIO.setmode(GPIO.BCM)

        #setup SPI
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)  # Open SPI bus 0, device (CS) 0
        self.spi.max_speed_hz = 1350000  # Set SPI speed

        #setup GPIO pins for buttons and switches
        self.button_pins = {
            "emergency_brake": 17,
            "": 27,
            "lights": 22,
            "left_door": 5,
            "right_door": 6,
            "horn": 13
        }

        for pin in self.button_pins.values():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Buttons are active low