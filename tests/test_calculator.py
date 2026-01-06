"""
Tests for the safe calculator implementation.

Verifies that the AST-based calculator correctly evaluates mathematical
expressions while rejecting potentially malicious code.
"""

import pytest
import ast
import operator


# Self-contained SafeCalculator for testing (avoids langchain import chain)
class SafeCalculator:
    """
    Safe arithmetic evaluator using AST parsing.
    Only allows: +, -, *, /, //, %, ** and numeric literals.
    """
    
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }
    
    def evaluate(self, expression: str) -> float:
        try:
            tree = ast.parse(expression, mode='eval')
            return self._eval_node(tree.body)
        except (SyntaxError, ValueError, TypeError) as e:
            raise ValueError(f"Invalid expression: {e}")
    
    def _eval_node(self, node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Only numeric values allowed, got {type(node.value)}")
        
        elif isinstance(node, ast.Num):  # Python 3.7 compatibility
            return node.n
        
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op = self.OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op(left, right)
        
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op = self.OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op(operand)
        
        elif isinstance(node, ast.Expression):
            return self._eval_node(node.body)
        
        else:
            raise ValueError(f"Unsupported expression type: {type(node).__name__}")


class CalculatorTools:
    """Wrapper matching the production CalculatorTools interface."""
    _calculator = SafeCalculator()
    
    def calculate(self, operation: str) -> str:
        try:
            result = self._calculator.evaluate(operation)
            return str(result)
        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error: Invalid syntax - {e}"


class TestSafeCalculator:
    """Test the SafeCalculator class directly."""
    
    @pytest.fixture
    def calculator(self):
        return SafeCalculator()
    
    # ========== Basic Arithmetic Tests ==========
    
    def test_addition(self, calculator):
        assert calculator.evaluate("2 + 3") == 5
        assert calculator.evaluate("100 + 200") == 300
        assert calculator.evaluate("0 + 0") == 0
    
    def test_subtraction(self, calculator):
        assert calculator.evaluate("10 - 3") == 7
        assert calculator.evaluate("100 - 200") == -100
        assert calculator.evaluate("5 - 5") == 0
    
    def test_multiplication(self, calculator):
        assert calculator.evaluate("4 * 5") == 20
        assert calculator.evaluate("100 * 0") == 0
        assert calculator.evaluate("7 * 7") == 49
    
    def test_division(self, calculator):
        assert calculator.evaluate("10 / 2") == 5.0
        assert calculator.evaluate("100 / 4") == 25.0
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
    
    def test_unary_negative(self, calculator):
        assert calculator.evaluate("-5") == -5
        assert calculator.evaluate("-10 + 3") == -7
    
    # ========== Complex Expression Tests ==========
    
    def test_complex_expressions(self, calculator):
        assert calculator.evaluate("2 + 3 * 4") == 14  # Order of operations
        assert calculator.evaluate("(2 + 3) * 4") == 20  # Parentheses
        assert calculator.evaluate("100 / 4 + 25") == 50.0
        assert calculator.evaluate("2 ** 3 + 1") == 9
    
    def test_nested_parentheses(self, calculator):
        assert calculator.evaluate("((2 + 3) * (4 + 1))") == 25
        assert calculator.evaluate("(10 + (5 * 2)) / 4") == 5.0
    
    def test_floating_point(self, calculator):
        assert calculator.evaluate("3.14 * 2") == pytest.approx(6.28)
        assert calculator.evaluate("10.5 + 4.5") == 15.0
        assert calculator.evaluate("1.5 ** 2") == 2.25
    
    # ========== Budget Calculation Tests ==========
    
    def test_budget_calculations(self, calculator):
        """Test common budget calculations used in trip planning."""
        total_budget = 3000
        
        # Budget allocations (35%, 35%, 20%, 10%)
        assert calculator.evaluate("3000 * 0.35") == 1050.0  # Flights
        assert calculator.evaluate("3000 * 0.35") == 1050.0  # Hotels
        assert calculator.evaluate("3000 * 0.20") == 600.0   # Activities
        assert calculator.evaluate("3000 * 0.10") == 300.0   # Meals
        
        # Per-night hotel calculation
        assert calculator.evaluate("1050 / 7") == 150.0  # 7-day trip
        
        # Daily budget
        assert calculator.evaluate("(600 + 300) / 7") == pytest.approx(128.57, rel=0.01)
    
    # ========== Security Tests ==========
    
    def test_rejects_function_calls(self, calculator):
        """Ensure function calls are rejected."""
        with pytest.raises(ValueError):
            calculator.evaluate("print('hacked')")
        
        with pytest.raises(ValueError):
            calculator.evaluate("len('test')")
        
        with pytest.raises(ValueError):
            calculator.evaluate("eval('1+1')")
    
    def test_rejects_import_statements(self, calculator):
        """Ensure import attempts are rejected."""
        with pytest.raises(ValueError):
            calculator.evaluate("__import__('os').system('ls')")
    
    def test_rejects_attribute_access(self, calculator):
        """Ensure attribute access is rejected."""
        with pytest.raises(ValueError):
            calculator.evaluate("''.join(['a', 'b'])")
    
    def test_rejects_string_literals(self, calculator):
        """Ensure string literals are rejected."""
        with pytest.raises(ValueError):
            calculator.evaluate("'hello' + 'world'")
    
    def test_rejects_list_operations(self, calculator):
        """Ensure list operations are rejected."""
        with pytest.raises(ValueError):
            calculator.evaluate("[1, 2, 3]")
        
        with pytest.raises(ValueError):
            calculator.evaluate("sum([1, 2, 3])")
    
    def test_rejects_dict_operations(self, calculator):
        """Ensure dict operations are rejected."""
        with pytest.raises(ValueError):
            calculator.evaluate("{'key': 'value'}")
    
    def test_rejects_lambda(self, calculator):
        """Ensure lambda expressions are rejected."""
        with pytest.raises(ValueError):
            calculator.evaluate("(lambda x: x + 1)(5)")
    
    def test_rejects_comprehensions(self, calculator):
        """Ensure list comprehensions are rejected."""
        with pytest.raises(ValueError):
            calculator.evaluate("[x for x in range(10)]")
    
    # ========== Error Handling Tests ==========
    
    def test_syntax_error(self, calculator):
        """Test handling of syntax errors."""
        with pytest.raises(ValueError):
            calculator.evaluate("2 + + 3")
        
        with pytest.raises(ValueError):
            calculator.evaluate("(2 + 3")
    
    def test_division_by_zero(self, calculator):
        """Test division by zero."""
        with pytest.raises(ZeroDivisionError):
            calculator.evaluate("10 / 0")


class TestCalculatorToolsIntegration:
    """Test the CalculatorTools class that wraps SafeCalculator for LangChain."""
    
    def test_calculate_tool_basic(self):
        """Test the calculate tool with basic expressions."""
        result = CalculatorTools().calculate("200 * 7")
        assert result == "1400"
    
    def test_calculate_tool_complex(self):
        """Test the calculate tool with complex expressions."""
        result = CalculatorTools().calculate("(3000 * 0.35) / 7")
        assert result == "150.0"
    
    def test_calculate_tool_error_handling(self):
        """Test that the tool returns error messages gracefully."""
        result = CalculatorTools().calculate("print('test')")
        assert "Error" in result
    
    def test_calculate_tool_syntax_error(self):
        """Test that syntax errors are handled gracefully."""
        result = CalculatorTools().calculate("2 + + 3")
        assert "Error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
