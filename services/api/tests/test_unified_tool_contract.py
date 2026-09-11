from uuid import UUID

from aethon.schemas import ToolRequest, ToolResult, ToolSpec, RiskClass
from aethon.tools import ToolRegistry


def test_tool_specs_expose_execution_contracts():
    specs = ToolRegistry().list()
    assert {spec.name for spec in specs} == {'calculator', 'web_search', 'web_fetch'}
    for spec in specs:
        assert isinstance(spec, ToolSpec)
        assert spec.input_schema['type'] == 'object'
        assert spec.output_schema
        assert spec.risk in RiskClass
        assert spec.timeout_seconds > 0
        assert spec.max_retries >= 0
        assert spec.authentication
        assert spec.audit_required is True


def test_tool_request_has_unique_request_id_and_result_propagates_it():
    first = ToolRequest(tool='calculator', arguments={'expression': '2 + 3'})
    second = ToolRequest(tool='calculator', arguments={'expression': '4 + 5'})
    assert first.request_id != second.request_id

    result = ToolRegistry().execute(first)
    assert result.ok is True
    assert result.output == 5
    assert result.request_id == first.request_id
    assert isinstance(result.request_id, UUID)


def test_unknown_tool_is_explicit_failure_not_exception():
    request = ToolRequest(tool='does_not_exist')
    result = ToolRegistry().execute(request)
    assert isinstance(result, ToolResult)
    assert result.ok is False
    assert result.request_id == request.request_id
    assert result.error == 'tool not found'
