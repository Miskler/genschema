from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ToDelete:
    content: int | float | str | list | dict = ""
    comparator_trigger: Optional["Comparator"] = None


@dataclass
class Resource:
    id: str
    type: str
    content: Any


@dataclass
class ProcessingContext:
    schemas: list[Resource]
    jsons: list[Resource]
    sealed: bool = False


ComparatorResult = tuple[Optional[dict[str, ToDelete | Any | bool]], Optional[list[dict]]]


class Comparator:
    name = "base"

    def can_process(self, ctx: ProcessingContext, env: str, prev_result: dict) -> bool:
        return False

    def process(self, ctx: ProcessingContext, env: str, prev_result: dict) -> ComparatorResult:
        return None, None
