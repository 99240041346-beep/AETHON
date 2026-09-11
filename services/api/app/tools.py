import ast
import operator as op
from aethon.schemas import ToolResult, ToolSpec, RiskClass
from aethon.web import WebFetcher
from aethon.web_search import WebSearch


class CalculatorTool:
    spec = ToolSpec(
        name='calculator',
        description='Evaluate a basic arithmetic expression safely.',
        input_schema={
            'type': 'object',
            'properties': {'expression': {'type': 'string', 'minLength': 1, 'maxLength': 1000}},
            'required': ['expression'],
            'additionalProperties': False,
        },
        output_schema={'type': 'number'},
        risk=RiskClass.LOW,
        side_effects=False,
        timeout_seconds=5,
        max_retries=0,
        authentication='owner',
        audit_required=True,
    )
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


class WebSearchTool:
    spec = ToolSpec(
        name='web_search',
        description='Search the public web for information.',
        input_schema={
            'type': 'object',
            'properties': {
                'query': {'type': 'string', 'minLength': 1, 'maxLength': 2000},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 10},
            },
            'required': ['query'],
            'additionalProperties': False,
        },
        output_schema={'type': 'array', 'items': {'type': 'object'}},
        risk=RiskClass.LOW,
        side_effects=False,
        timeout_seconds=15,
        max_retries=1,
        authentication='owner',
        audit_required=True,
    )

    def __init__(self, provider=None):
        self.provider = provider or WebSearch()

    def execute(self, query: str, limit: int = 5) -> ToolResult:
        try:
            results = self.provider.search(query, limit)
            return ToolResult(ok=True, output=[
                {'title': item.title, 'url': item.url, 'snippet': item.snippet, 'source': item.source}
                for item in results
            ])
        except Exception as exc:
            return ToolResult(ok=False, error=f'web search failed: {exc}')


class WebFetchTool:
    spec = ToolSpec(
        name='web_fetch',
        description='Fetch a public HTTP(S) web page with security limits.',
        input_schema={
            'type': 'object',
            'properties': {'url': {'type': 'string', 'format': 'uri', 'maxLength': 4000}},
            'required': ['url'],
            'additionalProperties': False,
        },
        output_schema={'type': 'object'},
        risk=RiskClass.LOW,
        side_effects=False,
        timeout_seconds=15,
        max_retries=1,
        authentication='owner',
        audit_required=True,
    )

    def __init__(self, fetcher=None):
        self.fetcher = fetcher or WebFetcher()

    def execute(self, url: str) -> ToolResult:
        try:
            result = self.fetcher.fetch(url)
            return ToolResult(ok=True, output=result)
        except Exception as exc:
            return ToolResult(ok=False, error=f'web fetch failed: {exc}')


class ToolRegistry:
    def __init__(self, web_search=None, web_fetch=None):
        self._tools = {
            'calculator': CalculatorTool(),
            'web_search': WebSearchTool(web_search),
            'web_fetch': WebFetchTool(web_fetch),
        }

    def list(self):
        return [tool.spec for tool in self._tools.values()]

    def execute(self, request):
        tool = self._tools.get(request.tool)
        if not tool:
            return ToolResult(ok=False, error='tool not found', request_id=request.request_id)
        try:
            result = tool.execute(**request.arguments)
            return result.model_copy(update={'request_id': request.request_id})
        except Exception as exc:
            return ToolResult(ok=False, error=f'tool execution failed: {exc}', request_id=request.request_id)
