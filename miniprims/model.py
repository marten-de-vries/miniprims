import simpy

from .chunk import Chunk
from .modules import Action, Constants, Declarative, Goal, Imaginal, Visual
from .utils import Config


class Model:
    def __init__(self, name=None):
        self.name = name
        self.config = Config()

        self.action = Action(self.config)
        self.declarative = Declarative(self.config)
        self.visual = Visual(self.config)
        self.modules = {'AC': self.action, 'C': Constants(),
                        'G': Goal(self.config), 'RT': self.declarative,
                        'V': self.visual, 'WM': Imaginal(self.config)}
        self.env = simpy.Environment()
        self.env.process(self._run())

    def chunk(self, *args, **kwargs):
        return Chunk.build(self.config, *args, **kwargs)

    def register_skill(self, name, skill):
        chunk = Chunk(self.config, skill.slots, name, 'skill')
        self.declarative.add_memory(chunk)

    def focus(self, skills):
        pass  # TODO

    def script(self, script):
        pass  # TODO

    def _run(self):
        while True:
            # reset buffers?
            # run script
            while True:
                step = self._run_prims(self.env.active_process)

                try:
                    yield self.env.process(step)
                except simpy.Interrupt:
                    break  # we're done with this simulation round
            break  # TODO: remove

    def _match_ops(self, chunk):
        return chunk['isa'] == 'operator'

    def _run_prims(self, parent):
        matches = self.declarative.best_matches(self._match_ops, self.env.now)
        for _, op in matches:
            if self.match_conditions(op):
                self.modules['C'].buffer = op

                # perform actions
                module_response_processes = self.perform_actions(op, parent)
                yield self.env.timeout(0.05)  # TODO
                yield self.env.all_of(module_response_processes)
                break

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

    def perform_actions(self, operator, parent):
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
            callback = mod.buffer_change(c, self.env, parent)
            yield self.env.process(callback)

    def slot_value(self, slotinfo):
        if not slotinfo:
            return None
        mod, slot = slotinfo
        return self.modules[mod].buffer[slot]
