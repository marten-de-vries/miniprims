"""Implementation details of PRIMs modules."""

from .chunk import Chunk


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


class Declarative(Module):
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
