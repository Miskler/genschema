from .template import ProcessingContext, Comparator
import logging

logger = logging.getLogger(__name__)

class RequiredComparator(Comparator):
    """
    Компаратор для определения обязательных полей.
    Устанавливает "required" на основе наличия ключей в JSON на текущем уровне.
    """

    def can_process(self, ctx: ProcessingContext, env: str, node: dict) -> bool:
        # обрабатываем только объекты
        return node.get("type") == "object" or node.get("type") is None or not ctx.jsons

    def process(self, ctx: ProcessingContext, env: str, node: dict):
        # собираем все ключи в JSON на этом уровне
        keys = set()
        for j in ctx.jsons:
            if isinstance(j.content, dict):
                keys.update(j.content.keys())

        # определяем обязательные: ключи, которые есть во всех JSON
        required = [k for k in keys if all(isinstance(j.content, dict) and k in j.content for j in ctx.jsons)]

        if required:
            return {"required": required}, None
        return None, None
