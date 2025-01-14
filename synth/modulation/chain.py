class Chain:
    def __init__(self, generator, *modifiers):
        self.generator = generator
        self.modifiers = modifiers

    def __getattr__(self, attr):
        val = None
        if hasattr(self.generator, attr):
            val = getattr(self.generator, attr)
        else:
            for modifier in self.modifiers:
                if hasattr(modifier, attr):
                    val = getattr(modifier, attr)
                    break
            else:
                raise AttributeError(f"attribute '{attr}' does not exist")
        return val

    def trigger_release(self):
        tr = "trigger_release"
        if hasattr(self.generator, tr):
            self.generator.trigger_release()
        for modifier in self.modifiers:
            if hasattr(modifier, tr):
                modifier.trigger_release()

    @property
    def ended(self):
        ended = []
        e = "ended"
        if hasattr(self.generator, e):
            ended.append(self.generator.ended)
        ended.extend([m.ended for m in self.modifiers if hasattr(m, e)])
        return all(ended)

    def __iter__(self):
        iter(self.generator)
        [iter(mod) for mod in self.modifiers if hasattr(mod, "__iter__")]
        return self

    def __next__(self):
        val = next(self.generator)
        [next(mod) for mod in self.modifiers if hasattr(mod, "__iter__")]
        for modifier in self.modifiers:
            val = modifier(val)
        return val