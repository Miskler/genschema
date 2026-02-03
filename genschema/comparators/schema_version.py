from .template import Comparator, ComparatorResult, ProcessingContext


class SchemaVersionComparator(Comparator):
    """
    Компаратор для установки версии JSON Schema на верхнем уровне.
    """

    name = "schema_version"

    def __init__(self, version: str = "https://json-schema.org/draft/2020-12/schema"):
        self._version = version

    def can_process(self, ctx: ProcessingContext, env: str, prev_result: dict) -> bool:
        return env == "/" and "$schema" not in prev_result

    def process(self, ctx: ProcessingContext, env: str, prev_result: dict) -> ComparatorResult:
        return {"$schema": self._version}, None
