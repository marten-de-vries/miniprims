import numpy
import miniprims


def build_globals(model):  # noqa: C901 - complexity estimate is misleading
    def run_until_action(*action):
        model.action.interrupt_trigger = action
        return model.schedule_steps()

    def run_absolute_time_or_action(time, *action):
        model.action.interrupt_trigger = action
        return model.schedule_steps(until=time)

    def run_relative_time(time):
        return model.schedule_steps(model.env.time + time)

    def run_relative_time_or_action(time, *action):
        model.action.interrupt_trigger = action
        return run_relative_time(time)

    def instantiate_skill(skill, name, *args):
        slots = {1: skill, **dict(args)}
        chunk = miniprims.Chunk(model.config, slots, name, 'skill')
        model.declarative.add_memory(chunk, model.env.time)

    return {
        '__builtins__': {},  # not a hard sandbox, but nice for cleanliness

        # running the model
        'run-step': model.schedule_step,
        'run-until-action': run_until_action,
        'run-relative-time': run_relative_time,
        'run-absolute-time': model.schedule_steps,
        'run-relative-time-or-action': run_relative_time_or_action,
        'run-absolute-time-or-action': run_absolute_time_or_action,

        # perception and action
        'screen': model.visual.show,
        'last-action': lambda: list(model.action.buffer.slotslist),

        # run control of the model
        # TODO: trial-start
        'instantiate-skill': instantiate_skill,
        'trial-end': lambda: None,  # TODO: call reset?
        'issue-reward': lambda: None,  # TODO
        'sleep': model.env.timeout,

        # modification and inspection of the model
        'time': lambda: model.env.time,
        # TODO: add-dm
        # TODO: set-activation
        # TODO: set-sji
        # TODO: sgp
        # TODO: batch-parameters
        # TODO: set-skill
        # TODO: set-buffer-slot
        # TODO: get-buffer-slot

        # other commands and functions
        'print': print,
        'shuffle': numpy.random.permutation,
        'length': len,
        # TODO: set-data-file-field
        'random': lambda n: numpy.random.randint(n),
        # TODO: random-string
        'str-to-int': int,
        # TODO: set-graph-title
        # TODO: plot-point
        # TODO: set-average-window
    }
