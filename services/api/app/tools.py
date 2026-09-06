import ast
import operator as op
from aethon.schemas import ToolResult, ToolSpec, RiskClass

class CalculatorTool:
    spec = ToolSpec(name='calculator', description='Evaluate a basic arithmetic expression safely.', risk=RiskClass.LOW)
    _ops = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Mod: op.mod, ast.Pow: op.pow, ast.USub: op.neg}
    def execute(self, expression: str) -> ToolResult:
        try:
            tree = ast.parse(expression, mode='eval')
            value = self._eval(tree.body)
            return ToolResult(ok=True, output=value)
        except Exception as exc:
            return ToolResult(ok=False, error=f'invalid expression: {exc}')
    def _eval(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in self._ops:
            return self._ops[type(node.op)](self._eval(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in self._ops:
            return self._ops[type(node.op)](self._eval(node.left), self._eval(node.right))
        raise ValueError('only numeric arithmetic is allowed')

class ToolRegistry:
    def __init__(self): self._tools = {'calculator': CalculatorTool()}
    def list(self): return [tool.spec for tool in self._tools.values()]
    def execute(self, request):
        tool = self._tools.get(request.tool)
        if not tool: return ToolResult(ok=False, error='tool not found')
        return tool.execute(**request.arguments)
