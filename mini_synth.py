import math
import pyaudio
import itertools
import numpy as np
import keyboard
from enum import Enum

from adsr_envelope import ADSREnvelope
from modulated_oscillator import ModulatedOscillator
from sawtooth_oscillator import SawtoothOscillator
from sine_oscillator import SineOscillator
from square_oscillator import SquareOscillator
from triangle_oscillator import TriangleOscillator

class OscillatorType(Enum):
    SINE = 0
    SQUARE = 1
    TRIANGLE = 2
    SAWTOOTH = 3

# Custom parameters
BUFFER_SIZE = 256
SAMPLE_RATE = 44100
AMP = 0.05 # between [0, 1]
MIN_OCTAVE = 0
MAX_OCTAVE = 9
OSCILLATOR_TYPE = OscillatorType.TRIANGLE

# Piano keyboard layout based on:
# https://ux.stackexchange.com/questions/46669/mapping-piano-keys-to-computer-keyboard
KEYS = {
    'A': 12, 'W': 13, 'S': 14, 'E': 15, # C0 to D#0
    'D': 16, 'F': 17, 'T': 18, 'G': 19, # E0 to G0
    'Y': 20, 'H': 21, 'U': 22, 'J': 23, # G#0 to B0
    'K': 24, 'O': 25, 'L': 26, 'P': 27, # C1 to D#1
    ';': 28, '\'': 29, ']': 30          # E1 to F#1
}

# Default key bindings
OCTAVE_DOWN = 'Z'
OCTAVE_UP = 'X'

# Simple sine oscillator
# @todo remove
def get_sine_oscillator(freq=440, amp=1, sample_rate=SAMPLE_RATE):
    increment = (2 * math.pi * freq) / sample_rate
    return ( math.sin(v) * amp * AMP for v in itertools.count(start=0, step=increment) )

# Converts notes that are being played to 16bit ints
def get_samples(notes_dict, num_samples=BUFFER_SIZE):
    # Sum every oscillator and dividing by the total number
    # to normalize amplitude
    samples = [ sum( [next(osc) for _, osc in notes_dict.items()] )
                / len(notes_dict.items())
                for _ in range(num_samples)]

    samples = np.array(samples)
    # Ensure that values are normalized
    samples = np.clip(samples, -1, 1)
    # Scale based on the amplitude
    samples = samples * AMP

    samples = np.int16(samples * 32767)
    return samples

# Return the requested oscillator
def get_oscillator(oscillator_type, freq):
    if oscillator_type == OscillatorType.SINE:
        osc = iter(SineOscillator(freq=freq))
    elif oscillator_type == OscillatorType.SQUARE:
        osc = iter(SquareOscillator(freq=freq))
    elif oscillator_type == OscillatorType.TRIANGLE:
        osc = iter(TriangleOscillator(freq=freq))
    elif oscillator_type == OscillatorType.SAWTOOTH:
        osc = iter(SawtoothOscillator(freq=freq))

    # Add modulation
    adsr_envelope = ADSREnvelope(attack_duration=0.9, decay_duration=0.2, sustain_level=0.7, release_duration=0.0)
    lfo = SineOscillator(freq=5, wave_range=(0.2, 1))
    mod_osc = ModulatedOscillator(osc, *(lfo, adsr_envelope), amp_mod=amp_mod)
    mod_osc = iter(mod_osc)

    return mod_osc

# Amplitude Modulation
def amp_mod(init_amp, env):
    return env * init_amp

# Frequency (and Phase) Modulation
def freq_mod(init_freq, env, mod_amt=1, sustain_level=0.7):
    # When env is at sustain stage it will play the initial frequency
    return init_freq + ((env - sustain_level) * init_freq * mod_amt)

# Converts MIDI note to frequency in Hz
# https://homes.luddy.indiana.edu/donbyrd/Teach/MusicalPitchesTable.htm
def note_to_frequency(note):
    return 440 * 2**((note - 69) / 12)

# Converts MIDI note from keybind in the correct octave
def midi_note_to_octave(midi_note, octave):
    return midi_note + octave * 12

# Clamps value between [lower_bound, upper_bound]
def clamp(value, lower_bound = 0, upper_bound = 1):
    if value < lower_bound:
        value = lower_bound
    elif value > upper_bound:
        value = upper_bound
    return value

# Increases or decreases octave based on direction
def switch_octave(octave, direction):
    octave += direction
    octave = clamp(octave, lower_bound=MIN_OCTAVE, upper_bound=MAX_OCTAVE)
    print('OCTAVE:', octave) # DEBUG
    return octave

####################
# CODE STARTS HERE #
####################

# Open audio stream
stream = pyaudio.PyAudio().open(
    rate=SAMPLE_RATE,
    channels=1,
    format=pyaudio.paInt16,
    output=True,
    frames_per_buffer=BUFFER_SIZE,
)

try:
    print("Starting...")
    notes_dict = {}
    octave = 4
    pressed_keys = {OCTAVE_DOWN: False, OCTAVE_UP: False}

    while True:

        # Octave switch between [MIN_OCTAVE, MAX_OCTAVE]
        if keyboard.is_pressed(OCTAVE_UP) and not pressed_keys[OCTAVE_UP]:
            pressed_keys[OCTAVE_UP] = True
            octave = switch_octave(octave, +1)
        if keyboard.is_pressed(OCTAVE_DOWN) and not pressed_keys[OCTAVE_DOWN]:
            pressed_keys[OCTAVE_DOWN] = True
            octave = switch_octave(octave, -1)

        # Remove key pressed on key release
        if not keyboard.is_pressed(OCTAVE_UP):
            pressed_keys[OCTAVE_UP] = False
        if not keyboard.is_pressed(OCTAVE_DOWN):
            pressed_keys[OCTAVE_DOWN] = False

        # Updating note dictionary
        for key, midi_note in KEYS.items():
            if keyboard.is_pressed(key):
                # Adding the note if not already there
                if key not in notes_dict:
                    midi_note_in_octave = midi_note_to_octave(midi_note, octave)
                    freq = note_to_frequency(midi_note_in_octave)
                    notes_dict[key] = get_oscillator(OSCILLATOR_TYPE, freq)
            else:
                if key in notes_dict:
                    if not notes_dict[key].ended:
                        notes_dict[key].trigger_release()
                    else:
                        del notes_dict[key]

        # Send notes to the audio stream
        if notes_dict:
            samples = get_samples(notes_dict)
            samples = np.int16(samples).tobytes()
            stream.write(samples)

except KeyboardInterrupt as err:
    stream.close()
    print("Stopping...")