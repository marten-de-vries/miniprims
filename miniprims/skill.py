import ast
import contextlib
import inspect
import textwrap

from .prims import (CopyPRIM, EmptyPRIM, EqualsPRIM, NotEmptyPRIM,
                    NotEqualsPRIM, RemovePRIM, SlotID)

# TODO: reverse logic. The model can call this, which also means we get rid of
# 'model' in the constructor & the other TODO.


class Skill:
    """Syntactic sugar for defining operator, skill and skill instance
    chunks (the last one is TODO).

    """
    def __init__(self, model):
        for attribute in self.__class__.__dict__.values():
            # TODO: check if operators already in model
            if not inspect.isfunction(attribute):
                continue
            self.to_operator(model, attribute)
        self.slots = {}  # TODO

    def to_operator(self, model, function):
        module = ast.parse(textwrap.dedent(inspect.getsource(function)))
        func, = module.body

        assert not func.decorator_list
        assert not func.returns
        with contextlib.suppress(AttributeError):
            assert not func.type_comment
        with contextlib.suppress(AttributeError):
            assert not func.args.posonlyargs
        constants = [a.arg for a in func.args.args]

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
        operator = model.chunk(func.name, 'operator', *constants,
                               prims=condition + action)
        model.declarative.add_memory(operator)

    def to_condition_prim(self, expr, constants):
        assert len(expr.value.ops) == 1
        assert len(expr.value.comparators) == 1
        # because we're still building the condition
        lhs = self.to_slot(expr.value.left, constants)
        rhs = self.to_slot(expr.value.comparators[0], constants)
        if isinstance(expr.value.ops[0], ast.Eq):
            if lhs and rhs:
                return EqualsPRIM(lhs, rhs)
            else:
                return EmptyPRIM(lhs or rhs)
        else:
            assert isinstance(expr.value.ops[0], ast.NotEq)
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
            return SlotID('C', constants.index(expr.id) + 1)
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
