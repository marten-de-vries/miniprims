"""Implementation details of PRIMs modules."""

import bisect
import math

import numpy

from .chunk import Chunk


class BufferModule:
    def __init__(self, config):
        self.config = config
        # a list of all buffers this module has known. The most recent one is
        # accessable as self.buffer
        self.buffers = [Chunk.build(config, self.__class__.__name__, 'buffer')]

    @property
    def buffer(self):
        return self.buffers[-1]

    def buffer_change(self, new_buffer, env):
        """return type: True when the simulation should pause, False
        otherwise.

        """
        self.buffers.append(new_buffer)

        yield env.timeout(0)
        return False


class Visual(BufferModule):
    def show(self, *values):
        chunk = Chunk.build(self.config, 'Visual', 'buffer', *values)
        self.buffers.append(chunk)


class Imaginal(BufferModule):
    pass


class Goal(BufferModule):
    def buffer_change(self, new_buffer, env):
        self.buffers.append(new_buffer)
        yield env.timeout(0)
        # stop if no goal remains
        return not self.buffer.slotslist()

    def focus(self, *values):
        chunk = Chunk.build(self.config, 'Goal', 'buffer', *values)
        self.buffers.append(chunk)


class Declarative(BufferModule):
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
        chunk.reinforce(t)

    def best_matches(self, match_cond, t, max_matches=None):
        result = []
        for chunk in self.memory:
            if not match_cond(chunk):
                continue
            activation = chunk.baselevel_activation(t)
            if activation < self.config['rt']:
                continue
            # TODO: more activation
            bisect.insort(result, (activation, numpy.random.random(), chunk))
            result = result[:max_matches]

        for activation, _, chunk in reversed(result):
            yield activation, chunk

    def best_match(self, search_chunk, t):
        search_slots = search_chunk.slotslist()

        def match_cond(chunk):
            return search_slots == chunk.slotslist()[:len(search_slots)]
        return next(self.best_matches(match_cond, t, max_matches=1))

    def buffer_change(self, new_buffer, env):
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


class Action(BufferModule):
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

    def buffer_change(self, new_buffer, env):
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


class Procedural:
    def __init__(self, config, modules):
        self.config = config
        self.modules = modules
        self.declarative = modules['RT']

    def step(self, env):
        # return True if the simulation should pause, else False
        matches = self.declarative.best_matches(self.match_ops, env.now)
        for _, op in matches:
            self.modules['C'].buffer = op
            if all(prim.match_condition(self.modules) for prim in op['prims']):
                # found our operator! Perform action
                new_buffers = yield env.process(self.perform_action(env, op))
                module_resp_processes = self.module_responses(env, new_buffers)
                stop_requests = yield env.all_of(module_resp_processes)
                return any(stop_requests.values())
        return False  # no operator matched

    def match_ops(self, chunk):
        return chunk['isa'] == 'operator'

    def perform_action(self, env, operator):
        new_buffers = {}
        for i, prim in enumerate(operator['prims']):
            prim.fire(self.modules, new_buffers)
            # TODO:
            yield env.timeout(0.05 if i == 0 else 0.2)
        return new_buffers

    def module_responses(self, env, new_buffers):
        # NOT meant to be a simpy process. Yielding here is solely to build up
        # a list (of processes), not to wait for them to execute.
        for mod, new_buffer in new_buffers.items():
            c = Chunk(self.config, new_buffer)
            callback = mod.buffer_change(c, env)
            yield env.process(callback)
