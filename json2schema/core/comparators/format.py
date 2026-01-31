import re
from typing import Optional, Any, Dict, List
from .template import Comparator, ProcessingContext, ComparatorResult

class FormatDetector:
    """Глобальный детектор форматов. Расширяем — просто добавляем в _registry."""

    _registry = {
        "string": {
            re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"): "email",
            re.compile(
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
                re.I,
            ): "uuid",
            re.compile(r"^\d{4}-\d{2}-\d{2}$"): "date",
            re.compile(
                r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$"
            ): "date-time",
            re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.I): "uri",
            re.compile(
                r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}" r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
            ): "ipv4",
        }
    }

    @classmethod
    def detect(cls, value: Any, type_hint: str = "string") -> Optional[str]:
        patterns = cls._registry.get(type_hint, {})
        for pattern, name in patterns.items():
            if pattern.fullmatch(str(value)):
                return name
        return None

class FormatComparator(Comparator):
    name = "format"

    def can_process(self, ctx: ProcessingContext, env: str, prev_result: Dict) -> bool:
        # Форматы только если есть string (в том числе в anyOf/oneOf/allOf)
        def has_string_type(node):
            if isinstance(node, dict):
                if node.get("type") == "string":
                    return True
                for key in ["anyOf", "oneOf", "allOf"]:
                    if key in node and any(has_string_type(child) for child in node[key]):
                        return True
            return False
        return has_string_type(prev_result)

    def process(self, ctx: ProcessingContext, env: str, prev_result: Dict):
        # Рекурсивно обходим node, модифицируем все элементы type="string"
        def apply_format(node: Dict) -> List[Dict]:
            if "type" in node and node["type"] == "string":
                base_triggers = set(node.get("j2sElementTrigger", []))
                variants_map: Dict[Optional[str], set[int]] = {None: set(base_triggers)}

                # Форматы из схем
                for s in ctx.schemas:
                    if isinstance(s.content, dict) and s.content.get("type") == "string":
                        fmt = s.content.get("format")
                        variants_map.setdefault(fmt, set()).add(s.id)
                        if fmt is not None:
                            variants_map[None].discard(s.id)

                # Форматы из JSON
                for j in ctx.jsons:
                    if isinstance(j.content, str):
                        fmt = FormatDetector.detect(j.content, type_hint="string")
                        variants_map.setdefault(fmt, set()).add(j.id)
                        if fmt is not None:
                            variants_map[None].discard(j.id)

                # Формируем список вариантов
                variants = []
                for fmt, ids in variants_map.items():
                    if not ids:
                        continue
                    var = {"type": "string", "j2sElementTrigger": sorted(ids)}
                    if fmt is not None:
                        var["format"] = fmt
                    variants.append(var)

                # Только один вариант → возвращаем его напрямую
                if len(variants) == 1:
                    return [variants[0]]
                return variants

            # Рекурсивно обходим anyOf/oneOf/allOf
            for key in ["anyOf", "oneOf", "allOf"]:
                if key in node:
                    new_list = []
                    for child in node[key]:
                        new_list.extend(apply_format(child))
                    node[key] = new_list
            return [node]



        updated_nodes = apply_format(dict(prev_result))
        if len(updated_nodes) == 1:
            return updated_nodes[0], None
        else:
            return None, updated_nodes
