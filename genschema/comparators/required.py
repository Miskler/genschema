import logging

from .template import Comparator, ComparatorResult, ProcessingContext

logger = logging.getLogger(__name__)


class RequiredComparator(Comparator):
    """
    Компаратор для определения обязательных полей.
    Устанавливает "required" на основе наличия ключей в JSON на текущем уровне.
    """

    def can_process(self, ctx: ProcessingContext, env: str, node: dict) -> bool:
        # обрабатываем только объекты
        return (
            (node.get("type") == "object" and not node.get("isPseudoArray", False))
            or node.get("type") is None
            or not ctx.jsons
        )

    def process(self, ctx: ProcessingContext, env: str, node: dict) -> ComparatorResult:
        # собираем все ключи в JSON на этом уровне
        keys: set[str] = set()
        for j in ctx.jsons:
            if isinstance(j.content, dict):
                keys.update(j.content.keys())

        # определяем обязательные: ключи, которые есть во всех JSON
        required = [
            k
            for k in sorted(keys)
            if all(isinstance(j.content, dict) and k in j.content for j in ctx.jsons)
        ]

        if required:
            return {"required": required}, None
        return None, None
