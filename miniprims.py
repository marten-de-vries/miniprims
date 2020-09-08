import simpy

import contextlib
import math
import operator
import types
import typing

# TODO:
# - proper declarative memory (incl. skills extension)
# - FIXMEs
# - production compilation (& productions)
# - spreading activation & skills (incl. proper context/goal tracking)
# - timings
# - operator compilation (bottom-up learning)
# - perceptual action PRIMs


class SlotID(typing.NamedTuple):
    """Immutable representation of a slot identifier like 'AC2'"""

    buffer_name: str
    slot_num: int

    def __repr__(self):
        return f'{self.buffer_name}{self.slot_num}'


class EqualsPrim(typing.NamedTuple):
    """Immutable representation of a prim like 'WM1==RT2'"""

    lhs: SlotID
    rhs: SlotID
    operator = operator.eq

    def __repr__(self):
        return f"{self.lhs or 'nil'}=={self.rhs or 'nil'}"

class NotEqualsPrim(typing.NamedTuple):
    """Immutable representation of a prim like 'WM1<>RT2'"""

    lhs: SlotID
    rhs: SlotID
    operator = operator.ne

    def __repr__(self):
        return f"{self.lhs or 'nil'}<>{self.rhs or 'nil'}"

class CopyPrim(typing.NamedTuple):
    """Immutable representation of a prim like 'WM1->RT2'"""

    lhs: SlotID
    rhs: SlotID

    def __repr__(self):
        return f"{self.lhs or 'nil'}->{self.rhs or 'nil'}"

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


class Module:
    def __init__(self):
        # a list of all buffers this module has known. The most recent one is
        # accessable as self.buffer
        self.buffers = [Chunk.build(self.__class__.__name__, 'buffer')]

    @property
    def buffer(self):
        return self.buffers[-1]

    def buffer_change(self, new_buffer, env, main_process):
        self.buffers.append(new_buffer)

        yield env.timeout(0)


class Visual(Module):
    pass


class Imaginal(Module):
    pass


class Goal(Module):
    def buffer_change(self, new_buffer, env, main_process):
        self.buffers.append(new_buffer)
        if 1 in self.buffer.slots and self.buffer[1] is None:
            return main_process.interrupt()
        yield env.timeout(0)


class Retrieval(Module):
    def __init__(self):
        super().__init__()

        self.memory = []

    def buffer_change(self, new_buffer, env, main_process):
        self.buffers.append(new_buffer)
        matches = [c for c in self.memory if all(
            a == b for a, b in zip(c.slotslist(), self.buffer.slotslist())
        )]
        if len(matches) == 1:
            chunk = matches[0]
            self.buffer.slots = chunk.slots.copy()
        yield env.timeout(0)  # TODO


class Action(Module):
    def buffer_change(self, new_buffer, env, main_process):
        self.buffers.append(new_buffer)
        try:
            action, *args = self.buffer.slotslist()
        except ValueError:
            pass
        else:
            pretty = {
                'say': "Saying",
            }[action]
            print(f"{pretty} {' '.join(args)}")
            if action == 'say' and args == ['stop']:
                return main_process.interrupt()
        yield env.timeout(0)  # TODO


class Constants:
    """Not a module, just used to hold the current operator in its 'buffer'."""


class Model:
    def __init__(self):
        self.modules = {'V': Visual(), 'WM': Imaginal(), 'RT': Retrieval(),
                       'AC': Action(), 'C': Constants(), 'G': Goal()}
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
        if len(matching_ops) == 0 and math.isinf(env.peek()):
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
