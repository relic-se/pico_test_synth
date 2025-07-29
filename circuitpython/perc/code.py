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
import audiofilters
import synthio
import audiofreeverb

# Settings

LEVEL      = 0.25  # Use `SAMPLES[notenum]["level"]` to override
FILTER_MAX = 20000.0
FILTER_MIN = 50.0

VELOCITY_HARD = 100  # Velocity is 0->127
VELOCITY_SOFT = 0  # Adjust to act as gate

SAMPLES = {
    36: {
        "samples": {
            VELOCITY_HARD: "kick_hard",
            VELOCITY_SOFT: "kick_soft"
        },
        "level": 0.3
    },
    38: {
        "samples": {
            VELOCITY_HARD: "snare_hard",
            VELOCITY_SOFT: "snare_soft"
        },
        "level": 0.3
    },
    41: {
        "samples": {
            VELOCITY_HARD: "tom_lo_hard",
            VELOCITY_SOFT: "tom_lo_soft"
        }
    },
    42: {
        "samples": {
            VELOCITY_SOFT: "hihat_closed"
        }
    },
    43: {
        "samples": {
            VELOCITY_HARD: "tom_mid_hard",
            VELOCITY_SOFT: "tom_mid_soft"
        }
    },
    44: {
        "samples": {
            VELOCITY_SOFT: "hihat_pedal"
        }
    },
    45: {
        "samples": {
            VELOCITY_HARD: "tom_hi_hard",
            VELOCITY_SOFT: "tom_hi_soft"
        }
    },
    46: {
        "samples": {
            VELOCITY_SOFT: "hihat_open"
        }
    },
    49: {
        "samples": {
            VELOCITY_HARD: "crash_hard",
            VELOCITY_SOFT: "crash_soft"
        }
    },
    51: {
        "samples": {
            VELOCITY_HARD: "ride_hard",
            VELOCITY_SOFT: "ride_soft"
        }
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

effect_filter = audiofilters.Filter(
    filter=synthio.Biquad(synthio.FilterMode.LOW_PASS, FILTER_MAX, 1.2),
    sample_rate=hardware.SAMPLE_RATE,
    channel_count=hardware.CHANNEL_COUNT,
    buffer_size=hardware.BUFFER_SIZE,
)

effect_reverb = audiofreeverb.Freeverb(
    mix=0.0,
    sample_rate=hardware.SAMPLE_RATE,
    channel_count=hardware.CHANNEL_COUNT,
    buffer_size=hardware.BUFFER_SIZE,
)

hardware.audio.play(effect_reverb)
effect_reverb.play(effect_filter)
effect_filter.play(mixer)

for i, wav in enumerate(samples.values()):
    mixer.voice[i].play(wav)
    mixer.voice[i].level = 0.0

def get_sample(notenum:int, velocity:int = 127) -> tuple[str, float]|None:
    if notenum in SAMPLES:
        sample = SAMPLES[notenum].copy()
        for vel, name in sample["samples"].items():
            if velocity >= vel:
                sample["name"] = name
                del sample["samples"]
                return sample
    return None

def get_sample_index(name:str) -> int|None:
    try:
        return list(samples.keys()).index(name)
    except ValueError:
        return None

def play_sample(sample:dict) -> None:
    global samples
    if "name" in sample and sample["name"] in samples:
        i = get_sample_index(sample["name"])
        wav = samples[sample["name"]]
        mixer.voice[i].level = sample.get("level", LEVEL)
        mixer.voice[i].loop = sample.get("loop", False)
        mixer.voice[i].play(wav)

def stop_sample(sample:dict) -> None:
    if sample.get("loop", False):
        i = get_sample_index(sample["name"])
        mixer.voice[i].stop()

# Keyboard

async def touch_handler():
    while True:
        for event in hardware.check_touch():
            if (notenum := event.key_number + 36) in SAMPLES and (sample := get_sample(notenum)):
                if event.pressed:
                    play_sample(sample)
                elif event.released:
                    stop_sample(sample)
        await asyncio.sleep(0.005)

# MIDI

from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn

async def midi_handler():
    while True:
        for midi in (hardware.midi_uart, hardware.midi_usb):
            msg = midi.receive()
            if isinstance(msg, (NoteOn, NoteOff)) and msg.note in SAMPLES and (sample := get_sample(msg.note, msg.velocity)):
                if isinstance(msg, NoteOn) and msg.velocity != 0:
                    play_sample(sample)
                elif isinstance(msg, NoteOff) or (isinstance(msg, NoteOn) and msg.velocity == 0):
                    stop_sample(sample)
        await asyncio.sleep(0)

# Controls

async def controls_handler():
    while True:
        for event in hardware.check_buttons():
            pass

        knobA, knobB = hardware.knobA.value, hardware.knobB.value
        effect_filter.filter.frequency = ((knobA / 65535.0) ** 2) * (FILTER_MAX - FILTER_MIN) + FILTER_MIN
        effect_reverb.mix = knobB / 65535.0

        await asyncio.sleep(0.005)

async def main():
    await asyncio.gather(
        asyncio.create_task(touch_handler()),
        asyncio.create_task(midi_handler()),
        asyncio.create_task(controls_handler())
    )

asyncio.run(main())
