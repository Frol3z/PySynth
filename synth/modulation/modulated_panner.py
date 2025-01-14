from synth.modulation.panner import Panner


class ModulatedPanner(Panner):
    def __init__(self, modulator):
        super().__init__(r=0)
        self.modulator = modulator

    def __iter__(self):
        iter(self.modulator)
        return self

    def __next__(self):
        self.r = (next(self.modulator) + 1) / 2
        return self.r