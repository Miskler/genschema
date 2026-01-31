from typing import Any, Dict, List
from .comparators.template import Resource, Comparator, ProcessingContext
import logging

def merge(a: Dict, b: Dict) -> Dict:
    r = dict(a)
    r.update(b)
    return r


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Converter:
    def __init__(self):
        self._schemas: List[Resource] = []
        self._jsons: List[Resource] = []
        self._comparators: List[Comparator] = []
        self._id = 0

    def add_schema(self, s: dict):
        self._schemas.append(Resource(self._id, "schema", s))
        self._id += 1

    def add_json(self, j: Any):
        self._jsons.append(Resource(self._id, "json", j))
        self._id += 1

    def register(self, c: Comparator):
        self._comparators.append(c)

    def _collect_prop_names(self, schemas: List[Resource], jsons: List[Resource]) -> List[str]:
        """
        Собираем имена свойств из схем (properties) и из json-объектов (ключи словарей).
        Возвращаем отсортированный детерминированный список.
        """
        names = set()
        # from schemas
        for s in schemas:
            if isinstance(s.content, dict) and "properties" in s.content and isinstance(s.content["properties"], dict):
                names.update(s.content["properties"].keys())
        # from jsons
        for j in jsons:
            if isinstance(j.content, dict):
                names.update(j.content.keys())
        return sorted(names)

    def _gather_property_candidates(self, schemas: List[Resource], jsons: List[Resource], prop: str):
        """
        Возвращаем два списка Resource:
        - s_out: для каждой схемы, которая содержит property -> вложенный schema с тем же id
        - j_out: для каждого json, где есть ключ prop -> значение с тем же id
        """
        s_out = []
        j_out = []
        for s in schemas:
            c = s.content
            if isinstance(c, dict) and "properties" in c and isinstance(c["properties"], dict) and prop in c["properties"]:
                s_out.append(Resource(s.id, "schema", c["properties"][prop]))
        for j in jsons:
            if isinstance(j.content, dict) and prop in j.content:
                j_out.append(Resource(j.id, "json", j.content[prop]))
        return s_out, j_out

    
    def _run_level(self, ctx: ProcessingContext, env: str, prev_result: Dict) -> Dict:
        """
        Рекурсивная генерация схемы на уровне `env` с логированием.
        """
        node = dict(prev_result)
        logger.debug("Entering _run_level: env=%s, prev_result=%s", env, prev_result)

        # --- Применяем компараторы ---
        for comp in self._comparators:
            if not comp.can_process(ctx, env, node):
                logger.debug("Comparator %s cannot process env=%s", comp.__class__.__name__, env)
                continue

            logger.debug("Running comparator %s at env=%s", comp.__class__.__name__, env)
            g, alts = comp.process(ctx, env, node)
            if g:
                logger.debug("Comparator %s returned global update: %s", comp.__class__.__name__, g)
                node.update(g)

            if alts:
                logger.debug("Comparator %s returned alternatives: %s", comp.__class__.__name__, alts)
                if "anyOf" in node:
                    logger.debug("Merging alternatives into existing anyOf")
                    node["anyOf"].extend(alts)
                else:
                    logger.debug("Creating new anyOf with alternatives")
                    node["anyOf"] = alts

        # --- Рекурсивно обходим properties ---
        prop_names = self._collect_prop_names(ctx.schemas, ctx.jsons)
        if prop_names:
            node.setdefault("properties", {})
            for name in prop_names:
                s_cands, j_cands = self._gather_property_candidates(ctx.schemas, ctx.jsons, name)
                sub_ctx = ProcessingContext(s_cands, j_cands, sealed=ctx.sealed)

                logger.debug("Recursing into property '%s', schemas=%s, jsons=%s", 
                            name, [s.id for s in s_cands], [j.id for j in j_cands])
                child_node = self._run_level(sub_ctx, env + f"/properties/{name}", {})

                # Определяем массив
                is_array = any(isinstance(j.content.get(name) if isinstance(j.content, dict) else None, list)
                            for j in ctx.jsons)
                array_triggers = [j.id for j in ctx.jsons if isinstance(j.content, dict) and name in j.content]

                if is_array:
                    arr_node: Dict[str, Any] = {
                        "type": "array",
                        "j2sElementTrigger": array_triggers,
                        "items": child_node
                    }
                    logger.debug("Property '%s' is array, node=%s", name, arr_node)
                    node["properties"][name] = arr_node
                else:
                    node["properties"][name] = child_node
                    logger.debug("Property '%s' node=%s", name, child_node)

        logger.debug("Exiting _run_level: env=%s, node=%s", env, node)
        return node



    def run(self):
        root_ctx = ProcessingContext(self._schemas, self._jsons, sealed=False)
        return self._run_level(root_ctx, "/", {})
