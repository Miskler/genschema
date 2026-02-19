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


def infer_schema_type(s: dict | str) -> None | str:
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


def _unique_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def infer_schema_types(s: dict | str) -> list[str]:
    """
    Return all detectable schema types.
    Unlike infer_schema_type(), this helper can extract types from unions
    (type list / anyOf / oneOf / allOf).
    """

    if not isinstance(s, dict):
        return []

    t = s.get("type")
    if isinstance(t, str):
        return [t]
    if isinstance(t, list):
        return _unique_keep_order([item for item in t if isinstance(item, str)])

    result: list[str] = []

    for key in ("anyOf", "oneOf"):
        variants = s.get(key)
        if isinstance(variants, list):
            for variant in variants:
                result.extend(infer_schema_types(variant))

    all_of = s.get("allOf")
    if isinstance(all_of, list):
        intersections: set[str] | None = None
        for variant in all_of:
            types = set(infer_schema_types(variant))
            if not types:
                continue
            intersections = types if intersections is None else (intersections & types)
        if intersections:
            result.extend(sorted(intersections))

    if result:
        return _unique_keep_order(result)

    inferred = infer_schema_type(s)
    if inferred:
        return [inferred]
    return []


class TypeComparator(Comparator):
    name = "type"

    def can_process(self, ctx: ProcessingContext, env: str, prev_result: dict) -> bool:
        return "type" not in prev_result and bool(ctx.schemas or ctx.jsons)

    def process(self, ctx: ProcessingContext, env: str, prev_result: dict) -> ComparatorResult:
        type_map: dict[str, set[str]] = {}

        for s in ctx.schemas:
            for t in infer_schema_types(s.content):
                type_map.setdefault(t, set()).add(s.id)

        for j in ctx.jsons:
            t = infer_json_type(j.content)
            type_map.setdefault(t, set()).add(j.id)

        # Нормализация: number поглощает integer
        if "number" in type_map and "integer" in type_map:
            type_map["number"].update(type_map["integer"])
            del type_map["integer"]

        if not type_map:
            return None, None

        variants: list[dict[str, Any]] = [
            {"type": t, "j2sElementTrigger": sorted(ids)} for t, ids in type_map.items()
        ]

        if ctx.sealed:
            # cannot create Of inside sealed context — choose first deterministic
            return variants[0], None

        if len(variants) == 1:
            return variants[0], None

        return None, variants
