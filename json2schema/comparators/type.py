from typing import Any

from .template import Comparator, ComparatorResult, ProcessingContext


def infer_json_type(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    return "any"


def infer_schema_type(s) -> None | str:
    if not isinstance(s, dict):
        return None
    if "type" in s:
        t = s["type"]
        if isinstance(t, str):
            return t
    if "properties" in s:
        return "object"
    if "items" in s:
        return "array"
    return None


class TypeComparator(Comparator):
    name = "type"

    def can_process(self, ctx: ProcessingContext, env: str, prev_result: dict) -> bool:
        return "type" not in prev_result and bool(ctx.schemas or ctx.jsons)

    def process(self, ctx: ProcessingContext, env: str, prev_result: dict) -> ComparatorResult:
        type_map = {}
        for s in ctx.schemas:
            t = infer_schema_type(s.content)
            if t:
                type_map.setdefault(t, set()).add(s.id)
        for j in ctx.jsons:
            t = infer_json_type(j.content)
            type_map.setdefault(t, set()).add(j.id)
        if not type_map:
            return None, None
        variants = [
            {"type": t, "j2sElementTrigger": sorted(list(ids))} for t, ids in type_map.items()
        ]
        if ctx.sealed:
            # cannot create Of inside sealed context — choose first deterministic
            return variants[0], None
        if len(variants) == 1:
            return variants[0], None
        return None, variants
