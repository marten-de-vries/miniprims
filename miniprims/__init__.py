from .chunk import Chunk
from .production import (SlotID, EmptyPRIM, EqualsPRIM, CopyPRIM, NotEmptyPRIM,
                         NotEqualsPRIM, RemovePRIM)
from .skill import Skill

__all__ = ('Model', 'Chunk', 'SlotID', 'EmptyPRIM', 'EqualsPRIM', 'CopyPRIM',
           'NotEmptyPRIM', 'NotEqualsPRIM', 'RemovePRIM', 'Skill')

# TODO:
# - proper declarative memory (incl. skills extension)
# - FIXMEs
# - spreading activation & skills (incl. proper context/goal tracking)
# - timings
# - operator compilation (bottom-up learning)
# - perceptual action PRIMs
# - imaginal + retrieval reinforcement

import simpy

from .modules import (Action, Constants, Declarative, Goal, Imaginal,
                      Procedural, Visual)
from .utils import Config


class Model:
    def __init__(self, name=None):
        self.name = name
        self.config = Config()

        self.action = Action(self.config)
        self.declarative = Declarative(self.config)
        self.goal = Goal(self.config)
        self.visual = Visual(self.config)
        self.imaginal = Imaginal(self.config)

        # used to map buffers to modules
        self.modules = {'AC': self.action, 'C': Constants(), 'G': self.goal,
                        'RT': self.declarative, 'V': self.visual,
                        'WM': self.imaginal}
        self.procedural = Procedural(self.config, self.modules)

        self.env = simpy.Environment()

    def chunk(self, *args, **kwargs):
        return Chunk.build(self.config, *args, **kwargs)

    def register_skill(self, name, skill):
        chunk = Chunk(self.config, skill.slots, name, 'skill')
        self.declarative.add_memory(chunk)

    def script(self, script):
        pass  # TODO

    def schedule_steps_until_done(self):
        return self.env.process(self._run())

    def schedule_step(self):
        return self.env.process(self.procedural.step(self.env))

    def _run(self):
        # TODO: reset buffers?
        # TODO: run script?
        stop = False
        while not stop:
            stop = yield self.schedule_step()
