from langchain.tools import tool
import ast
import operator


class SafeCalculator:
    """
    Safe arithmetic evaluator using AST parsing.
    Only allows: +, -, *, /, //, %, ** and numeric literals.
    Prevents arbitrary code execution that was possible with eval().
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
        """Safely evaluate a mathematical expression."""
        try:
            tree = ast.parse(expression, mode='eval')
            return self._eval_node(tree.body)
        except (SyntaxError, ValueError, TypeError) as e:
            raise ValueError(f"Invalid expression: {e}")
    
    def _eval_node(self, node):
        if isinstance(node, ast.Constant):  # Python 3.8+
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


# Singleton instance for the calculator
_safe_calculator = SafeCalculator()


class CalculatorTools():

    @tool("Make a calculation")
    def calculate(operation):
        """Useful to perform any mathematical calculations,
        like sum, minus, multiplication, division, etc.
        The input to this tool should be a mathematical
        expression, a couple examples are `200*7` or `5000/2*10`
        """
        try:
            result = _safe_calculator.evaluate(operation)
            return str(result)
        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error: Invalid syntax in mathematical expression - {e}"

