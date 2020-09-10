"""Implementation details of PRIMs modules."""

import bisect
import math

import numpy

from .chunk import Chunk


class Module:
    def __init__(self, config):
        self.config = config
        # a list of all buffers this module has known. The most recent one is
        # accessable as self.buffer
        self.buffers = [Chunk.build(config, self.__class__.__name__, 'buffer')]

    @property
    def buffer(self):
        return self.buffers[-1]

    def buffer_change(self, new_buffer, env, main_process):
        """return type: True when the simulation should pause, False
        otherwise.

        """
        self.buffers.append(new_buffer)

        yield env.timeout(0)
        return False


class Visual(Module):
    def show(self, *values):
        chunk = Chunk.build(self.config, 'Visual', 'buffer', *values)
        self.buffers.append(chunk)


class Imaginal(Module):
    pass


class Goal(Module):
    def buffer_change(self, new_buffer, env, main_process):
        self.buffers.append(new_buffer)
        yield env.timeout(0)
        # stop if no goal remains
        return not self.buffer.slotslist()

    def focus(self, *values):
        chunk = Chunk.build(self.config, 'Goal', 'buffer', *values)
        self.buffers.append(chunk)


class Declarative(Module):
    def __init__(self, config):
        super().__init__(config)

        self.memory = []

    def add_memory(self, new_chunk, t=0):
        for chunk in self.memory:
            if chunk.slots == new_chunk.slots:
                break  # there's an existing chunk in memory like this one
        else:
            # no chunk like this in memory yet, so create it
            chunk = new_chunk
            self.memory.append(chunk)
        # reinforce the chunk
        self.reinforce(chunk, t)

    def reinforce(self, chunk, t):
        if self.config['ol']:  # optimized learning
            if chunk.creation_time is None:
                chunk.creation_time = t
            chunk.reinforced_count += 1
        else:
            chunk.reinforced.append(t)

    def best_matches(self, match_cond, t, max_matches=None):
        result = []
        for chunk in self.memory:
            if not match_cond(chunk):
                continue
            activation = chunk.baselevel_activation(t)
            if activation < self.config['rt']:
                continue
            # TODO: more activation
            # '-' because Python implements a min heap and we want a max heap
            # random() to prevent chunks from ever being compared.
            bisect.insort(result, (activation, numpy.random.random(), chunk))
            result = result[:max_matches]

        for activation, _, chunk in reversed(result):
            yield activation, chunk

    def best_match(self, search_chunk, t):
        search_slots = search_chunk.slotslist()

        def match_cond(chunk):
            return all(a == b for a, b in zip(chunk.slotslist(), search_slots))
        return next(self.best_matches(match_cond, t, max_matches=1))

    def buffer_change(self, new_buffer, env, main_process):
        try:
            exponent, match = self.best_match(new_buffer, env.now)
        except StopIteration:
            exponent = self.config['rt']
            match = Chunk.build(self.config, 'retrieval-failure', 'status',
                                'error')

        yield env.timeout(self.config['lf'] * math.exp(-exponent))
        self.buffers.append(new_buffer)
        self.buffers.append(match)
        return False


class Action(Module):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.interrupt_trigger = None
        self.actions = {}

    def register(self, name, latency, noise, distribution, output):
        duration = {
            'none': lambda: latency,
            'uniform': lambda: numpy.random.uniform(latency - noise,
                                                    latency + noise),
            'logistic': lambda: numpy.random.logistic(latency, noise),
        }[distribution]
        self.actions[name] = duration, output

    def buffer_change(self, new_buffer, env, main_process):
        self.buffers.append(new_buffer)
        info = self.buffer.slotslist()
        try:
            action, *args = info
        except ValueError:
            pass
        else:
            calculate_duration, output = self.actions[action]
            yield env.timeout(calculate_duration())
            print(f"{env.now:.3f} {output} {' '.join(args)}")

        # if the interrupt trigger is in the buffer, stop.
        return self.interrupt_trigger == info[:len(self.interrupt_trigger)]


class Constants:
    """Not a module, just used to hold the current operator in its 'buffer'."""
