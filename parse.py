import ast
import operator

import lark

import miniprims

parser = lark.Lark.open('prims.lark', rel_to=__file__, parser='lalr',
                        debug=True)

class TreeLoader(lark.Transformer):
    mp = ast.Name('miniprims', ast.Load())

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
        # TODO: use prefs
        return miniprims.Chunk(slots, name, isa='fact')

    # script
    def variable(self, args):
        return ast.Name(args[0], ctx=ast.Load())

    def call(self, args):
        return ast.Call(args[0], args[1:], [])

    def array(self, args):
        return ast.List(args, ctx=ast.Load())

    def indexing(self, args):
        return ast.Subscript(args[0], ast.Index(args[1], ctx=ast.Load), ctx=ast.Load())

    def literal(self, args):
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

    # skill
    def bufferslot(self, args):
        if len(args) == 1:
            return args[0]
        return miniprims.SlotID(*args)

    def bufferequal(self, args):
        return miniprims.EqualsPrim(args[0], args[1])

    def bufferinequal(self, args):
        return miniprims.NotEqualsPrim(args[0], args[1])

    def prioritization(self, args):
        return args[0]

    def actionprim(self, args):
        return args

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
                action.append(miniprims.CopyPrim(*arg))
            else:
                condition.append(arg)
        return miniprims.Chunk.build(args[0], 'operator', *constants.keys(),
                                     condition=condition, action=action)

    # model
    def start(self, args):
        model = miniprims.Model()
        script = None

        for arg in args:
            if arg.data == 'facts':
                for chunk in arg.children:
                    model.modules['RT'].memory.append(chunk)
            elif arg.data == 'script':
                assert not script
                script = ast.Module(arg.children[0], [])
                ast.fix_missing_locations(script)
            elif arg.data == 'skill':
                # we do not really use the skill name in arg.children[0]...
                for chunk in arg.children[1:]:
                    model.modules['RT'].memory.append(chunk)
            else:
                print('UNPROCESSED', arg.data)
        return script, model

filename = 'count.prims'
with open(filename) as f:
    tree = parser.parse(f.read())
    # print(tree.pretty())
    script, model = TreeLoader().transform(tree)
    # stress test correctness by converting/compiling the AST:
    import astor
    print(astor.to_source(script))
    compile(script, filename, "exec")
    # show resulting declarative memory
    for chunk in model.modules['RT'].memory:
        print(chunk)
