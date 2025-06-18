# SPDX-FileCopyrightText: Copyright (c) 2025 Cooper Dalrymple
# SPDX-License-Identifier: MIT
"""
`code.py`
================================================================================

This is the main code.py for a polyphonic synth

18 June 2025 - @relic_se / Cooper Dalrymple
"""

import hardware
import asyncio

# Settings

VOICES = 4
ROOT = 48

# Synth

from relic_synthvoice.oscillator import Oscillator

voices = [Oscillator(hardware.synth) for i in range(VOICES)]

# Keyboard

import relic_keymanager

keyboard = relic_keymanager.Keyboard(
    max_voices=VOICES,
    root=ROOT,
)

keyboard.arpeggiator = relic_keymanager.Arpeggiator(
    steps=relic_keymanager.TimerStep.EIGHTH,
    mode=relic_keymanager.ArpeggiatorMode.UP,
)

def on_voice_press(voice):
    voices[voice.index].press(voice.note.notenum, voice.note.velocity)
    hardware.led.value = True
keyboard.on_voice_press = on_voice_press

def on_voice_release(voice):
    voices[voice.index].release()
    if not hardware.synth.pressed:
        hardware.led.value = False
keyboard.on_voice_release = on_voice_release

async def touch_handler():
    while True:
        for event in hardware.check_touch():
            if event.pressed:
                keyboard.append(event.key_number + ROOT, keynum=event.key_number)
            elif event.released:
                keyboard.remove(event.key_number + ROOT)
        await asyncio.sleep(0.005)

# MIDI

from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.control_change import ControlChange
from adafruit_midi.pitch_bend import PitchBend

async def midi_handler():
    while True:
        for midi in (hardware.midi_uart, hardware.midi_usb):
            msg = midi.receive()
            if isinstance(msg, NoteOn) and msg.velocity != 0:
                keyboard.append(msg.note, msg.velocity / 127.0)
            elif isinstance(msg, NoteOff) or (isinstance(msg, NoteOn) and msg.velocity == 0):
                keyboard.remove(msg.note)
            elif isinstance(msg, ControlChange):
                if msg.control == 1:  # Mod Wheel
                    value = msg.value / 127.0
                    # TODO
                elif msg.control == 64:  # Sustain Pedal
                    keyboard.sustain = msg.value >= 64
            elif isinstance(msg, PitchBend):
                value = (msg.pitch_bend / 8192.0) - 1.0
                # TODO
        await asyncio.sleep(0)

# Controls

async def controls_handler():
    global voices

    while True:
        for event in hardware.check_buttons():
            if not event.released:
                continue
            if event.key_number == 0:
                keyboard.sustain = not keyboard.sustain
            if event.key_number == 1:
                keyboard.arpeggiator.active = not keyboard.arpeggiator.active

        knobA, knobB = hardware.knobA.value, hardware.knobB.value
        filter_freq = knobA/65535 * 8000 + 100  # range 100-8100
        filter_resonance = knobB/65535 * 3 + 0.2  # range 0.2-3.2
        for voice in voices:
            voice.filter_frequency = filter_freq
            voice.filter_resonance = filter_resonance
        
        await asyncio.sleep(0.005)

async def main():
    await asyncio.gather(
        asyncio.create_task(touch_handler()),
        asyncio.create_task(midi_handler()),
        asyncio.create_task(controls_handler()),
        asyncio.create_task(keyboard.arpeggiator.update())
    )

asyncio.run(main())
