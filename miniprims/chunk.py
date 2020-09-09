import contextlib
import math
import types

import numpy


class Chunk:
    """A chunk is mostly immutable, with the exception of
    'reinforced'/'reinforced_count & creation_time

    """
    # constructors
    def __init__(self, config, slots, name=None, isa=None, activation=None):
        self.config = config

        # read-only dict with chunk data
        self.slots = types.MappingProxyType({0: name, 'isa': isa, **slots})
        if activation is None:
            self.fixed_activation = self.config['default-activation']
        else:
            self.fixed_activation = activation
        if self.config['ol']:  # optimized learning
            self.reinforced_count = 0
            self.creation_time = None
        else:
            self.reinforced = []

    @classmethod
    def build(cls, config, name, isa, *slot_vals, condition=None, action=None,
              **kwargs):
        """alternate constructor"""

        slots = {i + 1: value for i, value in enumerate(slot_vals)}
        if condition:
            slots['condition'] = condition
        if action:
            slots['action'] = action
        return cls(config, slots, name, isa, **kwargs)

    # accessors
    def __getitem__(self, slot):
        return self.slots[slot]

    def slotslist(self):
        return [v for k, v in sorted(self.slots.items(), key=lambda x: str(x))
                if isinstance(k, int) and k != 0]

    @numpy.errstate(divide='ignore')
    def baselevel_activation(self, t):
        d = self.config['bll']
        # TODO: check validity of fixed term!!!
        fixedterm = math.exp(self.fixed_activation)
        if self.config['ol']:  # optimized learning
            t0 = self.creation_time
            n = self.reinforced_count
            return numpy.log(fixedterm + n / (1 - d)) - d * numpy.log(t - t0)
        else:
            sumterm = numpy.sum(t - numpy.array(self.reinforced))**(-d)
            return numpy.log(fixedterm + sumterm)

    # setters
    def reinforce(self, t):
        if self.config['ol']:
            self.reinforced_count += 1
        else:
            self.reinforced.append(t)

    # debugging
    def __repr__(self):
        remainder = ' '.join(self.slotslist())
        with contextlib.suppress(KeyError):
            remainder += f" | {'; '.join(repr(c) for c in self['condition'])}"
            remainder += f" ==> {'; '.join(repr(a) for a in self['action'])}"
        return f"<{self[0]}: {self['isa']} | {remainder}>"
