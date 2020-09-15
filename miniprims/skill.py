import ast
import collections
import contextlib
import inspect
import textwrap

from .production import (CopyPRIM, EmptyPRIM, EqualsPRIM, NotEmptyPRIM,
                         NotEqualsPRIM, RemovePRIM, SlotID, SlotPlaceholder)


class Skill:
    """Syntactic sugar for defining operator, skill and skill instance
    chunks (the last one is TODO).

    """
    def __init__(self, **slots):
        self.slots = slots
        self.slots[1] = type(self).__name__

    def add_operators_to_memory(self, model):
        for attribute in self.__class__.__dict__.values():
            if not inspect.isfunction(attribute):
                continue
            self.to_operator(model, attribute)

    def to_operator(self, model, function):
        module = ast.parse(textwrap.dedent(inspect.getsource(function)))
        func, = module.body

        assert not func.decorator_list
        assert not func.returns
        with contextlib.suppress(AttributeError):
            assert not func.type_comment
        with contextlib.suppress(AttributeError):
            assert not func.args.posonlyargs
        assert func.args.args[0].arg == 'self'
        items = ((a.arg, i + 1) for i, a in enumerate(func.args.args[1:]))
        constants = collections.OrderedDict(items)

        condition = []
        action = []
        for expr in func.body:
            assert isinstance(expr, ast.Expr)
            if isinstance(expr.value, ast.Compare):
                assert not action
                condition.append(self.to_condition_prim(expr, constants))
            else:
                assert isinstance(expr.value, ast.BinOp)
                assert condition  # there should be at least one condition
                action.append(self.to_action_prim(expr, constants))
        prims = condition + action
        operator = model.chunk(func.name, 'operator', *constants.keys(),
                               prims=prims)
        model.declarative.add_memory(operator)

    def to_condition_prim(self, expr, constants):
        assert len(expr.value.ops) == 1
        assert len(expr.value.comparators) == 1
        # because we're still building the condition
        lhs = self.to_slot(expr.value.left, constants)
        rhs = self.to_slot(expr.value.comparators[0], constants)
        if isinstance(expr.value.ops[0], ast.Eq):
            return self.equality_prim(lhs, rhs)
        else:
            assert isinstance(expr.value.ops[0], ast.NotEq)
            return self.nonequality_prim(lhs, rhs)

    def equality_prim(self, lhs, rhs):
        if lhs and rhs:
            return EqualsPRIM(lhs, rhs)
        else:
            return EmptyPRIM(lhs or rhs)

    def nonequality_prim(self, lhs, rhs):
        if lhs and rhs:
            return NotEqualsPRIM(lhs, rhs)
        else:
            return NotEmptyPRIM(lhs or rhs)

    def to_slot(self, expr, constants):
        if isinstance(expr, ast.Subscript):
            assert isinstance(expr.value, ast.Name)
            assert isinstance(expr.slice, ast.Index)

            return SlotID(expr.value.id, self.index_num(expr.slice))
        elif isinstance(expr, ast.Name):
            return SlotID('C', constants[expr.id])
        elif isinstance(expr, ast.Attribute):
            assert isinstance(expr.value, ast.Name)
            assert expr.value.id == 'self'
            next_i = len(constants) + 1
            num = constants.setdefault(SlotPlaceholder(expr.attr), next_i)
            return SlotID('C', num)
        else:
            assert isinstance(expr, (ast.Constant, ast.NameConstant))
            assert expr.value is None
            return expr.value

    def index_num(self, expr):
        if isinstance(expr.value, ast.Constant):
            num = expr.value.value
        else:
            assert isinstance(expr.value, ast.Num)
            num = expr.value.n
        assert isinstance(num, int)
        return num

    def to_action_prim(self, expr, constants):
        assert isinstance(expr.value.op, ast.RShift)
        lhs = self.to_slot(expr.value.left, constants)
        rhs = self.to_slot(expr.value.right, constants)
        assert rhs
        if lhs:
            return CopyPRIM(lhs, rhs)
        else:
            return RemovePRIM(rhs)
