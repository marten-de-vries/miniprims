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
        matches = self.declarative.best_matches(self._match_ops, env.now)
        for _, op in matches:
            if self.match_conditions(op):
                self.modules['C'].buffer = op

                # perform actions
                module_resp_processes = self.perform_actions(env, op)
                yield env.timeout(0.05)  # TODO
                stop_requests = yield env.all_of(module_resp_processes)
                return any(stop_requests.values())
        return False

    def _match_ops(self, chunk):
        return chunk['isa'] == 'operator'

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

    def perform_actions(self, env, operator):
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
            c = Chunk(self.config, new_buffer)
            callback = mod.buffer_change(c, env)
            yield env.process(callback)

    def slot_value(self, slotinfo):
        if not slotinfo:
            return None
        mod, slot = slotinfo
        return self.modules[mod].buffer[slot]
