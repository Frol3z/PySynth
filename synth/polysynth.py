import itertools
import math

import keyboard
import numpy as np
import pyaudio
from scipy.signal import butter, lfilter, lfilter_zi

MIN_OCTAVE = 0
MAX_OCTAVE = 9
MIN_CUTOFF = 10
MAX_CUTOFF = 2000
CUTOFF_INCREMENT = 100

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
CUTOFF_DOWN = 'C'
CUTOFF_UP = 'V'
TOGGLE_FILTER = 'B'

def butter_lowpass(cutoff, fs, order=2):
    b, a = butter(order, cutoff, fs=fs, btype='low', analog=False)
    return b, a

def butter_lowpass_filter(data, cutoff, fs, order=2, zi=None):
    b, a = butter_lowpass(cutoff, fs, order)

    # Initialize the zi state if not provided
    if zi is None:
        zi = lfilter_zi(b, a) * data[0]  # Use the first value of data to initialize zi

    # Apply the filter and update zi
    filtered_data, zi_new = lfilter(b, a, data, zi=zi)

    # Return filtered data and updated zi
    return filtered_data, zi_new

def get_sin_oscillator(freq=55, amp=1, sample_rate=44100):
    increment = (2 * math.pi * freq)/ sample_rate
    return (math.sin(v) * amp for v in itertools.count(start=0, step=increment))

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

class PolySynth:
    def __init__(self, amp_scale=0.3, max_amp=0.3, sample_rate=44100, num_samples=128):
        # Constants
        self.num_samples = num_samples
        self.sample_rate = sample_rate
        self.amp_scale = amp_scale
        self.max_amp = max_amp
        self.octave = 4
        # Filter stuff
        self.enable_filter = False
        self.zi = None # Filter state
        self.cutoff = 500

    def _init_stream(self, nchannels):
        # Initialize the Stream object
        self.stream = pyaudio.PyAudio().open(
            rate=self.sample_rate,
            channels=nchannels,
            format=pyaudio.paInt16,
            output=True,
            frames_per_buffer=self.num_samples
        )

    def _get_samples(self, notes_dict):
        # Return samples in int16 format
        samples = []
        for _ in range(self.num_samples):
            samples.append(
                [next(osc[0]) for _, osc in notes_dict.items()]
            )

        samples = np.array(samples).sum(axis=1)

        # Apply filter
        if self.enable_filter:
            samples, zi = butter_lowpass_filter(samples, cutoff=self.cutoff, fs=self.sample_rate, order=6, zi=self.zi)
            self.zi = zi

        samples = np.float32(samples)
        samples *= self.amp_scale
        samples = np.int16(samples.clip(-self.max_amp, self.max_amp) * 32767)
        return samples.reshape(self.num_samples, -1)

    def play(self, osc_function=get_sin_oscillator):
        # Check for release trigger, number of channels and init Stream
        tempcf = osc_function(1, 1, self.sample_rate)
        has_trigger = hasattr(tempcf, "trigger_release")
        tempsm = self._get_samples({-1: [tempcf, False]})
        nchannels = tempsm.shape[1]
        self._init_stream(nchannels)

        try:
            notes_dict = {}
            pressed_keys = {OCTAVE_DOWN: False, OCTAVE_UP: False, CUTOFF_DOWN: False, CUTOFF_UP: False, TOGGLE_FILTER: False}
            while True:
                if notes_dict:
                    # Play the notes
                    samples = self._get_samples(notes_dict)
                    self.stream.write(samples.tobytes())

                # Octave switch between [MIN_OCTAVE, MAX_OCTAVE]
                if keyboard.is_pressed(OCTAVE_UP) and not pressed_keys[OCTAVE_UP]:
                    pressed_keys[OCTAVE_UP] = True
                    self.octave = switch_octave(self.octave, +1)
                if keyboard.is_pressed(OCTAVE_DOWN) and not pressed_keys[OCTAVE_DOWN]:
                    pressed_keys[OCTAVE_DOWN] = True
                    self.octave = switch_octave(self.octave, -1)
                # Filters stuff
                if keyboard.is_pressed(TOGGLE_FILTER) and not pressed_keys[TOGGLE_FILTER]:
                    pressed_keys[TOGGLE_FILTER] = True
                    self.enable_filter = not self.enable_filter
                    print('Filter enabled: ' + str(self.enable_filter))
                if keyboard.is_pressed(CUTOFF_DOWN) and not pressed_keys[CUTOFF_DOWN]:
                    pressed_keys[CUTOFF_DOWN] = True
                    self.cutoff -= CUTOFF_INCREMENT
                    if self.cutoff < MIN_CUTOFF:
                        self.cutoff = MIN_CUTOFF
                    self.zi = None
                    print('Cutoff: ' + str(self.cutoff))
                if keyboard.is_pressed(CUTOFF_UP) and not pressed_keys[CUTOFF_UP]:
                    pressed_keys[CUTOFF_UP] = True
                    self.cutoff += CUTOFF_INCREMENT
                    if self.cutoff > MAX_CUTOFF:
                        self.cutoff = MAX_CUTOFF
                    self.zi = None
                    print('Cutoff: ' + str(self.cutoff))

                # Remove key pressed on key release
                if not keyboard.is_pressed(OCTAVE_UP):
                    pressed_keys[OCTAVE_UP] = False
                if not keyboard.is_pressed(OCTAVE_DOWN):
                    pressed_keys[OCTAVE_DOWN] = False
                if not keyboard.is_pressed(TOGGLE_FILTER):
                    pressed_keys[TOGGLE_FILTER] = False
                if not keyboard.is_pressed(CUTOFF_UP):
                    pressed_keys[CUTOFF_UP] = False
                if not keyboard.is_pressed(CUTOFF_DOWN):
                    pressed_keys[CUTOFF_DOWN] = False

                # Updating note dictionary
                for key, midi_note in KEYS.items():
                    if keyboard.is_pressed(key):
                        # Adding the note if not already there
                        if key not in notes_dict:
                            midi_note_in_octave = midi_note_to_octave(midi_note, self.octave)
                            freq = note_to_frequency(midi_note_in_octave)
                            # [ oscillator, trigger_release flag ]
                            notes_dict[key] = [ osc_function(freq=freq, amp=self.max_amp, sample_rate=self.sample_rate), False ]
                    else:
                        # Deleting note or triggering release if key is not being pressed
                        if key in notes_dict:
                            if has_trigger:
                                if not notes_dict[key][1]:
                                    notes_dict[key][0].trigger_release()
                                    notes_dict[key][1] = True
                            else:
                                del notes_dict[key]

                if has_trigger:
                    # Delete notes if ended
                    ended_notes = [k for k, o in notes_dict.items() if o[0].ended and o[1]]
                    for note in ended_notes:
                        del notes_dict[note]

        except KeyboardInterrupt as err:
            self.stream.close()