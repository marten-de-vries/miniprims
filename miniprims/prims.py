"""Just a bunch of named tuples that make debugging nice."""

import typing
import operator


class SlotID(typing.NamedTuple):
    """Immutable representation of a slot identifier like 'AC2'"""

    buffer_name: str
    slot_num: int

    def __repr__(self):
        return f'{self.buffer_name}{self.slot_num}'


class EmptyPRIM(typing.NamedTuple):
    """Immutable representation of a prim like 'WM1==nil'"""

    slot: SlotID

    def __repr__(self):
        return f"{self.slot}==nil"

    def match_condition(self, modules):
        buffer = modules[self.slot.buffer_name].buffer
        return self.slot.slot_num not in buffer.slots

    def fire(self, modules, new_buffers):
        pass  # not an action prim


class NotEmptyPRIM(typing.NamedTuple):
    """Immutable representation of a prim like 'WM1<>nil'"""

    slot: SlotID

    def __repr__(self):
        return f"{self.slot}<>nil"

    def match_condition(self, modules):
        buffer = modules[self.slot.buffer_name].buffer
        return self.slot.slot_num in buffer.slots

    def fire(self, modules, new_buffers):
        pass  # not an action prim


class EqualsPRIM(typing.NamedTuple):
    """Immutable representation of a prim like 'WM1==RT2'"""

    lhs: SlotID
    rhs: SlotID

    def __repr__(self):
        return f"{self.lhs}=={self.rhs}"

    def match_condition(self, modules):
        return compare(modules, self.lhs, self.rhs, operator.eq)

    def fire(self, modules, new_buffers):
        pass  # not an action prim


def compare(modules, lhs, rhs, op):
    try:
        a = modules[lhs.buffer_name].buffer[lhs.slot_num]
        b = modules[rhs.buffer_name].buffer[rhs.slot_num]
    except KeyError:
        return False
    else:
        return op(a, b)


class NotEqualsPRIM(typing.NamedTuple):
    """Immutable representation of a prim like 'WM1<>RT2'"""

    lhs: SlotID
    rhs: SlotID

    def __repr__(self):
        return f"{self.lhs}<>{self.rhs}"

    def match_condition(self, modules):
        return compare(modules, self.lhs, self.rhs, operator.ne)

    def fire(self, modules, new_buffers):
        pass  # not an action prim


class CopyPRIM(typing.NamedTuple):
    """Immutable representation of a prim like 'WM1->RT2'"""

    lhs: SlotID
    rhs: SlotID

    def __repr__(self):
        return f"{self.lhs}->{self.rhs}"

    def match_condition(self, modules):
        return True  # not a condition PRIM

    def fire(self, modules, new_buffers):
        buffer = get_buffer(modules, new_buffers, self.rhs)
        slot_value = modules[self.lhs.buffer_name].buffer[self.lhs.slot_num]
        buffer[self.rhs.slot_num] = slot_value


def get_buffer(modules, new_buffers, slot):
    mod = modules[slot.buffer_name]
    # TODO: only RT? And is there a nicer way?
    fallback = {} if slot.buffer_name == 'RT' else mod.buffer.slots.copy()
    return new_buffers.setdefault(mod, fallback)


class RemovePRIM(typing.NamedTuple):
    """Immutable representation of a prim like 'nil->WM1'"""

    slot: SlotID

    def __repr__(self):
        return f"nil->{self.slot}"

    def match_condition(self, modules):
        return True  # not a condition PRIM

    def fire(self, modules, new_buffers):
        buffer = get_buffer(modules, new_buffers, self.slot)
        del buffer[self.slot.slot_num]
