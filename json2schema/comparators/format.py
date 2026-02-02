import re
from collections import defaultdict
from functools import lru_cache
from typing import Any, Optional

from .template import Comparator, ComparatorResult, ProcessingContext


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
    @lru_cache(maxsize=512)
    def detect(cls, value: Any, type_hint: str = "string") -> Optional[str]:
        patterns = cls._registry.get(type_hint, {})
        for pattern, name in patterns.items():
            if pattern.fullmatch(str(value)):
                return name
        return None


class FormatComparator(Comparator):
    name = "format"

    def can_process(self, ctx: ProcessingContext, env: str, prev_result: dict) -> bool:
        # Обрабатываем только если на текущем уровне уже есть type: "string"
        return prev_result.get("type") == "string"

    def process(self, ctx: ProcessingContext, env: str, prev_result: dict) -> ComparatorResult:

        # Базовые триггеры из предыдущих компараторов (обычно из TypeComparator)
        base_triggers = set(prev_result.get("j2sElementTrigger", []))

        # Собираем все возможные форматы и их источники
        format_to_ids: dict[str, set[str]] = defaultdict(set)
        format_to_ids[None].update(base_triggers)

        # 1. Форматы, явно указанные в схемах
        for s in ctx.schemas:
            if isinstance(s.content, dict) and s.content.get("type") == "string":
                fmt = s.content.get("format")
                format_to_ids[fmt].add(s.id)
                if fmt is not None:
                    format_to_ids[None].discard(s.id)

        # 2. Форматы, выведенные из значений JSON
        for j in ctx.jsons:
            if isinstance(j.content, str):
                fmt = FormatDetector.detect(j.content)
                format_to_ids[fmt].add(j.id)
                if fmt is not None:
                    format_to_ids[None].discard(j.id)

        # Формируем варианты
        variants: list[dict] = []
        for fmt, ids in format_to_ids.items():
            if not ids:
                continue
            variant = {"type": "string", "j2sElementTrigger": sorted(ids)}
            if fmt is not None:
                variant["format"] = fmt
            variants.append(variant)

        # Результат
        if len(variants) == 1:
            return variants[0], None
        if len(variants) > 1:
            return None, variants

        # Если ничего нового не нашли — оставляем как есть
        return None, None
