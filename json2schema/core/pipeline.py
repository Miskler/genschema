from typing import Any, Dict, List
from .comparators.template import Resource, Comparator, ProcessingContext
import logging

logging.basicConfig(level=logging.ERROR)
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

    # ---------------- utils ----------------

    def _collect_prop_names(self, schemas, jsons):
        names = set()
        for s in schemas:
            c = s.content
            if isinstance(c, dict) and isinstance(c.get("properties"), dict):
                names.update(c["properties"].keys())
        for j in jsons:
            if isinstance(j.content, dict):
                names.update(j.content.keys())
        return sorted(names)

    def _gather_property_candidates(self, schemas, jsons, prop):
        s_out, j_out = [], []

        for s in schemas:
            c = s.content
            if isinstance(c, dict) and prop in c.get("properties", {}):
                s_out.append(Resource(s.id, "schema", c["properties"][prop]))

        for j in jsons:
            if isinstance(j.content, dict) and prop in j.content:
                j_out.append(Resource(j.id, "json", j.content[prop]))

        return s_out, j_out

    def _split_array_ctx(self, ctx: ProcessingContext):
        obj_jsons = []
        item_jsons = []

        for j in ctx.jsons:
            if isinstance(j.content, list):
                for el in j.content:
                    item_jsons.append(Resource(j.id, "json", el))
            else:
                obj_jsons.append(j)

        obj_schemas = []
        item_schemas = []

        for s in ctx.schemas:
            c = s.content
            if isinstance(c, dict) and c.get("type") == "array":
                # schema массива → идёт в items
                if "items" in c:
                    item_schemas.append(Resource(s.id, "schema", c["items"]))
            else:
                # object / scalar schema → ТОЛЬКО в object
                obj_schemas.append(s)

        return (
            ProcessingContext(obj_schemas, obj_jsons, ctx.sealed),
            ProcessingContext(item_schemas, item_jsons, ctx.sealed),
        )

    def _filter_ctx_by_ids(self, ctx: ProcessingContext, ids: set) -> ProcessingContext:
        if not ids:
            return ctx
        schemas = [s for s in ctx.schemas if s.id in ids]
        jsons = [j for j in ctx.jsons if j.id in ids]
        return ProcessingContext(schemas, jsons, ctx.sealed)

    # ---------------- core ----------------

    def _run_level(self, ctx: ProcessingContext, env: str, prev: Dict) -> Dict:
        logger.debug("Entering _run_level: env=%s, prev_result=%s", env, prev)
        node = dict(prev)

        # вызываем компараторы на текущем узле
        for comp in self._comparators:
            if not comp.can_process(ctx, env, node):
                continue

            g, alts = comp.process(ctx, env, node)
            if g:
                node.update(g)
            if alts:
                node.setdefault("anyOf", []).extend(alts)

        # если есть anyOf — обработаем каждую альтернативу через _run_level
        if "anyOf" in node:
            new_anyof = []
            for idx, alt in enumerate(node["anyOf"]):
                # фильтровать контекст по j2sElementTrigger если он указан в альтернативе
                alt_ids = set(alt.get("j2sElementTrigger", []))
                alt_ctx = self._filter_ctx_by_ids(ctx, alt_ids) if alt_ids else ctx

                # запустить альтернативу через тот же pipeline (вызов компараторов и рекурсия)
                processed_alt = self._run_level(alt_ctx, env + f"/anyOf/{idx}", alt)
                new_anyof.append(processed_alt)
            node["anyOf"] = new_anyof
            logger.debug("Exiting _run_level (anyOf handled): env=%s, node=%s", env, node)
            return node

        # объект → рекурсивно по свойствам (каждое свойство как отдельный уровень)
        if node.get("type") == "object":
            node = self._run_object(ctx, env, node)

        # массив → рекурсивно по items (items как отдельный уровень)
        if node.get("type") == "array":
            node = self._run_array(ctx, env, node)

        logger.debug("Exiting _run_level: env=%s, node=%s", env, node)
        return node

    # ---------------- object ----------------

    def _run_object(self, ctx: ProcessingContext, env: str, node: Dict) -> Dict:
        node = dict(node)  # копия
        node.setdefault("properties", {})

        props = self._collect_prop_names(ctx.schemas, ctx.jsons)
        for name in props:
            s, j = self._gather_property_candidates(ctx.schemas, ctx.jsons, name)
            sub_ctx = ProcessingContext(s, j, ctx.sealed)
            # запускаем full pipeline для свойства — компараторы + рекурсия
            node["properties"][name] = self._run_level(
                sub_ctx, f"{env}/properties/{name}", node["properties"].get(name, {})
            )

        if len(node["properties"]) <= 0:
            del node["properties"]

        return node

    # ---------------- array ----------------

    def _run_array(self, ctx: ProcessingContext, env: str, node: Dict) -> Dict:
        node = dict(node)
        node.setdefault("items", {})

        # используем split для формирования контекста элементов массива
        _, items_ctx = self._split_array_ctx(ctx)
        # запускаем full pipeline для items
        node["items"] = self._run_level(items_ctx, f"{env}/items", node.get("items", {}))

        return node

    # ---------------- entry ----------------

    def run(self):
        ctx = ProcessingContext(self._schemas, self._jsons, sealed=False)
        return self._run_level(ctx, "/", {})
