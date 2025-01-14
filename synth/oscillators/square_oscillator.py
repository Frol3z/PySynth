import math

from synth.oscillators.sine_oscillator import SineOscillator


class SquareOscillator(SineOscillator):
    def __init__(self, freq=440, phase=0, amp=1, sample_rate=44_100, wave_range=(-1, 1), threshold=0):
        super().__init__(freq, phase, amp, sample_rate, wave_range)
        self.threshold = threshold

    def __next__(self):
        val = math.sin(self._i + self._p)
        self._i = self._i + self._step
        if val < self.threshold:
            val = self._wave_range[0]
        else:
            val = self._wave_range[1]
        return val * self._a