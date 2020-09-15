import operator
import typing


class Production:
    def __init__(self, config, prims, initial_utility):
        self.config = config
        self.prims = tuple(prims)
        self.utilities = [initial_utility]

    @property
    def utility(self):
        return self.utilities[-1]

    def fire(self, modules, new_buffers):
        return all(prim.fire(modules, new_buffers) for prim in self.prims)

    def succesfully_used(self, time_left):
        self._reinforce(payoff=self.config['procedural-reward'] - time_left)

    def _reinforce(self, payoff):
        alpha = self.config['alpha']
        self.utilities.append(self.utility + alpha * (payoff - self.utility))

    def reconstructed(self, parent_utility):
        self._reinforce(payoff=parent_utility)

    def __repr__(self):
        return ';'.join(repr(p) for p in self.prims)


class SlotID(typing.NamedTuple):
    """Immutable representation of a slot identifier like 'AC2'"""

    buffer_name: str
    slot_num: int

    def __repr__(self):
        return f'{self.buffer_name}{self.slot_num}'


class SlotPlaceholder(typing.NamedTuple):
    """Immutable representation of a slot placeholder like '*next-op'"""

    name: str

    def __repr__(self):
        return f'*{self.name}'


class EmptyPRIM(typing.NamedTuple):
    """Immutable representation of a prim like 'WM1==nil'"""

    slot: SlotID

    def __repr__(self):
        return f"{self.slot}==nil"

    def fire(self, modules, new_buffers):
        buffer = modules[self.slot.buffer_name].buffer
        return self.slot.slot_num not in buffer.slots


class NotEmptyPRIM(typing.NamedTuple):
    """Immutable representation of a prim like 'WM1<>nil'"""

    slot: SlotID

    def __repr__(self):
        return f"{self.slot}<>nil"

    def fire(self, modules, new_buffers):
        buffer = modules[self.slot.buffer_name].buffer
        return self.slot.slot_num in buffer.slots


class EqualsPRIM(typing.NamedTuple):
    """Immutable representation of a prim like 'WM1==RT2'"""

    lhs: SlotID
    rhs: SlotID

    def __repr__(self):
        return f"{self.lhs}=={self.rhs}"

    def fire(self, modules, new_buffers):
        return compare(modules, self.lhs, self.rhs, operator.eq)


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

    def fire(self, modules, new_buffers):
        return compare(modules, self.lhs, self.rhs, operator.ne)


class CopyPRIM(typing.NamedTuple):
    """Immutable representation of a prim like 'WM1->RT2'"""

    lhs: SlotID
    rhs: SlotID

    def __repr__(self):
        return f"{self.lhs}->{self.rhs}"

    def fire(self, modules, new_buffers):
        buffer = get_buffer(modules, new_buffers, self.rhs)
        slot_value = modules[self.lhs.buffer_name].buffer[self.lhs.slot_num]
        buffer[self.rhs.slot_num] = slot_value
        return True  # not a condition PRIM


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

    def fire(self, modules, new_buffers):
        buffer = get_buffer(modules, new_buffers, self.slot)
        if self.slot.slot_num == 0:
            # TODO: in the case of WM, move to declarative memory
            buffer.clear()
        else:
            del buffer[self.slot.slot_num]
        return True  # not a condition PRIM
