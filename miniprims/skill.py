import ast
import inspect
import textwrap

from .prims import CopyPRIM, SlotID, EqualsPRIM, NotEqualsPRIM


class Skill:
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
        assert not func.type_comment
        assert not func.args.posonlyargs
        constants = [a.arg for a in func.args.args]

        condition = []
        action = []
        for expr in func.body:
            assert isinstance(expr, ast.Expr)
            if isinstance(expr.value, ast.Compare):
                assert not action
                condition.append(self.to_condition_prim(expr, constants))
            elif isinstance(expr.value, ast.BinOp):
                assert condition  # there should be at least one condition
                action.append(self.to_action_prim(expr, constants))
            else:
                assert False, f"unexpected expression type: {type(expr)}"
        operator = model.chunk(func.name, 'operator', *constants,
                               condition=condition, action=action)
        model.declarative.add_memory(operator)

    def to_condition_prim(self, expr, constants):
        assert len(expr.value.ops) == 1
        assert len(expr.value.comparators) == 1
        # because we're still building the condition
        lhs = self.to_slot(expr.value.left, constants)
        rhs = self.to_slot(expr.value.comparators[0], constants)
        if isinstance(expr.value.ops[0], ast.Eq):
            return EqualsPRIM(lhs, rhs)
        else:
            assert isinstance(expr.value.ops[0], ast.NotEq)
            return NotEqualsPRIM(lhs, rhs)

    def to_slot(self, expr, constants):
        if isinstance(expr, ast.Subscript):
            assert isinstance(expr.value, ast.Name)
            assert isinstance(expr.slice, ast.Index)
            assert isinstance(expr.slice.value, ast.Constant)

            assert isinstance(expr.slice.value.value, int)
            return SlotID(expr.value.id, expr.slice.value.value)
        elif isinstance(expr, ast.Name):
            return SlotID('C', constants.index(expr.id) + 1)
        else:
            assert isinstance(expr, ast.Constant)
            assert expr.value is None
            return expr.value

    def to_action_prim(self, expr, constants):
        assert isinstance(expr.value.op, ast.RShift)
        lhs = self.to_slot(expr.value.left, constants)
        rhs = self.to_slot(expr.value.right, constants)
        return CopyPRIM(lhs, rhs)
