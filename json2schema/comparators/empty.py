from .template import Comparator, ComparatorResult, ProcessingContext, Resource


class EmptyComparator(Comparator):
    """
    Добавляет maxItems=0 или maxProperties=0 для полностью пустых массивов/объектов,
    а так же minItems=0 или minProperties=0 для полностью НЕ пустых массивов/объектов,
    если на данном уровне нет кандидатов из непустых схем или JSON.
    """

    name = "empty"

    def __init__(self, flag_empty: bool = True, flag_non_empty: bool = True):
        self.flag_empty = flag_empty
        self.flag_non_empty = flag_non_empty

    def can_process(self, ctx: ProcessingContext, env: str, node: dict) -> bool:
        t = node.get("type")
        return t == "object" or t == "array"

    def process(self, ctx: ProcessingContext, env: str, node: dict) -> ComparatorResult:

        # Проверяем есть ли непустые кандидаты на этом уровне
        def is_nonempty(r: Resource) -> bool:
            c = r.content
            if isinstance(c, dict):
                return bool(c)  # не пустой словарь
            if isinstance(c, list):
                return bool(c)  # не пустой список
            return True  # скаляры считаем непустыми

        candidates = [is_nonempty(r) for r in ctx.schemas + ctx.jsons]

        if self.flag_empty and not any(candidates):
            t = node.get("type")
            if t == "object":
                return {"maxProperties": 0}, None
            elif t == "array":
                return {"maxItems": 0}, None
        elif self.flag_non_empty and all(candidates):
            t = node.get("type")
            if t == "object":
                return {"minProperties": 1}, None
            elif t == "array":
                return {"minItems": 1}, None

        return None, None
