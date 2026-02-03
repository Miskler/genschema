from typing import Any

from .template import Comparator, ComparatorResult, ProcessingContext, ToDelete


class NoAdditionalProperties(Comparator):
    """
    Компаратор, который всегда добавляет additionalProperties: false
    ко всем объектам (type: "object"), если это поле ещё не задано.

    Работает только на уровне объектов.
    Не перезаписывает уже существующие значения additionalProperties.
    """

    name = "no_additional_properties"

    def can_process(self, ctx: ProcessingContext, env: str, node: dict) -> bool:
        # Обрабатываем только те узлы, где уже определён тип object
        # и additionalProperties ещё не задан
        return node.get("type") == "object" and "additionalProperties" not in node

    def process(self, ctx: ProcessingContext, env: str, node: dict) -> ComparatorResult:
        """
        Добавляет additionalProperties: false, если его ещё нет.
        Возвращает обновление только для текущего узла.
        """
        updated: dict[str, ToDelete | Any | bool] = {"additionalProperties": False}
        return updated, None
