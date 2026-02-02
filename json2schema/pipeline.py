import json
import logging
from typing import Literal, Optional

from .comparators import TypeComparator
from .comparators.template import Comparator, ProcessingContext, Resource, ToDelete
from .pseudo_arrays import PseudoArrayHandlerBase

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


class Converter:
    def __init__(
        self,
        pseudo_handler: Optional[PseudoArrayHandlerBase] = None,
        base_of: Literal["anyOf", "oneOf", "allOf"] = "anyOf",
        core_comparator: Optional[TypeComparator] = None,
    ):
        """
        Конвертер JSON + JSON Schema структур в JSON Schema.

        :param pseudo_handler: Обработчик псевдомассивов
        (большие словари с одинаковым паттерном значений, а ключами являются индефикаторы).
        :type pseudo_handler: Optional[PseudoArrayHandlerBase]

        :param base_of: Базовый оператор объединения схем.
        Логики определения конкретного типа Of индивидуально не предусмотрено.
        :type base_of: Literal["anyOf", "oneOf", "allOf"]

        :param core_comparator: Базовый компаратор типов.
        Он вынесен отдельно,
        так как type - единственное поле без которого Converter не может построить структуру.
        :type core_comparator: TypeComparator
        """
        self._schemas: list[Resource] = []
        self._jsons: list[Resource] = []
        self._comparators: list[Comparator] = []
        self._core_comparator = core_comparator or TypeComparator()
        self._id = 0
        self._pseudo_handler = pseudo_handler
        self._base_of = base_of

    def add_schema(self, s: dict | str) -> None:
        if isinstance(s, str):
            with open(s, "r") as f:
                s = json.loads(f.read())

        self._schemas.append(Resource(str(self._id), "schema", s))
        self._id += 1

    def add_json(self, j: dict | list | str) -> None:
        if isinstance(j, str):
            with open(j, "r") as f:
                j = json.loads(f.read())

        self._jsons.append(Resource(str(self._id), "json", j))
        self._id += 1

    def register(self, c: Comparator) -> None:
        if isinstance(c, TypeComparator):
            raise UserWarning(
                "A TypeComparator-like comparator must be provided during initialization "
                "using the core_comparator attribute."
            )
        self._comparators.append(c)

    # ---------------- utils ----------------

    def _collect_prop_names(self, schemas: list[Resource], jsons: list[Resource]) -> list[str]:
        names = set()
        for s in schemas:
            c = s.content
            if isinstance(c, dict) and isinstance(c.get("properties"), dict):
                names.update(c["properties"].keys())
        for j in jsons:
            if isinstance(j.content, dict):
                names.update(j.content.keys())
        return sorted(names)

    def _gather_property_candidates(
        self, schemas: list[Resource], jsons: list[Resource], prop: str
    ) -> tuple[list[Resource], list[Resource]]:
        s_out, j_out = [], []

        for s in schemas:
            c = s.content
            if isinstance(c, dict) and prop in c.get("properties", {}):
                s_out.append(Resource(f"{s.id}/{prop}", "schema", c["properties"][prop]))

        for j in jsons:
            if isinstance(j.content, dict) and prop in j.content:
                j_out.append(Resource(f"{j.id}/{prop}", "json", j.content[prop]))

        return s_out, j_out

    def _split_array_ctx(
        self, ctx: ProcessingContext
    ) -> tuple[ProcessingContext, ProcessingContext]:
        obj_jsons = []
        item_jsons = []

        for j in ctx.jsons:
            c = j.content
            if isinstance(c, list):
                for i, el in enumerate(c):
                    item_jsons.append(Resource(f"{j.id}/{i}", "json", el))
            elif isinstance(c, dict):
                keys = self._collect_prop_names([], [j])
                if self._pseudo_handler and self._pseudo_handler.is_pseudo_array(keys, ctx):
                    sorted_keys = sorted(keys, key=lambda k: int(k) if k.isdigit() else -1)
                    for i, k in enumerate(sorted_keys):
                        item_jsons.append(Resource(f"{j.id}/{i}", "json", c[k]))
                else:
                    obj_jsons.append(j)
            else:
                obj_jsons.append(j)

        obj_schemas = []
        item_schemas = []

        for s in ctx.schemas:
            c = s.content
            if isinstance(c, dict):
                t = c.get("type")
                if t == "array" and "items" in c:
                    item_schemas.append(Resource(f"{s.id}/items", "schema", c["items"]))
                elif t == "object" and "properties" in c:
                    keys = sorted(c["properties"].keys())
                    if self._pseudo_handler and self._pseudo_handler.is_pseudo_array(keys, ctx):
                        sorted_keys = sorted(keys, key=lambda k: int(k) if k.isdigit() else -1)
                        for i, k in enumerate(sorted_keys):
                            item_schemas.append(
                                Resource(f"{s.id}/{i}", "schema", c["properties"][k])
                            )
                    else:
                        obj_schemas.append(s)
                else:
                    obj_schemas.append(s)
            else:
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

    def _run_level(self, ctx: ProcessingContext, env: str, prev: dict) -> dict:
        logger.debug("Entering _run_level: env=%s, prev_result=%s", env, prev)
        node = dict(prev)

        def use_comp(comp: Comparator) -> bool:
            if not comp.can_process(ctx, env, node):
                return False

            g, alts = comp.process(ctx, env, node)
            if g:
                node.update(g)
            if alts:
                node.setdefault(self._base_of, []).extend(alts)
            return True

        # Вызов базового компаратора
        use_comp(self._core_comparator)

        # Определение является ли объект псевдомассивом
        if node.get("type") == "object":
            props = self._collect_prop_names(ctx.schemas, ctx.jsons)
            if self._pseudo_handler:
                is_pseudo_array, pattern = self._pseudo_handler.is_pseudo_array(props, ctx)
                node["isPseudoArray"] = is_pseudo_array
            else:
                node["isPseudoArray"] = False
                is_pseudo_array = False

        # Вызов остальных компараторов
        for comp in self._comparators:
            use_comp(comp)

        # Удаление атрибутов помеченных на удаление
        to_delete_keys = []
        for key, element in node.items():
            if isinstance(element, ToDelete):
                to_delete_keys.append(key)
        for key in to_delete_keys:
            del node[key]

        # если есть Of — обработаем каждую альтернативу через _run_level
        if self._base_of in node:
            new_of = []
            for idx, alt in enumerate(node[self._base_of]):
                alt_ids = set(alt.get("j2sElementTrigger", []))
                alt_ctx = self._filter_ctx_by_ids(ctx, alt_ids) if alt_ids else ctx
                processed_alt = self._run_level(alt_ctx, env + f"/{self._base_of}/{idx}", alt)
                new_of.append(processed_alt)
            node[self._base_of] = new_of
            logger.debug(
                "Exiting _run_level (%s handled): env=%s, node=%s", self._base_of, env, node
            )
            return node

        # recursion based on type
        if node.get("type") == "object":
            if is_pseudo_array:
                node = self._run_pseudo_array(ctx, env, node, str(pattern))
            else:
                node = self._run_object(ctx, env, node)
        elif node.get("type") == "array":
            node = self._run_array(ctx, env, node)

        logger.debug("Exiting _run_level: env=%s, node=%s", env, node)
        return node

    # ---------------- object ----------------

    def _run_object(self, ctx: ProcessingContext, env: str, node: dict) -> dict:
        node = dict(node)
        node.setdefault("properties", {})

        props = self._collect_prop_names(ctx.schemas, ctx.jsons)
        for name in props:
            s, j = self._gather_property_candidates(ctx.schemas, ctx.jsons, name)
            sub_ctx = ProcessingContext(s, j, ctx.sealed)
            node["properties"][name] = self._run_level(
                sub_ctx, f"{env}/properties/{name}", node["properties"].get(name, {})
            )

        if not node["properties"]:
            node.pop("properties", None)

        return node

    # ---------------- pseudo array ----------------

    def _run_pseudo_array(self, ctx: ProcessingContext, env: str, node: dict, pattern: str) -> dict:
        node = dict(node)
        node.setdefault("patternProperties", {})
        _, items_ctx = self._split_array_ctx(ctx)
        node["patternProperties"][pattern] = self._run_level(
            items_ctx, f"{env}/patternProperties/{pattern}", {}
        )
        if not node["patternProperties"]:
            node.pop("patternProperties", None)
        return node

    # ---------------- array ----------------

    def _run_array(self, ctx: ProcessingContext, env: str, node: dict) -> dict:
        node = dict(node)
        node.setdefault("items", {})

        _, items_ctx = self._split_array_ctx(ctx)
        node["items"] = self._run_level(items_ctx, f"{env}/items", node.get("items", {}))

        return node

    # ---------------- entry ----------------

    def run(self) -> dict:
        ctx = ProcessingContext(self._schemas, self._jsons, sealed=False)
        return self._run_level(ctx, "/", {})
