"""
Tests for the calculator tool.

These tests import the SHIPPED implementation. An earlier version of this file
defined its own syntax-tree evaluator and tested that, while the tool the agents
can actually call filtered characters and used `eval`. The suite passed, the
production path was untested, and the two implementations had drifted: the copy
did not handle unary plus, so `2 + + 3` raised there and evaluated to 5 in
production.

Importing the real module is the point of this file. If the tool changes, these
tests change with it or fail.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from src.core.safe_math import (MAX_EXPONENT, MAX_EXPRESSION_LENGTH,
                                SafeCalculator, UnsafeExpression, calculate)


@pytest.fixture
def calculator():
    return SafeCalculator()


class TestArithmetic:
    """The operators a budget calculation actually needs."""

    def test_addition(self, calculator):
        assert calculator.evaluate("2 + 3") == 5
        assert calculator.evaluate("100 + 200") == 300
        assert calculator.evaluate("0 + 0") == 0

    def test_subtraction(self, calculator):
        assert calculator.evaluate("10 - 3") == 7
        assert calculator.evaluate("100 - 200") == -100

    def test_multiplication(self, calculator):
        assert calculator.evaluate("4 * 5") == 20
        assert calculator.evaluate("100 * 0") == 0

    def test_division(self, calculator):
        assert calculator.evaluate("10 / 2") == 5.0
        assert calculator.evaluate("7 / 2") == 3.5

    def test_floor_division(self, calculator):
        assert calculator.evaluate("7 // 2") == 3
        assert calculator.evaluate("10 // 3") == 3

    def test_modulo(self, calculator):
        assert calculator.evaluate("10 % 3") == 1
        assert calculator.evaluate("15 % 5") == 0

    def test_power(self, calculator):
        assert calculator.evaluate("2 ** 3") == 8
        assert calculator.evaluate("10 ** 2") == 100
        assert calculator.evaluate("5 ** 0") == 1

    def test_unary_minus(self, calculator):
        assert calculator.evaluate("-5") == -5
        assert calculator.evaluate("-10 + 3") == -7

    def test_unary_plus(self, calculator):
        """
        `2 + + 3` is valid arithmetic and evaluates to 5.

        The superseded copy of this evaluator omitted unary plus and raised
        here, and this test asserted the raise. The assertion documented a
        defect in the test's own copy rather than a property of the tool.
        """
        assert calculator.evaluate("2 + + 3") == 5
        assert calculator.evaluate("+7") == 7

    def test_precedence_and_parentheses(self, calculator):
        assert calculator.evaluate("2 + 3 * 4") == 14
        assert calculator.evaluate("(2 + 3) * 4") == 20
        assert calculator.evaluate("((2 + 3) * (4 + 1))") == 25
        assert calculator.evaluate("(10 + (5 * 2)) / 4") == 5.0

    def test_floating_point(self, calculator):
        assert calculator.evaluate("3.14 * 2") == pytest.approx(6.28)
        assert calculator.evaluate("10.5 + 4.5") == 15.0
        assert calculator.evaluate("1.5 ** 2") == 2.25

    def test_budget_calculations(self, calculator):
        """The expressions this tool exists to evaluate."""
        assert calculator.evaluate("3000 * 0.35") == 1050.0
        assert calculator.evaluate("3000 * 0.20") == 600.0
        assert calculator.evaluate("1050 / 7") == 150.0
        assert calculator.evaluate("(600 + 300) / 7") == pytest.approx(128.57, rel=0.01)


class TestRejectsNonArithmetic:
    """Anything that is not a number or an arithmetic operator must be refused."""

    @pytest.mark.parametrize("expression", [
        "print('hacked')",
        "len('test')",
        "eval('1+1')",
        "__import__('os').system('ls')",
        "''.join(['a', 'b'])",
        "'hello' + 'world'",
        "[1, 2, 3]",
        "sum([1, 2, 3])",
        "{'key': 'value'}",
        "(lambda x: x + 1)(5)",
        "[x for x in range(10)]",
        "open('/etc/passwd')",
        "True + 1",
        "1 if 1 else 2",
        "x + 1",
    ])
    def test_rejected(self, calculator, expression):
        with pytest.raises(UnsafeExpression):
            calculator.evaluate(expression)

    def test_rejection_is_a_value_error(self, calculator):
        """Callers catching ValueError keep working; UnsafeExpression subclasses it."""
        with pytest.raises(ValueError):
            calculator.evaluate("print(1)")


class TestResourceLimits:
    """
    The defect the character-filter implementation could not prevent.

    `9**9**9` passes any character allowlist and occupies the interpreter
    indefinitely. These tests fail against the previous implementation.
    """

    def test_rejects_exponent_bomb(self, calculator):
        with pytest.raises(UnsafeExpression):
            calculator.evaluate("9**9**9")

    def test_rejects_large_exponent(self, calculator):
        with pytest.raises(UnsafeExpression):
            calculator.evaluate(f"2 ** {MAX_EXPONENT + 1}")

    def test_allows_exponent_at_the_limit(self, calculator):
        assert calculator.evaluate(f"2 ** {MAX_EXPONENT}") == 2 ** MAX_EXPONENT

    def test_rejects_large_base(self, calculator):
        with pytest.raises(UnsafeExpression):
            calculator.evaluate("1e13 ** 10")

    def test_rejects_overlong_expression(self, calculator):
        with pytest.raises(UnsafeExpression):
            calculator.evaluate("1+" * MAX_EXPRESSION_LENGTH + "1")

    def test_evaluation_is_prompt(self, calculator):
        """A bounded expression must return immediately, not eventually."""
        import time
        start = time.time()
        with pytest.raises(UnsafeExpression):
            calculator.evaluate("9**9**9")
        assert time.time() - start < 1.0


class TestErrors:
    def test_syntax_error(self, calculator):
        with pytest.raises(UnsafeExpression):
            calculator.evaluate("(2 + 3")
        with pytest.raises(UnsafeExpression):
            calculator.evaluate("2 +")

    def test_empty_expression(self, calculator):
        with pytest.raises(UnsafeExpression):
            calculator.evaluate("")
        with pytest.raises(UnsafeExpression):
            calculator.evaluate("   ")

    def test_non_string_input(self, calculator):
        with pytest.raises(UnsafeExpression):
            calculator.evaluate(None)

    def test_division_by_zero(self, calculator):
        with pytest.raises(ZeroDivisionError):
            calculator.evaluate("10 / 0")


class TestToolBehaviour:
    """
    The function the MCP server exposes. It returns a string either way, because
    an exception crossing the tool boundary is reported to the agent as a
    transport failure rather than as a refusal it can act on.
    """

    def test_basic(self):
        assert calculate("200 * 7") == "1400"

    def test_complex(self):
        assert calculate("(3000 * 0.35) / 7") == "150.0"

    def test_returns_error_string_for_code(self):
        assert "Error" in calculate("print('test')")

    def test_returns_error_string_for_syntax(self):
        assert "Error" in calculate("(2 + 3")

    def test_returns_error_string_for_division_by_zero(self):
        assert "Error" in calculate("10 / 0")

    def test_returns_error_string_for_exponent_bomb(self):
        assert "Error" in calculate("9**9**9")

    def test_never_raises(self):
        """Whatever it is given, the tool returns a string."""
        for expression in ("", None, "1/0", "__import__('os')", "9**9**9", "2+2"):
            assert isinstance(calculate(expression), str)


def test_mcp_server_uses_this_implementation():
    """
    The server's tool must BE this code, not a copy of it.

    This test is the reason the file exists in its current form: without it,
    nothing stops the two drifting apart again.
    """
    from src.server import mcp_server
    assert mcp_server.calculate("9**9**9").startswith("Error")
    assert mcp_server.calculate("2 + 2") == "4"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
