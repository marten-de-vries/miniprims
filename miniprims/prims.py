"""Just a bunch of named tuples that make debugging nice."""

import typing
import operator


class SlotID(typing.NamedTuple):
    """Immutable representation of a slot identifier like 'AC2'"""

    buffer_name: str
    slot_num: int

    def __repr__(self):
        return f'{self.buffer_name}{self.slot_num}'


class EqualsPRIM(typing.NamedTuple):
    """Immutable representation of a prim like 'WM1==RT2'"""

    lhs: SlotID
    rhs: SlotID
    operator = operator.eq

    def __repr__(self):
        return f"{self.lhs or 'nil'}=={self.rhs or 'nil'}"


class NotEqualsPRIM(typing.NamedTuple):
    """Immutable representation of a prim like 'WM1<>RT2'"""

    lhs: SlotID
    rhs: SlotID
    operator = operator.ne

    def __repr__(self):
        return f"{self.lhs or 'nil'}<>{self.rhs or 'nil'}"


class CopyPRIM(typing.NamedTuple):
    """Immutable representation of a prim like 'WM1->RT2'"""

    lhs: SlotID
    rhs: SlotID

    def __repr__(self):
        return f"{self.lhs or 'nil'}->{self.rhs or 'nil'}"
