from __future__ import annotations

import copy
from dataclasses import dataclass, field

from .template import Comparator, ComparatorResult, ProcessingContext

DEFAULT_MERGE_OWNED_KEYWORDS = {
    "$defs",
    "$ref",
    "$schema",
    "allOf",
    "anyOf",
    "contains",
    "else",
    "enum",
    "format",
    "if",
    "isPseudoArray",
    "items",
    "j2sElementTrigger",
    "not",
    "oneOf",
    "patternProperties",
    "prefixItems",
    "properties",
    "propertyNames",
    "required",
    "then",
    "type",
    "unevaluatedItems",
    "unevaluatedProperties",
}


@dataclass
class PreserveCommonKeywordsComparator(Comparator):
    """
    Restores shared schema-only keywords that the main merge pipeline does not
    rebuild on its own.

    The comparator is intended to run last in a chain. It inspects only input
    schema fragments from ``ctx.schemas`` and copies back identical keys that:

    - are present in every schema at the current level
    - are equal across all those schemas
    - are still absent from the merged node

    Structural keywords that belong to the merge itself (``type``,
    ``properties``, ``required``, ``anyOf``, etc.) are intentionally excluded.
    """

    name = "preserve-common-keywords"

    excluded_keywords: set[str] = field(default_factory=lambda: set(DEFAULT_MERGE_OWNED_KEYWORDS))

    def can_process(self, ctx: ProcessingContext, env: str, node: dict) -> bool:
        return any(isinstance(schema.content, dict) for schema in ctx.schemas)

    def process(self, ctx: ProcessingContext, env: str, node: dict) -> ComparatorResult:
        schema_dicts = [
            schema.content for schema in ctx.schemas if isinstance(schema.content, dict)
        ]
        if not schema_dicts:
            return None, None

        shared_keys = set(schema_dicts[0].keys())
        for schema in schema_dicts[1:]:
            shared_keys &= set(schema.keys())

        if not shared_keys:
            return None, None

        updates: dict = {}
        for key in sorted(shared_keys):
            if key in self.excluded_keywords or key in node:
                continue

            reference_value = schema_dicts[0][key]
            if all(schema.get(key) == reference_value for schema in schema_dicts[1:]):
                updates[key] = copy.deepcopy(reference_value)

        return (updates or None), None
