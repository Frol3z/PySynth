from synth.modulation.volume import Volume


class ModulatedVolume(Volume):
    def __init__(self, modulator):
        super().__init__(0.)
        self.modulator = modulator

    def __iter__(self):
        iter(self.modulator)
        return self

    def __next__(self):
        self.amp = next(self.modulator)
        return self.amp

    def trigger_release(self):
        if hasattr(self.modulator, "trigger_release"):
            self.modulator.trigger_release()

    @property
    def ended(self):
        ended = False
        if hasattr(self.modulator, "ended"):
            ended = self.modulator.ended
        else:
            ended = True
        return ended