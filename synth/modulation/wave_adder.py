from collections.abc import Iterable

class WaveAdder:
    def __init__(self, *generators, stereo=False):
        self.generators = generators
        self.stereo = stereo

    def _mod_channels(self, _val):
        val = _val
        if isinstance(_val, (int, float)) and self.stereo:
            val = (_val, _val)
        elif isinstance(_val, Iterable) and not self.stereo:
            val = sum(_val) / len(_val)
        return val

    def trigger_release(self):
        [gen.trigger_release() for gen in self.generators if hasattr(gen, "trigger_release")]

    @property
    def ended(self):
        ended = [gen.ended for gen in self.generators if hasattr(gen, "ended")]
        return all(ended)

    def __iter__(self):
        [iter(gen) for gen in self.generators]
        return self

    def __next__(self):
        vals = [self._mod_channels(next(gen)) for gen in self.generators]
        if self.stereo:
            l, r = zip(*vals)
            val = (sum(l) / len(l), sum(r) / len(r))
        else:
            val = sum(vals) / len(vals)
        return val