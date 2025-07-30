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

from synth_tools.param import ParamRange
from ui import UI, splash_screen
splash_screen(hardware.display)

# Settings

LEVEL      = 0.25  # Use `SAMPLES[notenum]["level"]` to override
FILTER_MAX = min(20000.0, hardware.SAMPLE_RATE / 2.0)
FILTER_MIN = 50.0
WIDTH      = 1.0  # 0.0->1.0

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
        "level": 0.3,
        "panning": -0.3 * WIDTH
    },
    41: {
        "samples": {
            VELOCITY_HARD: "tom_lo_hard",
            VELOCITY_SOFT: "tom_lo_soft"
        },
        "panning": 1.0 * WIDTH
    },
    42: {
        "samples": {
            VELOCITY_SOFT: "hihat_closed"
        },
        "panning": -1.0 * WIDTH
    },
    43: {
        "samples": {
            VELOCITY_HARD: "tom_mid_hard",
            VELOCITY_SOFT: "tom_mid_soft"
        },
        "panning": 0.4 * WIDTH
    },
    44: {
        "samples": {
            VELOCITY_SOFT: "hihat_pedal"
        },
        "panning": -1.0 * WIDTH
    },
    45: {
        "samples": {
            VELOCITY_HARD: "tom_hi_hard",
            VELOCITY_SOFT: "tom_hi_soft"
        },
        "panning": -0.4 * WIDTH
    },
    46: {
        "samples": {
            VELOCITY_SOFT: "hihat_open"
        },
        "panning": -1.0 * WIDTH
    },
    49: {
        "samples": {
            VELOCITY_HARD: "crash_hard",
            VELOCITY_SOFT: "crash_soft"
        },
        "panning": -0.6 * WIDTH
    },
    51: {
        "samples": {
            VELOCITY_HARD: "ride_hard",
            VELOCITY_SOFT: "ride_soft"
        },
        "panning": 0.6 * WIDTH
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
        mixer.voice[i].panning = sample.get("panning", 0.0)
        mixer.voice[i].loop = sample.get("loop", False)
        mixer.voice[i].play(wav)

def stop_sample(sample:dict|str) -> None:
    if type(sample) is str or sample.get("loop", False):
        i = get_sample_index(sample if type(sample) is str else sample["name"])
        mixer.voice[i].stop()

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
        await asyncio.sleep(0.001)

# Controls

button_held = False
button_with_touch = False

params = (
    
    ParamRange("FiltFreq", "filter frequency", FILTER_MAX, "%4d", FILTER_MIN, FILTER_MAX,
        setter=lambda x: setattr(effect_filter.filter, "frequency", x),
        getter=lambda: getattr(effect_filter.filter, "frequency")
    ),
    ParamRange("FilterRes", "filter resonance", 0.7, "%1.2f", 0.1, 2.5,
        setter=lambda x: setattr(effect_filter.filter, "Q", x),
        getter=lambda: getattr(effect_filter.filter, "Q")
    ),

    ParamRange("ReverbMix", "reverb mix", 0.0, "%1.2f", 0.0, 1.0,
        setter=lambda x: setattr(effect_reverb, "mix", x),
        getter=lambda: getattr(effect_reverb, "mix")
    ),
    ParamRange("RevrbSize", "reverb roomsize", 0.5, "%1.2f", 0.0, 1.0,
        setter=lambda x: setattr(effect_reverb, "roomsize", x),
        getter=lambda: getattr(effect_reverb, "roomsize")
    ),

)

ui = UI(hardware.display, params, hardware.knobA.value, hardware.knobB.value)
ui.set_patch_name("drums")

async def touch_handler():
    global button_held, button_with_touch, ui
    while True:
        for event in hardware.check_touch():
            if not button_held:
                if (notenum := event.key_number + 36) in SAMPLES and (sample := get_sample(notenum)):
                    if event.pressed:
                        play_sample(sample)
                        # Special case for hihat
                        if notenum in (42, 44):
                            stop_sample("hihat_open")
                    elif event.released:
                        stop_sample(sample)
            elif event.pressed and not button_with_touch:
                button_with_touch = True
                if event.key_number < (ui.num_params//2):
                    ui.select_pair(event.key_number)
            elif event.released:
                button_with_touch = False
        await asyncio.sleep(0.005)

async def controls_handler():
    global button_held, button_with_touch, ui
    while True:
        hardware.display.refresh()
        
        for event in hardware.check_buttons():
            if event.key_number == 0:
                pass
            elif event.key_number == 1:
                if event.pressed:
                    button_held = True
                if event.released:
                    button_held = False
                    button_with_touch = False

        ui.setA(hardware.knobA.value >> 8)
        ui.setB(hardware.knobB.value >> 8)

        await asyncio.sleep(0.1)

async def main():
    await asyncio.gather(
        asyncio.create_task(touch_handler()),
        asyncio.create_task(midi_handler()),
        asyncio.create_task(controls_handler())
    )

asyncio.run(main())
