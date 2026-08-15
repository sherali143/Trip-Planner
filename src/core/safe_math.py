"""
Arithmetic evaluation for the calculator tool, without `eval`.

Why this exists
---------------
The calculator tool is the one place in this system where text produced by a
language model is evaluated as code. The original implementation filtered the
input against a permitted character set and then called the interpreter's own
expression evaluator:

    allowed = set('0123456789+-*/().% ')
    if not all(c in allowed for c in operation):
        return "Error: Only mathematical expressions are allowed"
    result = eval(operation)

The character filter does block name lookups, so `__import__` and friends are
unreachable, and that is genuinely the hard part. What it does not block is
resource exhaustion: `9**9**9` is eight characters, passes the filter, and
occupies the interpreter indefinitely while allocating memory until the process
dies. A model that emits that string — by accident or because a user asked it
to — takes the server down.

The project's test suite appeared to cover this. It did not: it defined its own
syntax-tree evaluator inside the test file and exercised that, while the shipped
tool kept the character filter and the bare `eval`. A test that does not import
the code it claims to test provides assurance about nothing, and the two
implementations had already drifted apart. This module is the single
implementation, and `testing/test_calculator.py` imports it.

What is allowed
---------------
Numeric literals and the binary and unary arithmetic operators. Names, calls,
attributes, subscripts, comparisons and everything else raise. Exponentiation is
additionally bounded, because it is the one operator whose cost is not
proportional to the length of the expression.
"""

from __future__ import annotations

import ast
import operator
from typing import Any, Callable, Dict, Union

Number = Union[int, float]

# Only arithmetic. Bitwise operators are excluded deliberately: they have no
# meaning in a travel budget and `<<` is another cheap way to allocate a very
# large integer.
_OPERATORS: Dict[type, Callable[..., Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Bounds on exponentiation. A budget calculation never needs more than these,
# and without them a short expression can consume unbounded time and memory.
MAX_EXPONENT = 64
MAX_POW_BASE = 1e12

# Longest accepted expression. A genuine budget sum is far shorter; a very long
# one is either a mistake or an attempt to find a slow path.
MAX_EXPRESSION_LENGTH = 200


class UnsafeExpression(ValueError):
    """The expression is not simple arithmetic, or is too expensive to evaluate."""


class SafeCalculator:
    """Evaluates arithmetic expressions by walking the syntax tree."""

    OPERATORS = _OPERATORS

    def evaluate(self, expression: str) -> Number:
        """
        Evaluate `expression` and return its numeric value.

        Raises UnsafeExpression (a ValueError) for anything that is not plain
        arithmetic, so callers can treat every rejection the same way.
        """
        if not isinstance(expression, str):
            raise UnsafeExpression(f"expected a string, got {type(expression).__name__}")
        text = expression.strip()
        if not text:
            raise UnsafeExpression("empty expression")
        if len(text) > MAX_EXPRESSION_LENGTH:
            raise UnsafeExpression(
                f"expression is {len(text)} characters, over the "
                f"{MAX_EXPRESSION_LENGTH}-character limit")
        try:
            tree = ast.parse(text, mode="eval")
        except SyntaxError as exc:
            raise UnsafeExpression(f"invalid syntax: {exc.msg}") from exc
        return self._eval(tree.body)

    def _eval(self, node: ast.AST) -> Number:
        if isinstance(node, ast.Expression):
            return self._eval(node.body)

        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise UnsafeExpression(
                    f"only numbers are allowed, got {type(node.value).__name__}")
            return node.value

        if isinstance(node, ast.BinOp):
            op = self.OPERATORS.get(type(node.op))
            if op is None:
                raise UnsafeExpression(
                    f"unsupported operator: {type(node.op).__name__}")
            left, right = self._eval(node.left), self._eval(node.right)
            if isinstance(node.op, ast.Pow):
                self._check_power(left, right)
            return op(left, right)

        if isinstance(node, ast.UnaryOp):
            op = self.OPERATORS.get(type(node.op))
            if op is None:
                raise UnsafeExpression(
                    f"unsupported operator: {type(node.op).__name__}")
            return op(self._eval(node.operand))

        # Everything else — names, calls, attributes, subscripts, comparisons,
        # comprehensions, lambdas — is rejected by falling through to here.
        raise UnsafeExpression(
            f"{type(node).__name__} is not allowed in an arithmetic expression")

    @staticmethod
    def _check_power(base: Number, exponent: Number) -> None:
        """
        Reject exponentiation that would be expensive.

        Checked before the operator runs rather than after, because after is too
        late: evaluating 9**9**9 is what has to be prevented, not detected.
        """
        if abs(exponent) > MAX_EXPONENT:
            raise UnsafeExpression(
                f"exponent {exponent} exceeds the limit of {MAX_EXPONENT}")
        if abs(base) > MAX_POW_BASE:
            raise UnsafeExpression(
                f"base {base} exceeds the limit of {MAX_POW_BASE:.0f} for exponentiation")


_CALCULATOR = SafeCalculator()


def calculate(operation: str) -> str:
    """
    The calculator tool's behaviour: evaluate, or return a readable error.

    Returns a string because this is what an agent receives as a tool result; an
    exception crossing that boundary would be reported as a transport failure
    rather than as "that expression is not allowed".
    """
    try:
        return str(_CALCULATOR.evaluate(operation))
    except UnsafeExpression as exc:
        return f"Error: {exc}"
    except ZeroDivisionError:
        return "Error: Division by zero"
    except (OverflowError, MemoryError) as exc:
        return f"Error: result too large ({type(exc).__name__})"
    except Exception as exc:  # never let the tool layer raise into the agent
        return f"Error: {exc}"
