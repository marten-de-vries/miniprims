"""Implementation details of PRIMs modules."""

import bisect
import math

import numpy

from .chunk import Chunk
from .production import Production


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
        return not self.buffer.slotslist

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
        search_slots = search_chunk.slotslist

        def match_cond(chunk):
            return search_slots == chunk.slotslist[:len(search_slots)]
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
        info = self.buffer.slotslist
        try:
            action, *args = info
        except ValueError:
            pass
        else:
            calculate_duration, output = self.actions[action]
            yield env.timeout(calculate_duration())
            print(f"{env.now:7.3f} {output} {' '.join(args)}")

        # if the interrupt trigger is in the buffer, stop.
        return self.interrupt_trigger == info[:len(self.interrupt_trigger)]


class Constants:
    """Not a module, just used to hold the current operator in its 'buffer'."""


class Procedural:
    def __init__(self, config, modules):
        self.config = config
        self.modules = modules
        self.declarative = modules['RT']

        self.productions = {}

    def step(self, env):
        # return True if the simulation should pause, else False
        matches = self.declarative.best_matches(self.match_ops, env.now)
        for _, op in matches:
            self.modules['C'].buffer = op
            op_productions = list(self.productions_for(op))
            productions_process = self.run_productions(env, op_productions)
            success, new_buffers = yield env.process(productions_process)
            if success:
                self.reinforce(op_productions)

                module_resp_processes = self.module_responses(env, new_buffers)
                stop_requests = yield env.all_of(module_resp_processes)
                return any(stop_requests.values())
        return False  # no operator matched

    def match_ops(self, chunk):
        return chunk['isa'] == 'operator'

    def productions_for(self, op):
        remaining = tuple(op['prims'])
        while remaining:
            # baseline: the single-PRIM production
            best_production = Production(self.config, prims=[remaining[0]],
                                         initial_utility=self.config['primU'])
            best_utility = best_production.utility

            noise_values = numpy.random.logistic(scale=self.config['egs'],
                                                 size=len(self.productions))
            for p, noise in zip(self.productions.values(), noise_values):
                utility = p.utility + noise
                is_best = (utility > best_utility and
                           p.prims == remaining[:len(p.prims)])
                if is_best:
                    best_utility = utility
                    best_production = p
            yield best_production
            remaining = remaining[len(best_production.prims):]

    def run_productions(self, env, productions):
        new_buffers = {}
        for i, production in enumerate(productions):
            match_condition = production.fire(self.modules, new_buffers)
            if i == 0:
                t = self.config['dat']
            else:
                t = self.config['production-prim-latency']
                self.compile(productions[i - 1], production)
            yield env.timeout(t)
            if not match_condition:
                # some production condition failed -> wrong operator
                return False, new_buffers
        return True, new_buffers

    def compile(self, a, b):
        prims = a.prims + b.prims
        try:
            production = self.productions[prims]
            production.reconstructed(a.utility)
        except KeyError:
            # new production, compile it
            utility = self.config['nu']
            self.productions[prims] = Production(self.config, prims, utility)

    def reinforce(self, op_productions):
        latency = self.config['production-prim-latency']

        for i, production in enumerate(op_productions):
            time_left = latency * (len(op_productions) - i - 1)
            production.succesfully_used(time_left)

    def module_responses(self, env, new_buffers):
        # NOT meant to be a simpy process. Yielding here is solely to build up
        # a list (of processes), not to wait for them to execute.
        for mod, new_buffer in new_buffers.items():
            c = Chunk(self.config, new_buffer)
            callback = mod.buffer_change(c, env)
            yield env.process(callback)
