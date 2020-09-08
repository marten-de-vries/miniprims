import simpy

import math

from .prims import SlotID, EqualsPrim, NotEqualsPrim, CopyPrim
from .chunk import Chunk
from .modules import Action, Constants, Declarative, Goal, Imaginal, Visual

__all__ = 'Model', 'Chunk', 'SlotID', 'EqualsPrim', 'NotEqualsPrim', 'CopyPrim'

# TODO:
# - proper declarative memory (incl. skills extension)
# - FIXMEs
# - production compilation (& productions)
# - spreading activation & skills (incl. proper context/goal tracking)
# - timings
# - operator compilation (bottom-up learning)
# - perceptual action PRIMs


class Model:
    def __init__(self):
        self.modules = {'AC': Action(), 'C': Constants(), 'G': Goal(),
                        'RT': Declarative(), 'V': Visual(), 'WM': Imaginal()}
        self.env = simpy.Environment()
        self.env.process(self._run())

    def _run(self):
        while True:
            # reset buffers?
            # run script
            while True:
                try:
                    step = self._run_prims(self.env.active_process)
                    yield self.env.process(step)
                except simpy.Interrupt:
                    break  # we're done with this simulation round
            break  # TODO: remove

    def _run_prims(self, parent):
        # TODO: actual matching
        matching_ops = [
            c for c in self.modules['RT'].memory
            if c['isa'] == 'operator' and self.match_conditions(c)
        ]
        if len(matching_ops) == 0 and math.isinf(self.env.peek()):
            return parent.interrupt()
        assert len(matching_ops) == 1
        operator = matching_ops[0]
        self.modules['C'].buffer = operator

        # perform actions
        module_responses = self.perform_actions(operator)
        try:
            yield self.env.timeout(50)  # TODO
            yield self.env.any_of(module_responses)
        except simpy.Interrupt:
            # one of the modules decided it's time to quit. Pass on the
            # message.
            return parent.interrupt()

    def match_conditions(self, operator):
        return all(self.match_condition(part)
                   for part in operator['condition'])

    def match_condition(self, condition):
        undefined = object()
        try:
            lhs_val = self.slot_value(condition.lhs)
        except KeyError:
            lhs_val = undefined
        try:
            rhs_val = self.slot_value(condition.rhs)
        except KeyError:
            rhs_val = undefined
        if lhs_val == undefined and rhs_val == undefined:
            return False
        all_nothing = ((lhs_val is None and rhs_val == undefined) or
                       (lhs_val == undefined and rhs_val is None))
        if all_nothing:
            return condition.operator(None, None)
        return condition.operator(lhs_val, rhs_val)

    def perform_actions(self, operator):
        new_buffers = {}
        for lhs, rhs in operator['action']:
            mod_name, slot = rhs
            mod = self.modules[mod_name]
            # TODO: only RT? And is there a nicer way?
            fallback = {} if mod_name == 'RT' else mod.buffer.slots.copy()
            new_buffer = new_buffers.setdefault(mod, fallback)
            slot_val = self.slot_value(lhs)
            if slot_val is None:
                del new_buffer[slot]
            else:
                new_buffer[slot] = slot_val

        for mod, new_buffer in new_buffers.items():
            c = Chunk(new_buffer)
            callback = mod.buffer_change(c, self.env, self.env.active_process)
            yield self.env.process(callback)

    def slot_value(self, slotinfo):
        if not slotinfo:
            return None
        mod, slot = slotinfo
        return self.modules[mod].buffer[slot]
