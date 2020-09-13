import miniprims

import ast

import lark

parser = lark.Lark.open('prims.lark', rel_to=__file__, parser='lalr',
                        debug=True)


class TreeLoader(lark.Transformer):
    mp = ast.Name('miniprims', ast.Load())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.userscript = None
        self.model = miniprims.Model()
        self.constants = {}

    # basic type conversions
    def ESCAPED_STRING(self, args):
        return ast.literal_eval(args)

    def INT(self, args):
        return int(args)

    def SIGNED_NUMBER(self, args):
        return float(args)

    def NAME(self, args):
        return str(args)
    BUFFER_NAME = NAME

    def literal(self, args):
        try:
            return args[0]
        except IndexError:
            return None  # nil

    prioritization = literal

    # facts
    def chunk(self, args):
        prefs = {}
        slots = {}
        for i, arg in enumerate(args):
            if i == 0:
                name = arg
            elif arg.data == 'slot':
                slots[i] = arg.children[0]
            else:
                assert arg.data == 'pref'
                prefs[arg.children[0]] = arg.children[1]
        return miniprims.Chunk(self.model.config, slots, name, 'fact', **prefs)

    # script
    def variable(self, args):
        return ast.Name(args[0], ast.Load())

    def call(self, args):
        return ast.Call(args[0], args[1:], [])

    def array(self, args):
        return ast.List(args, ast.Load())

    def indexing(self, args):
        index = ast.Index(args[1])
        return ast.Subscript(args[0], index, ast.Load())

    def codeliteral(self, args):
        return ast.Constant(args[0])

    def expressionstatement(self, args):
        return ast.Expr(args[0])

    def addition(self, args):
        return ast.BinOp(args[0], ast.Add(), args[1])

    def equality(self, args):
        return ast.Compare(args[0], [ast.Eq()], [args[1]])

    def negation(self, args):
        return ast.UnaryOp(ast.Not(), args[0])

    def assignment(self, args):
        variable = ast.Name(args[0], ast.Store())
        return ast.Assign([variable], args[1])

    def ifstmt(self, args):
        return ast.If(args[0], args[1], args[2] if len(args) == 3 else [])

    def whilestmt(self, args):
        return ast.While(*args, [])

    def body(self, args):
        return args
    pair = body

    # skill
    def bufferslot(self, args):
        if len(args) == 1:
            return args[0]
        return miniprims.SlotID(*args)

    def equalsprim(self, args):
        return miniprims.EqualsPRIM(self._to_id(args[0]), self._to_id(args[1]))

    def _to_id(self, bufferslot):
        if isinstance(bufferslot, str):
            next_i = len(self.constants) + 1
            slot_num = self.constants.setdefault(bufferslot, next_i)
            bufferslot = miniprims.SlotID('C', slot_num)
        return bufferslot

    def notequalsprim(self, args):
        return miniprims.NotEqualsPRIM(self._to_id(args[0]),
                                       self._to_id(args[1]))

    def emptyprim(self, args):
        return miniprims.EmptyPRIM(self._to_id(args[0]))

    def notemptyprim(self, args):
        return miniprims.NotEmptyPRIM(self._to_id(args[0]))

    def copyprim(self, args):
        return miniprims.CopyPRIM(self._to_id(args[0]), self._to_id(args[1]))

    def removeprim(self, args):
        return miniprims.RemovePRIM(self._to_id(args[0]))

    def operator(self, args):
        constant_names = self.constants.keys()
        self.constants = {}  # prepare for the next operator
        return self.model.chunk(args[0], 'operator', *constant_names,
                                prims=args[1:])

    def facts(self, args):
        for chunk in args:
            self.model.declarative.add_memory(chunk)

    def skill(self, args):
        # add operators that are part of the skill
        for operator_chunk in args[1:]:
            self.model.declarative.add_memory(operator_chunk)

        # TODO: re-enable after activations have been figured out
        # ... and create a chunk for the skill itself
        # name = args[0]
        # skill_chunk = self.model.chunk(name, 'skill')
        # self.model.declarative.add_memory(skill_chunk)

    def action(self, args):
        name = args[0]
        opts = dict(args[1:])
        self.model.action.register(name, **opts)

    def script(self, args):
        assert not self.userscript

        self.userscript = ast.parse("")
        self.userscript.body = args[0]
        ast.fix_missing_locations(self.userscript)

    def task(self, args):
        self.model.name = args[0]
        for key, value in args[1:]:
            self.model.config.override(key, value)

    def true(self, args):
        return True

    def false(self, args):
        return False

    def initskills(self, args):
        self.model.goal.focus(*args)
        raise lark.visitors.Discard()

    # model
    def start(self, args):
        # check every definition has been handled by other visitor methods
        assert(a is None for a in args)
        return self.userscript, self.model


def load(filename):
    """Loads a (Swift) .prims file into a miniprims model, converting its
       scripts to a Python AST that can be exec'd easily.

    """
    with open(filename) as f:
        tree = parser.parse(f.read())
        # print(tree.pretty())
        script, model = TreeLoader().transform(tree)
        return script, model
