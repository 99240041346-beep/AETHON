from __future__ import annotations

import csv
import io
import json
import math
from typing import Any

from aethon.schemas import RiskClass, ToolResult, ToolSpec


class DataAnalysisTool:
    spec = ToolSpec(
        name="data_analyze",
        description="Analyze bounded CSV or JSON data supplied inline and return schema, statistics, and a compact summary.",
        input_schema={
            "type": "object",
            "properties": {
                "data": {"type": "string", "minLength": 1, "maxLength": 200000},
                "format": {"type": "string", "enum": ["csv", "json"]},
            },
            "required": ["data", "format"],
            "additionalProperties": False,
        },
        output_schema={"type": "object"},
        risk=RiskClass.LOW,
        side_effects=False,
        timeout_seconds=10,
        max_retries=0,
        authentication="owner",
        audit_required=True,
    )

    def execute(self, data: str, format: str) -> ToolResult:
        try:
            rows = self._parse(data, format)
            if not rows:
                return ToolResult(ok=False, error="dataset contains no rows")
            columns = sorted({key for row in rows for key in row})
            stats = {}
            for column in columns:
                values = [row.get(column) for row in rows]
                numeric = [float(v) for v in values if self._number(v)]
                stats[column] = {
                    "non_null": sum(v not in (None, "") for v in values),
                    "unique": len({str(v) for v in values if v not in (None, "")}),
                    "numeric": bool(numeric),
                    "min": min(numeric) if numeric else None,
                    "max": max(numeric) if numeric else None,
                    "mean": sum(numeric) / len(numeric) if numeric else None,
                }
            return ToolResult(ok=True, output={
                "rows": len(rows),
                "columns": columns,
                "statistics": stats,
                "sample": rows[:5],
            }, verified=True)
        except Exception as exc:
            return ToolResult(ok=False, error=f"data analysis failed: {exc}")

    @staticmethod
    def _number(value: Any) -> bool:
        try:
            if value in (None, ""):
                return False
            number = float(value)
            return math.isfinite(number)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _parse(data: str, format: str) -> list[dict[str, Any]]:
        if format == "json":
            value = json.loads(data)
            if isinstance(value, dict):
                value = value.get("rows", [value])
            if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
                raise ValueError("JSON must be an object list or {rows:[...]}")
            return value
        reader = csv.DictReader(io.StringIO(data))
        return [dict(row) for row in reader]
