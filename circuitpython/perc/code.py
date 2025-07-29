# SPDX-FileCopyrightText: Copyright (c) 2025 Cooper Dalrymple
# SPDX-License-Identifier: MIT
"""
`code.py`
================================================================================

This is the main code.py for a percussive sampler

29 July 2025 - @relic_se / Cooper Dalrymple
"""

import hardware
import asyncio
import audiocore
import os
import audiomixer

# Settings

## Velocity is 0->127
HARD = 100
SOFT = 0  # Adjust to act as gate

SAMPLES = {
    36: {
        "samples": {
            HARD: "kick_hard",
            SOFT: "kick_soft"
        },
        "level": 0.25
    },
    38: {
        "samples": {
            HARD: "snare_hard",
            SOFT: "snare_soft"
        },
        "level": 0.25
    },
    41: {
        "samples": {
            HARD: "tom_lo_hard",
            SOFT: "tom_lo_soft"
        },
        "level": 0.25
    },
    42: {
        "samples": {
            SOFT: "hihat_closed"
        },
        "level": 0.25
    },
    43: {
        "samples": {
            HARD: "tom_mid_hard",
            SOFT: "tom_mid_soft"
        },
        "level": 0.25
    },
    44: {
        "samples": {
            SOFT: "hihat_pedal"
        },
        "level": 0.25
    },
    45: {
        "samples": {
            HARD: "tom_hi_hard",
            SOFT: "tom_hi_soft"
        },
        "level": 0.25
    },
    46: {
        "samples": {
            SOFT: "hihat_open"
        },
        "level": 0.25
    },
    49: {
        "samples": {
            HARD: "crash_hard",
            SOFT: "crash_soft"
        },
        "level": 0.25
    },
    51: {
        "samples": {
            HARD: "ride_hard",
            SOFT: "ride_soft"
        },
        "level": 0.25
    }
}

# Load Samples

samples = dict()
for note in SAMPLES.values():
    for name in note["samples"].values():
        if name not in samples and os.stat(path := "/samples/{:s}.wav".format(name)):
            samples[name] = audiocore.WaveFile(path)

mixer = audiomixer.Mixer(
    sample_rate=hardware.SAMPLE_RATE,
    channel_count=hardware.CHANNEL_COUNT,
    buffer_size=hardware.BUFFER_SIZE,
    voice_count=len(samples),
)

hardware.audio.play(mixer)
for i, wav in enumerate(samples.values()):
    mixer.voice[i].play(wav)
    mixer.voice[i].level = 0.0

def get_sample(notenum:int, velocity:int = 127) -> tuple[str, float]:
    if notenum in SAMPLES:
        for vel, name in SAMPLES[notenum]["samples"].items():
            if velocity >= vel:
                return (name, SAMPLES[notenum]["level"])
    return None

def play_sample(name:str, level:float = 0.25) -> None:
    global samples
    if name in samples:
        i = 0
        for val, wav in samples.items():
            if val == name:
                mixer.voice[i].level = level
                mixer.voice[i].play(wav)
                break
            i += 1

def stop_sample(name:str) -> None:
    global samples
    if name in samples:
        for i, val in enumerate(samples.keys()):
            if val == name:
                mixer.voice[i].stop()
                break

# Keyboard

async def touch_handler():
    while True:
        for event in hardware.check_touch():
            if (notenum := event.key_number + 36) in SAMPLES:
                name, level = get_sample(notenum)
                if event.pressed:
                    play_sample(name, level)
                elif event.released:
                    pass
                    # stop_sample(name)
        await asyncio.sleep(0.005)

# MIDI

from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn

async def midi_handler():
    while True:
        for midi in (hardware.midi_uart, hardware.midi_usb):
            msg = midi.receive()
            if isinstance(msg, (NoteOn, NoteOff)) and msg.note in SAMPLES:
                name, level = get_sample(msg.note, msg.velocity)
                if isinstance(msg, NoteOn) and msg.velocity != 0:
                    play_sample(name, level)
                elif isinstance(msg, NoteOff) or (isinstance(msg, NoteOn) and msg.velocity == 0):
                    pass
                    # stop_sample(name)
        await asyncio.sleep(0)

# Controls

async def controls_handler():
    while True:
        for event in hardware.check_buttons():
            pass
        knobA, knobB = hardware.knobA.value, hardware.knobB.value
        await asyncio.sleep(0.005)

async def main():
    await asyncio.gather(
        asyncio.create_task(touch_handler()),
        asyncio.create_task(midi_handler()),
        asyncio.create_task(controls_handler())
    )

asyncio.run(main())
