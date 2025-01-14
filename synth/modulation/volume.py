from collections.abc import Iterable

class Volume:
    def __init__(self, amp=1.):
        self.amp = amp

    def __call__(self, val):
        _val = None
        if isinstance(val, Iterable):
            _val = tuple(v * self.amp for v in val)
        elif isinstance(val, (int, float)):
            _val = val * self.amp
        return _val