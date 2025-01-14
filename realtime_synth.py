from synth.modulation.adsr_envelope import ADSREnvelope
from synth.modulation.chain import Chain
from synth.modulation.modulated_panner import ModulatedPanner
from synth.modulation.modulated_volume import ModulatedVolume
from synth.modulation.panner import Panner
from synth.modulation.wave_adder import WaveAdder
from synth.oscillators.sawtooth_oscillator import SawtoothOscillator
from synth.oscillators.sine_oscillator import SineOscillator
from synth.oscillators.square_oscillator import SquareOscillator
from synth.polysynth import PolySynth
from synth.oscillators.triangle_oscillator import TriangleOscillator

# HOW TO PLAY
# Piano keyboard mapped based on: https://i.sstatic.net/iJ4XT.png
# Z | -1 Octave
# X | +1 Octave
# B | Toggle filter
# C | Decrease cutoff frequency
# V | Increase cutoff frequency

def double_sawtooth(freq, amp, sample_rate):
    osc = Chain(
        WaveAdder(
            SawtoothOscillator(freq=freq, amp=amp, sample_rate=sample_rate),
            SawtoothOscillator(freq=freq, amp=amp, phase=180, sample_rate=sample_rate)
        ),
        ModulatedVolume(
            ADSREnvelope(0.02, 0.3, 0.4, 0.1)
        ),
    )
    return iter(osc)

# Pulsing triangle wave
def lfo_oscillator(freq, amp, sample_rate):
    osc = Chain(
        TriangleOscillator(freq=freq,
                           amp=amp, sample_rate=sample_rate),
        ModulatedVolume(
            ADSREnvelope(0.02, 0.0, 1.0, 0.05)
        ),
        ModulatedVolume(
            SineOscillator(freq=1)
        )
    )
    return iter(osc)

# Oscillator with ADSR AM modulation
def default_oscillator(freq, amp, sample_rate):
    osc = Chain(
        TriangleOscillator(freq=freq,
                           amp=amp, sample_rate=sample_rate),
        ModulatedVolume(
            ADSREnvelope(0.05, 0.1, 0.4, 0.05)
        )
    )
    return iter(osc)

synth = PolySynth(max_amp=0.3)
synth.play(default_oscillator)


