from typing import Any, Dict, List
from .comparators.template import Resource, Comparator, ProcessingContext
import logging

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


    # ---------------- core ----------------

    def _run_level(self, ctx: ProcessingContext, env: str, prev: Dict) -> Dict:
        logger.debug("Entering _run_level: env=%s, prev_result=%s", env, prev)
        node = dict(prev)

        for comp in self._comparators:
            if not comp.can_process(ctx, env, node):
                continue

            g, alts = comp.process(ctx, env, node)
            if g:
                node.update(g)
            if alts:
                node.setdefault("anyOf", []).extend(alts)

        if "anyOf" in node:
            out = []
            for alt in node["anyOf"]:
                t = alt.get("type")

                if t == "object":
                    obj_ctx, _ = self._split_array_ctx(ctx)
                    out.append(self._run_object(obj_ctx, env, alt))

                elif t == "array":
                    _, items_ctx = self._split_array_ctx(ctx)
                    out.append(self._run_array(items_ctx, env, alt))

                else:
                    out.append(alt)

            node["anyOf"] = out
            return node

        if node.get("type") == "object":
            return self._run_object(ctx, env, node)

        if node.get("type") == "array":
            return self._run_array(ctx, env, node)

        logger.debug("Exiting _run_level: env=%s, node=%s", env, node)
        return node

    # ---------------- object ----------------

    def _run_object(self, ctx, env, node):
        props = self._collect_prop_names(ctx.schemas, ctx.jsons)
        if not props:
            return node

        node.setdefault("properties", {})

        for name in props:
            s, j = self._gather_property_candidates(ctx.schemas, ctx.jsons, name)
            if not s and not j:
                continue
            sub = ProcessingContext(s, j, ctx.sealed)
            node["properties"][name] = self._run_level(
                sub, f"{env}/properties/{name}", {}
            )

        return node

    # ---------------- array ----------------

    def _run_array(self, items_ctx, env, node):
        if not items_ctx.jsons:
            return node

        node["items"] = self._run_level(items_ctx, f"{env}/items", {})
        return node

    # ---------------- entry ----------------

    def run(self):
        ctx = ProcessingContext(self._schemas, self._jsons, sealed=False)
        return self._run_level(ctx, "/", {})
