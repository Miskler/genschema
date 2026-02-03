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
        required_sets: list[set[str]] = []

        # Если есть хотя бы один JSON, который не является объектом,
        # мы не можем корректно определить обязательные ключи.
        if ctx.jsons and any(not isinstance(j.content, dict) for j in ctx.jsons):
            return None, None

        # ---------- из json ----------
        objects = [j.content for j in ctx.jsons if isinstance(j.content, dict)]
        if objects:
            keys: set[str] = set()
            for obj in objects:
                keys.update(obj.keys())

            required_from_json = {k for k in keys if all(k in obj for obj in objects)}
            required_sets.append(required_from_json)

        # ---------- из схем ----------
        for schema in ctx.schemas:
            content = schema.content
            if not isinstance(content, dict):
                continue
            req = content.get("required")
            if isinstance(req, list):
                required_sets.append(set(req))

        if not required_sets:
            return None, None

        # ---------- минимальное пересечение ----------
        required = sorted(set.intersection(*required_sets))

        if required:
            return {"required": required}, None
        return None, None
