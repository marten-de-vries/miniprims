import miniprims

import ast

import astor
import lark
import numpy

parser = lark.Lark.open('prims.lark', rel_to=__file__, parser='lalr',
                        debug=True, propagate_positions=True)


def build_globals(model):
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

    result = {
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
    return result


@lark.visitors.v_args(meta=True)
class TreeLoader(lark.Transformer):
    noop = ast.Expr(ast.Yield(ast.Call(ast.Name('sleep', ctx=ast.Load()),
                                       [ast.Constant(0)], [])))

    def __init__(self, filename, globals, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.filename = filename

        self.parsed_task = False
        self.model = miniprims.Model()
        self.globals = build_globals(self.model)
        self.constants = {}

    def copy_locs(self, source, target):
        target.lineno = source.line
        target.col_offset = source.column
        target.end_lineno = source.end_line
        target.end_col_offset = source.end_column
        return target

    # basic type conversions
    def ESCAPED_STRING(self, args):
        return ast.literal_eval(args)
    INT = SIGNED_NUMBER = ESCAPED_STRING

    def NAME(self, args):
        return str(args)
    BUFFER_NAME = NAME

    def literal(self, args, _):
        try:
            return args[0]
        except IndexError:
            return None  # nil

    prioritization = literal

    # facts
    def chunk(self, args, _):
        prefs = {}
        slots = {}
        for i, arg in enumerate(args):
            if arg.data == 'slot':
                slots[i] = arg.children[0]
            else:
                assert arg.data == 'pref'
                prefs[arg.children[0]] = arg.children[1]
        return miniprims.Chunk(self.model.config, slots, isa='fact', **prefs)

    # script
    def variable(self, args, meta):
        return self.copy_locs(meta, ast.Name(args[0], ast.Load()))

    def call(self, args, meta):
        name, *funcargs = args
        call = ast.Call(name, funcargs, [])
        if name.id.startswith('run-') or name == 'sleep':
            call = ast.Yield(call)
        return self.copy_locs(meta, call)

    def array(self, args, meta):
        return self.copy_locs(meta, ast.List(args, ast.Load()))

    def indexing(self, args, meta):
        index = ast.Index(args[1])
        return self.copy_locs(meta, ast.Subscript(args[0], index, ast.Load()))

    def codeliteral(self, args, meta):
        return self.copy_locs(meta, ast.Constant(args[0]))

    def expressionstatement(self, args, meta):
        return self.copy_locs(meta, ast.Expr(args[0]))

    def addition(self, args, meta):
        return self.copy_locs(meta, ast.BinOp(args[0], ast.Add(), args[1]))

    def equality(self, args, meta):
        comparison = ast.Compare(args[0], [ast.Eq()], [args[1]])
        return self.copy_locs(meta, comparison)

    def negation(self, args, meta):
        return self.copy_locs(meta, ast.UnaryOp(ast.Not(), args[0]))

    def assignment(self, args, meta):
        variable = ast.Name(args[0], ast.Store())
        return self.copy_locs(meta, ast.Assign([variable], args[1]))

    def ifstmt(self, args, meta):
        ifstmt = ast.If(args[0], args[1], args[2] if len(args) == 3 else [])
        return self.copy_locs(meta, ifstmt)

    def whilestmt(self, args, meta):
        return self.copy_locs(meta, ast.While(*args, []))

    def body(self, args, _):
        return args
    pair = body

    # skill
    def bufferslot(self, args, _):
        if len(args) == 1:
            return args[0]
        return miniprims.SlotID(*args)

    def equalsprim(self, args, _):
        return miniprims.EqualsPRIM(self._to_id(args[0]), self._to_id(args[1]))

    def _to_id(self, bufferslot):
        if isinstance(bufferslot, str):
            next_i = len(self.constants) + 1
            slot_num = self.constants.setdefault(bufferslot, next_i)
            bufferslot = miniprims.SlotID('C', slot_num)
        return bufferslot

    def notequalsprim(self, args, _):
        return miniprims.NotEqualsPRIM(self._to_id(args[0]),
                                       self._to_id(args[1]))

    def emptyprim(self, args, _):
        return miniprims.EmptyPRIM(self._to_id(args[0]))

    def notemptyprim(self, args, _):
        return miniprims.NotEmptyPRIM(self._to_id(args[0]))

    def copyprim(self, args, _):
        return miniprims.CopyPRIM(self._to_id(args[0]), self._to_id(args[1]))

    def removeprim(self, args, _):
        return miniprims.RemovePRIM(self._to_id(args[0]))

    def operator(self, args, _):
        constant_names = self.constants.keys()
        self.constants = {}  # prepare for the next operator
        return self.model.chunk(args[0], 'operator', *constant_names,
                                prims=args[1:])

    def facts(self, args, _):
        for chunk in args:
            self.model.declarative.add_memory(chunk)

    def skill(self, args, _):
        # add operators that are part of the skill
        for operator_chunk in args[1:]:
            self.model.declarative.add_memory(operator_chunk)

        # TODO: re-enable after activations have been figured out
        # ... and create a chunk for the skill itself
        # name = args[0]
        # skill_chunk = self.model.chunk(name, 'skill')
        # self.model.declarative.add_memory(skill_chunk)

    def action(self, args, _):
        name = args[0]
        opts = dict(args[1:])
        self.model.action.register(name, **opts)

    def scriptcode(self, args, meta):
        script = ast.parse("def script(): pass")
        script.body[0].body = args[0]
        # to make sure every script becomes a generator function
        script.body[0].body.append(self.noop)
        self.copy_locs(meta, script.body[0])
        ast.fix_missing_locations(script)

        print(astor.to_source(script))
        bytecode = compile(script, self.filename, "exec")
        scope = self.globals.copy()
        exec(bytecode, scope)
        return scope['script']

    def script(self, args, _):
        self.model.register_script(args[0])

    def initscript(self, args):
        self.model.register_init_script(args[0])

    def task(self, args, _):
        assert not self.parsed_task
        self.model.name = args[0]
        for key, value in args[1:]:
            self.model.config.override(key, value)
        self.parsed_task = True

    def true(self, args, _):
        return True

    def false(self, args, _):
        return False

    def initskills(self, args, _):
        self.model.goal.focus(*args)
        raise lark.visitors.Discard()

    # model
    def start(self, args, _):
        # check every definition has been handled by other visitor methods
        assert(a is None for a in args)
        return self.model


def load(filename):
    """Loads a (Swift) .prims file into a miniprims model, converting its
       scripts to a Python AST that can be exec'd easily.

    """
    with open(filename) as f:
        tree = parser.parse(f.read())
        # print(tree.pretty())
        # model is returned by the 'start' rule
        model = TreeLoader(filename, globals).transform(tree)
        return model
