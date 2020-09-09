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
        return args[0]

    def NIL(self, args):
        return None

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
        return ast.Name(args[0], ctx=ast.Load())

    def call(self, args):
        return ast.Call(args[0], args[1:], [])

    def array(self, args):
        return ast.List(args, ctx=ast.Load())

    def indexing(self, args):
        index = ast.Index(args[1], ctx=ast.Load)
        return ast.Subscript(args[0], index, ctx=ast.Load())

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
        variable = ast.Name(args[0], ctx=ast.Store())
        return ast.Assign([variable], args[1])

    def ifstmt(self, args):
        return ast.If(args[0], args[1], args[2] if len(args) == 3 else [])

    def whilestmt(self, args):
        return ast.While(*args, [])

    def body(self, args):
        return args
    actionprim = pair = body

    # skill
    def bufferslot(self, args):
        if len(args) == 1:
            return args[0]
        return miniprims.SlotID(*args)

    def bufferequal(self, args):
        return miniprims.EqualsPRIM(args[0], args[1])

    def bufferinequal(self, args):
        return miniprims.NotEqualsPRIM(args[0], args[1])

    prioritization = literal

    def operator(self, args):
        constants = {}
        condition = []
        action = []
        for arg in args[1:]:
            for index in [0, -1]:
                bufferslot = arg[index]
                if isinstance(bufferslot, str):
                    next_i = len(constants) + 1
                    slot_num = constants.setdefault(bufferslot, next_i)
                    arg[index] = miniprims.SlotID('C', slot_num)
            if isinstance(arg, list):
                action.append(miniprims.CopyPRIM(*arg))
            else:
                condition.append(arg)
        return self.model.chunk(args[0], 'operator', *constants.keys(),
                                condition=condition, action=action)

    def facts(self, args):
        for chunk in args:
            self.model.declarative.add_memory(chunk)

    def skill(self, args):
        # we do not really use the skill name in arg.children[0]...
        for chunk in args[1:]:
            self.model.declarative.add_memory(chunk)

    def action(self, args):
        name = args[0]
        opts = dict(args[1:])
        self.model.action.register(name, **opts)

    def script(self, args):
        assert not self.userscript

        self.userscript = ast.Module(args[0], [])
        ast.fix_missing_locations(self.userscript)

    def task(self, args):
        print("UNPROCESSED: task")

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
        return TreeLoader().transform(tree)
