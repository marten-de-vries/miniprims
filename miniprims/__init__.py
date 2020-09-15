from .chunk import Chunk
from .production import (SlotID, SlotPlaceholder, EmptyPRIM, EqualsPRIM,
                         CopyPRIM, NotEmptyPRIM, NotEqualsPRIM, RemovePRIM)
from .skill import Skill

__all__ = ('Model', 'Chunk', 'SlotID', 'SlotPlaceholder', 'EmptyPRIM',
           'EqualsPRIM', 'CopyPRIM', 'NotEmptyPRIM', 'NotEqualsPRIM',
           'RemovePRIM', 'Skill')

# TODO:
# - proper declarative memory (incl. skills extension)
# - FIXMEs
# - spreading activation & skills (incl. proper context/goal tracking)
# - timings
# - operator compilation (bottom-up learning)
# - perceptual action PRIMs
# - imaginal + retrieval reinforcement

from .modules import (Action, Constants, Declarative, Goal, Imaginal,
                      Procedural, Visual)
from .utils import Config, Environment


class Model:
    def __init__(self, name=None):
        self.name = name
        self.init_script = None
        self.script = None

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

        self.env = Environment()
        self.start_time = 0
        self.init_script_ran = False
        self._current_step = self.env.timeout(0)
        self.skills = set()

    def chunk(self, *args, **kwargs):
        return Chunk.build(self.config, *args, **kwargs)

    def register_skill(self, name, skill):
        if type(skill) not in self.skills:
            skill.add_operators_to_memory(self)
            self.skills.add(type(skill))
        chunk = Chunk(self.config, skill.slots, name, 'skill')
        self.declarative.add_memory(chunk)

    def register_script(self, script):
        assert not self.script
        self.script = script

    def register_init_script(self, script):
        assert not self.init_script
        self.init_script = script

    def schedule_steps(self, until=float('inf')):
        return self.env.process(self._steps(until))

    def _steps(self, until):
        stop = False
        while self.env.time < until and not stop:
            stop = yield self.schedule_step()

    def schedule_step(self):
        self._current_step = self.env.process(self.procedural.step(self.env))
        return self._current_step

    @property
    def current_step(self):
        if self._current_step.processed:
            # we're waiting for the model to start again
            return self.env.timeout(0)
        return self._current_step

    def schedule_run(self, times=1):
        return self.env.process(self._run(times))

    def _run(self, times):
        if self.init_script and not self.init_script_ran:
            yield self.env.process(self.init_script())
            self.init_script_ran = True
        for _ in range(times):
            if self.script:
                yield self.env.process(self.script())
            self.reset()  # TODO: leave it to the script itself?

    def reset(self):
        for module in self.modules.values():
            module.reset()
        self.env.start_time = self.env.now
