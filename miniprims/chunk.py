import contextlib
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
        dat = sorted((k, v) for k, v in self.slots.items()
                     if isinstance(k, int) and k != 0)
        self.slotslist = tuple(v for k, v in dat)

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
    def build(cls, config, name, isa, *slot_vals, prims=None, **kwargs):
        """alternate constructor"""

        slots = {i + 1: value for i, value in enumerate(slot_vals)}
        if prims:
            slots['prims'] = prims
        return cls(config, slots, name, isa, **kwargs)

    # accessors
    def __getitem__(self, slot):
        return self.slots[slot]

    @numpy.errstate(divide='ignore')
    def baselevel_activation(self, t):
        d = self.config['bll']
        # TODO: check validity of fixed term!!!
        if self.fixed_activation is None:
            fixedterm = 0
        else:
            fixedterm = numpy.exp(self.fixed_activation)
        if self.config['ol']:  # optimized learning
            t0 = self.creation_time
            n = self.reinforced_count
            return numpy.log(fixedterm + n / (1 - d)) - d * numpy.log(t - t0)
        else:
            sumterm = numpy.sum(t - numpy.array(self.reinforced))**(-d)
            return numpy.log(fixedterm + sumterm)

    # setters
    def reinforce(self, t):
        if self.config['ol']:  # optimized learning
            if self.creation_time is None:
                self.creation_time = t
            self.reinforced_count += 1
        else:
            self.reinforced.append(t)

    # debugging
    def __repr__(self):
        remainder = ' '.join(str(s) for s in self.slotslist)
        with contextlib.suppress(KeyError):
            remainder += f" | {'; '.join(repr(c) for c in self['prims'])}"
        for key, value in self.slots.items():
            if isinstance(key, int) or key in ['prims', 'isa']:
                continue  # already handled
            remainder += f" | {key}={value}"
        return f"<{self[0]}: {self['isa']} | {remainder}>"
