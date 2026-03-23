"""Enum inference comparator.

This module contains :class:`EnumComparator`, a comparator that promotes
low-cardinality scalar fields to JSON Schema ``enum`` definitions.
It is designed to work with mixed input sources:

- raw JSON instances added via :meth:`genschema.pipeline.Converter.add_json`
- existing JSON Schemas added via :meth:`genschema.pipeline.Converter.add_schema`

The comparator is intentionally conservative. If a field looks unsafe for enum
inference, it stores a reject flag directly in the generated schema so the same
field will not be reconsidered as an enum candidate on future runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .template import Comparator, ComparatorResult, ProcessingContext

ENUM_REJECT_FLAG = "j2sEnumRejected"


@dataclass
class EnumComparator(Comparator):
    """Infer ``enum`` for compact scalar fields and persist rejection decisions."""

    name = "enum"

    max_unique_values: int = 16
    """Maximum number of distinct values allowed for enum inference."""

    max_avg_string_length: int = 20
    """Maximum average length of unique string values before the field is treated as free text."""

    excluded_field_names: set[str] = field(
        default_factory=lambda: {
            "name",
            "title",
            "description",
            "message",
            "text",
        }
    )
    """Field names that must be excluded from enum inference."""

    reject_flag: str = ENUM_REJECT_FLAG
    """Schema flag that persists enum rejection across repeated runs."""

    def _extract_field_name(self, env: str) -> str | None:
        """Extract the current property name from a pipeline path.

        Parameters
        ----------
        env:
            Internal path used by the converter, for example
            ``"/properties/status"`` or
            ``"/properties/meta/properties/status"``.

        Returns
        -------
        str | None
            The innermost property name for ``/properties/...`` paths, or
            ``None`` when the current node is not a named object property.
        """
        marker = "/properties/"
        if marker not in env:
            return None
        return env.rsplit(marker, 1)[-1].split("/", 1)[0]

    def _schema_type_matches(self, schema: Any, expected_type: str) -> bool:
        """Return ``True`` when a schema node explicitly matches the target type."""
        return isinstance(schema, dict) and schema.get("type") == expected_type

    def _collect_schema_values(self, ctx: ProcessingContext, expected_type: str) -> list[str | int]:
        """Collect candidate enum values from input schemas.

        Only explicit schema enums from nodes whose ``type`` matches
        ``expected_type`` are considered.
        """
        values: list[str | int] = []
        for schema in ctx.schemas:
            content = schema.content
            if not self._schema_type_matches(content, expected_type):
                continue
            enum_values = content.get("enum")
            if not isinstance(enum_values, list):
                continue
            for value in enum_values:
                if expected_type == "string" and isinstance(value, str):
                    values.append(value)
                elif (
                    expected_type == "integer"
                    and isinstance(value, int)
                    and not isinstance(value, bool)
                ):
                    values.append(value)
        return values

    def _collect_json_values(self, ctx: ProcessingContext, expected_type: str) -> list[str | int]:
        """Collect candidate enum values from raw JSON resources."""
        values: list[str | int] = []
        for resource in ctx.jsons:
            value = resource.content
            if expected_type == "string" and isinstance(value, str):
                values.append(value)
            elif (
                expected_type == "integer"
                and isinstance(value, int)
                and not isinstance(value, bool)
            ):
                values.append(value)
        return values

    def _has_schema_flag(self, ctx: ProcessingContext, flag_name: str) -> bool:
        """Check whether any input schema already contains the reject flag."""
        for schema in ctx.schemas:
            if isinstance(schema.content, dict) and schema.content.get(flag_name) is True:
                return True
        return False

    def _first_schema_format(self, ctx: ProcessingContext) -> str | None:
        """Return the first explicit schema format declared for the current node."""
        for schema in ctx.schemas:
            content = schema.content
            if not isinstance(content, dict):
                continue
            format_value = content.get("format")
            if isinstance(format_value, str):
                return format_value
        return None

    def _reject(self, extra: dict[str, Any] | None = None) -> ComparatorResult:
        """Build a rejection result that persists the enum reject flag."""
        result: dict[str, Any | bool] = {self.reject_flag: True}
        if extra:
            result.update(extra)
        return result, None

    def can_process(self, ctx: ProcessingContext | None, env: str, prev_result: dict) -> bool:
        """Decide whether enum inference should run for the current node.

        The comparator only participates for scalar nodes that still do not have
        a final enum decision. Excluded field names are intentionally *not*
        filtered here, because they still need to be processed in order to write
        the persistent reject flag.
        """
        current_type = prev_result.get("type")
        if current_type not in {"string", "integer"}:
            return False
        if prev_result.get(self.reject_flag) is True:
            return False
        if "enum" in prev_result:
            return False
        if "format" in prev_result:
            return False

        return True

    def process(self, ctx: ProcessingContext, env: str, prev_result: dict) -> ComparatorResult:
        """Infer enum values or persist a rejection marker.

        The method merges candidate values from schema enums and JSON payloads,
        deduplicates them while preserving order, and applies the configured
        heuristics. If the field is rejected, the existing enum is effectively
        removed because the returned update contains only the reject marker and
        omits ``enum``.
        """
        current_type = prev_result["type"]
        schema_format = self._first_schema_format(ctx)

        if schema_format is not None:
            return self._reject({"format": schema_format})

        if self._has_schema_flag(ctx, self.reject_flag):
            return self._reject()

        field_name = self._extract_field_name(env)
        if field_name in self.excluded_field_names:
            return self._reject()

        values = self._collect_schema_values(ctx, current_type)
        values.extend(self._collect_json_values(ctx, current_type))

        if not values:
            return None, None

        unique_values = list(dict.fromkeys(values))
        if len(unique_values) > self.max_unique_values:
            return self._reject()

        if current_type == "string":
            string_values = [value for value in unique_values if isinstance(value, str)]
            avg_length = sum(len(value) for value in string_values) / len(string_values)
            if avg_length > self.max_avg_string_length:
                return self._reject()

        return {"enum": unique_values}, None
