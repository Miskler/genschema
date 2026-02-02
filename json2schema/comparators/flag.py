from .template import Comparator, ComparatorResult, ProcessingContext


class FlagMaker(Comparator):
    """Визуально показывает где именно могут сработать компораторы"""

    name = "flag"

    def can_process(self, ctx: ProcessingContext, env: str, node: dict) -> bool:
        # Обрабатываем объекты и массивы
        return True

    def process(self, ctx: ProcessingContext, env: str, node: dict) -> ComparatorResult:
        return {"Flag": True}, None
