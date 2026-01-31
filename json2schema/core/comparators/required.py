from typing import List, Dict, Tuple, Optional
from .template import ProcessingContext, Comparator

class RequiredComparator(Comparator):
    """
    Компаратор для определения обязательных полей.
    Устанавливает "required" на основе присутствия ключей в JSON.
    """

    def can_process(self, ctx: ProcessingContext, env: str, node: Dict) -> bool:
        # Обрабатываем только объекты
        type_field = node.get("type")
        return type_field == "object" or type_field is None

    def process(
        self,
        ctx: ProcessingContext,
        env: str,
        node: Dict
    ) -> Tuple[Optional[Dict], Optional[List[Dict]]]:

        # собираем имена всех свойств из схем и JSON
        prop_names = set()

        for s in ctx.schemas:
            if s.content.get("type") == "object" and "properties" in s.content:
                prop_names.update(s.content["properties"].keys())

        for j in ctx.jsons:
            if j.type == "json" and isinstance(j.content, dict):
                prop_names.update(j.content.keys())

        required_fields = []
        for prop in prop_names:
            # проверяем: есть ли prop во всех JSON-объектах
            all_present = all(
                isinstance(j.content, dict) and prop in j.content for j in ctx.jsons if j.type == "json"
            )
            if all_present:
                required_fields.append(prop)

        if required_fields:
            return {"required": required_fields}, None
        return None, None
