# SPDX-FileCopyrightText: Copyright (c) 2025 Cooper Dalrymple
# SPDX-License-Identifier: MIT
"""
`hardware.py`
================================================================================

Configure all of the hardware components of the pico_touch_synth

29 July 2025 - @relic_se / Cooper Dalrymple
"""

import board
import busio
import digitalio
import os

# Settings

SAMPLE_RATE = 44100
CHANNEL_COUNT = 2
BUFFER_SIZE = 2048

# MCU

import microcontroller
microcontroller.cpu.frequency = 180_000_000

is_rp2350 = 'rp2350' in os.uname()[0]

led = digitalio.DigitalInOut(board.LED)
led.switch_to_output()

# Pins

buttonA_pin = board.USER_SW
buttonB_pin = board.GP28
knobA_pin = board.A0 # GP26
knobB_pin = board.A1 # GP27
i2s_bck_pin = board.GP20
i2s_lck_pin = board.GP21
i2s_dat_pin = board.GP22
i2c_scl_pin   = board.GP19
i2c_sda_pin   = board.GP18
uart_rx_pin   = board.GP17
uart_tx_pin   = board.GP16

touch_pins = (
    board.GP0, board.GP1, board.GP2, board.GP3, board.GP4, board.GP5,
    board.GP6, board.GP7 ,board.GP8, board.GP9, board.GP10, board.GP11,
    board.GP12, board.GP13, board.GP14, board.GP15 )

# Audio

import audiobusio

audio = audiobusio.I2SOut(
    bit_clock=i2s_bck_pin,
    word_select=i2s_lck_pin,
    data=i2s_dat_pin,
)

# Controls

import keypad
import analogio

buttonA = keypad.Keys((buttonA_pin,), value_when_pressed=False, pull=False)
buttonB = keypad.Keys((buttonB_pin,), value_when_pressed=False, pull=True)

def check_buttons():
    """Check the touch inputs, return keypad-like Events"""
    events = []
    eventA = buttonA.events.get()
    if eventA:
        events.append(keypad.Event(0, eventA.pressed))
    eventB = buttonB.events.get()
    if eventB:
        events.append(keypad.Event(1, eventB.pressed))
    return events

knobA = analogio.AnalogIn(knobA_pin)
knobB = analogio.AnalogIn(knobB_pin)

# Display

import i2cdisplaybus
import displayio
import adafruit_displayio_ssd1306

DW,DH = 128,64
displayio.release_displays()

i2c = busio.I2C(
    scl=i2c_scl_pin,
    sda=i2c_sda_pin,
    frequency=1_000_000,
)
display_bus = i2cdisplaybus.I2CDisplayBus(i2c, device_address=0x3c)
display = adafruit_displayio_ssd1306.SSD1306(display_bus,
    rotation=180,
    width=DW, height=DH,
    auto_refresh=False,
)
display.refresh()

# Touch Keys

import touchio
import adafruit_debouncer

pull_type = None if not is_rp2350 else digitalio.Pull.UP

touchins = [touchio.TouchIn(pin, pull_type) for pin in touch_pins]
for touchin in touchins:
    touchin.threshold = int(touchin.threshold * 1.1)

touches = [adafruit_debouncer.Debouncer(touchin) for touchin in touchins]

def check_touch():
    """Check the touch inputs, return keypad-like Events"""
    events = []
    for i,touch in enumerate(touches):
        touch.update()
        if touch.rose:
            events.append(keypad.Event(i,True))
        elif touch.fell:
            events.append(keypad.Event(i,False))
    return events

# MIDI

import usb_midi
import adafruit_midi

midi_settings = {
    "in_channel": 0,
    "out_channel": 0,
    "debug": False,
}

uart = busio.UART(uart_tx_pin, uart_rx_pin, baudrate=31250, timeout=0.001)

midi_uart = adafruit_midi.MIDI(
    midi_in=uart,
    midi_out=uart,
    **midi_settings,
)

midi_usb = adafruit_midi.MIDI(
    midi_in=usb_midi.ports[0],
    midi_out=usb_midi.ports[1],
    **midi_settings,
)
