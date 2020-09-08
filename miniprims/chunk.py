import contextlib
import types


class Chunk:
    # constructors
    def __init__(self, slots, name=None, isa=None):
        # read-only dict with chunk data
        self.slots = types.MappingProxyType({0: name, 'isa': isa, **slots})

    @classmethod
    def build(cls, name, isa, *slot_vals, condition=None, action=None):
        """alternate constructor"""

        slots = {i + 1: value for i, value in enumerate(slot_vals)}
        if condition:
            slots['condition'] = condition
        if action:
            slots['action'] = action
        return cls(slots, name, isa)

    # accessors
    def __getitem__(self, slot):
        return self.slots[slot]

    def slotslist(self):
        return [v for k, v in sorted(self.slots.items(), key=lambda x: str(x))
                if isinstance(k, int) and k != 0]

    # debugging
    def __repr__(self):
        remainder = ' '.join(self.slotslist())
        with contextlib.suppress(KeyError):
            remainder += f" | {'; '.join(repr(c) for c in self['condition'])}"
            remainder += f" ==> {'; '.join(repr(a) for a in self['action'])}"
        return f"<{self[0]}: {self['isa']} | {remainder}>"
