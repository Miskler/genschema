from __future__ import annotations

import copy
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Iterable, Literal, TypeAlias

from ..comparators import (
    DeleteElement,
    EmptyComparator,
    EnumComparator,
    FormatComparator,
    PreserveCommonKeywordsComparator,
    RequiredComparator,
)
from ..comparators.template import Comparator
from ..comparators.type import infer_schema_type, infer_schema_types
from ..pipeline import Converter
from ..pseudo_arrays import PseudoArrayHandlerBase

PathSegment: TypeAlias = str | int
SchemaPath: TypeAlias = tuple[PathSegment, ...]
ComparatorFactory: TypeAlias = Callable[[], Comparator]
SimilarityMetric: TypeAlias = Callable[[frozenset[str], frozenset[str]], float]
MergeStrategy: TypeAlias = Callable[[list[dict], "SchemaReferenceExtractionConfig"], dict]
NameFactory: TypeAlias = Callable[[int, "CandidateGroup", "SchemaReferenceExtractionConfig"], str]

DEFAULT_COMPARATOR_FACTORIES: tuple[ComparatorFactory, ...] = (
    FormatComparator,
    EnumComparator,
    RequiredComparator,
    EmptyComparator,
    DeleteElement,
    lambda: DeleteElement("isPseudoArray"),
)

DEFINITION_SECTION_KEYS = {"$defs", "definitions"}
STRUCTURAL_CONTAINER_KEYS = (
    "items",
    "additionalProperties",
    "contains",
    "if",
    "then",
    "else",
    "not",
    "propertyNames",
    "unevaluatedProperties",
    "unevaluatedItems",
)
STRUCTURAL_VARIANT_KEYS = ("anyOf", "oneOf", "allOf", "prefixItems")
MEANINGFUL_PATH_PARTS_BLACKLIST = {
    "properties",
    "patternProperties",
    "items",
    "anyOf",
    "oneOf",
    "allOf",
    "prefixItems",
    "additionalProperties",
    "contains",
    "if",
    "then",
    "else",
    "not",
    "propertyNames",
    "unevaluatedProperties",
    "unevaluatedItems",
    "$defs",
    "definitions",
}


def _default_similarity(left: frozenset[str], right: frozenset[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    intersection_size = len(left & right)
    return (2 * intersection_size) / (len(left) + len(right))


@dataclass(slots=True, frozen=True)
class SchemaReferenceExtractionConfig:
    similarity_threshold: float = 0.85
    min_total_keys: int = 3
    min_occurrences: int = 2
    defs_key: str = "$defs"
    ref_prefix: str | None = None
    merge_base_of: Literal["anyOf", "oneOf", "allOf"] = "anyOf"
    merge_pseudo_handler: PseudoArrayHandlerBase | None = None
    merge_comparator_factories: tuple[ComparatorFactory, ...] = field(
        default_factory=lambda: DEFAULT_COMPARATOR_FACTORIES
    )
    similarity_metric: SimilarityMetric = _default_similarity
    merge_strategy: MergeStrategy | None = None
    name_factory: NameFactory | None = None
    allowed_root_types: tuple[str, ...] = ("object", "array")
    preserve_common_keywords: bool = True
    include_root: bool = False
    skip_existing_definitions: bool = True

    def __post_init__(self) -> None:
        if not 0 < self.similarity_threshold <= 1:
            raise ValueError("similarity_threshold must be in the (0, 1] range")
        if self.min_total_keys < 0:
            raise ValueError("min_total_keys must be >= 0")
        if self.min_occurrences < 2:
            raise ValueError("min_occurrences must be >= 2")
        if not self.defs_key:
            raise ValueError("defs_key must not be empty")
        if not self.allowed_root_types:
            raise ValueError("allowed_root_types must not be empty")

    @property
    def normalized_ref_prefix(self) -> str:
        if self.ref_prefix is not None:
            return self.ref_prefix.rstrip("/")
        return f"#/{self.defs_key}"


@dataclass(slots=True)
class SchemaCandidate:
    path: SchemaPath
    schema: dict
    type_signature: tuple[str, ...]
    tokens: frozenset[str]
    total_keys: int


@dataclass(slots=True)
class CandidateGroup:
    members: list[SchemaCandidate]
    merged_schema: dict
    total_keys: int
    benefit: int
    definition_name: str = ""


class SchemaReferencePostprocessor:
    """
    Standalone JSON Schema postprocessor that extracts repeated or highly similar
    structures into shared definitions and replaces occurrences with ``$ref``.

    The postprocessor is intentionally independent from ``Converter`` itself:
    it can be run on any already-built schema. Candidate groups are merged
    through a fresh internal ``Converter`` run so the resulting definition stays
    aligned with the project's normal schema-combination pipeline.
    """

    @classmethod
    def process(cls, schema: dict, config: SchemaReferenceExtractionConfig | None = None) -> dict:
        if not isinstance(schema, dict):
            raise TypeError("schema must be a dict")

        config = config or SchemaReferenceExtractionConfig()
        prepared = copy.deepcopy(schema)

        candidates = cls._collect_candidates(prepared, config)
        if len(candidates) < config.min_occurrences:
            return prepared

        groups = cls._build_groups(candidates, config)
        if not groups:
            return prepared

        selected_groups = cls._select_groups(groups, config)
        if not selected_groups:
            return prepared

        defs = prepared.setdefault(config.defs_key, {})
        if not isinstance(defs, dict):
            raise TypeError(f"{config.defs_key} must be a dict when present")

        for index, group in enumerate(selected_groups, start=1):
            name_factory = config.name_factory or cls._default_name_factory
            definition_name = cls._ensure_unique_definition_name(
                defs, name_factory(index, group, config)
            )
            group.definition_name = definition_name
            defs[definition_name] = group.merged_schema

            ref_node = {"$ref": f"{config.normalized_ref_prefix}/{definition_name}"}
            for member in sorted(group.members, key=lambda item: len(item.path), reverse=True):
                cls._replace_at_path(prepared, member.path, copy.deepcopy(ref_node))

        return prepared

    @classmethod
    def extract(cls, schema: dict, config: SchemaReferenceExtractionConfig | None = None) -> dict:
        return cls.process(schema, config)

    @classmethod
    def _collect_candidates(
        cls, schema: dict, config: SchemaReferenceExtractionConfig
    ) -> list[SchemaCandidate]:
        candidates: list[SchemaCandidate] = []

        def walk(node: object, path: SchemaPath, inside_definition_section: bool) -> None:
            if not isinstance(node, dict):
                return

            local_inside_defs = inside_definition_section
            if path:
                parent_key = path[-1]
                if parent_key in DEFINITION_SECTION_KEYS:
                    local_inside_defs = True

            if (
                (config.include_root or path)
                and (not local_inside_defs or not config.skip_existing_definitions)
                and cls._is_schema_candidate(node, config)
            ):
                tokens = cls._collect_structural_tokens(node)
                total_keys = cls._count_total_keys(tokens)
                if total_keys >= config.min_total_keys:
                    type_signature = cls._type_signature(node)
                    candidates.append(
                        SchemaCandidate(
                            path=path,
                            schema=copy.deepcopy(node),
                            type_signature=type_signature,
                            tokens=frozenset(tokens),
                            total_keys=total_keys,
                        )
                    )

            for key, value in node.items():
                next_inside_defs = local_inside_defs or key in DEFINITION_SECTION_KEYS
                if key in {
                    "properties",
                    "patternProperties",
                    config.defs_key,
                    "$defs",
                    "definitions",
                }:
                    if isinstance(value, dict):
                        for child_key, child_value in value.items():
                            walk(child_value, path + (key, child_key), next_inside_defs)
                    continue

                if key in STRUCTURAL_CONTAINER_KEYS:
                    walk(value, path + (key,), next_inside_defs)
                    continue

                if key in STRUCTURAL_VARIANT_KEYS and isinstance(value, list):
                    for index, item in enumerate(value):
                        walk(item, path + (key, index), next_inside_defs)

        walk(schema, (), False)
        return candidates

    @classmethod
    def _is_schema_candidate(cls, schema: dict, config: SchemaReferenceExtractionConfig) -> bool:
        if "$ref" in schema:
            return False

        type_signature = cls._type_signature(schema)
        if not type_signature:
            return False

        return any(item in config.allowed_root_types for item in type_signature)

    @staticmethod
    def _type_signature(schema: dict) -> tuple[str, ...]:
        types = infer_schema_types(schema)
        if types:
            return tuple(sorted(types))

        inferred = infer_schema_type(schema)
        if inferred is not None:
            return (inferred,)

        if isinstance(schema.get("properties"), dict) or isinstance(
            schema.get("patternProperties"), dict
        ):
            return ("object",)
        if "items" in schema or "prefixItems" in schema:
            return ("array",)
        if any(key in schema for key in ("anyOf", "oneOf", "allOf")):
            return ("union",)
        return ()

    @classmethod
    def _collect_structural_tokens(cls, schema: dict) -> set[str]:
        tokens: set[str] = set()

        def walk(node: object, prefix: str) -> None:
            if not isinstance(node, dict):
                return

            type_signature = cls._type_signature(node)
            if type_signature:
                tokens.add(f"{prefix}|type:{','.join(type_signature)}")

            format_value = node.get("format")
            if isinstance(format_value, str):
                tokens.add(f"{prefix}|format:{format_value}")

            if isinstance(node.get("enum"), list):
                tokens.add(f"{prefix}|enum")

            properties = node.get("properties")
            if isinstance(properties, dict):
                for name, child in sorted(properties.items()):
                    child_prefix = f"{prefix}/properties/{name}"
                    tokens.add(f"{prefix}|prop:{name}")
                    walk(child, child_prefix)

            pattern_properties = node.get("patternProperties")
            if isinstance(pattern_properties, dict):
                for name, child in sorted(pattern_properties.items()):
                    child_prefix = f"{prefix}/patternProperties/{name}"
                    tokens.add(f"{prefix}|pattern:{name}")
                    walk(child, child_prefix)

            items = node.get("items")
            if isinstance(items, dict):
                tokens.add(f"{prefix}|items")
                walk(items, f"{prefix}/items")
            elif isinstance(items, list):
                for index, child in enumerate(items):
                    tokens.add(f"{prefix}|items:{index}")
                    walk(child, f"{prefix}/items/{index}")

            for key in ("anyOf", "oneOf", "allOf", "prefixItems"):
                variants = node.get(key)
                if not isinstance(variants, list):
                    continue
                tokens.add(f"{prefix}|{key}:{len(variants)}")
                for child in variants:
                    walk(child, f"{prefix}/{key}/*")

            for key in STRUCTURAL_CONTAINER_KEYS:
                child = node.get(key)
                if isinstance(child, dict):
                    tokens.add(f"{prefix}|{key}")
                    walk(child, f"{prefix}/{key}")

        walk(schema, "#")
        return tokens

    @staticmethod
    def _count_total_keys(tokens: Iterable[str]) -> int:
        return sum(1 for token in tokens if "|prop:" in token or "|pattern:" in token)

    @classmethod
    def _build_groups(
        cls, candidates: list[SchemaCandidate], config: SchemaReferenceExtractionConfig
    ) -> list[CandidateGroup]:
        by_type: dict[tuple[str, ...], list[SchemaCandidate]] = {}
        for candidate in candidates:
            by_type.setdefault(candidate.type_signature, []).append(candidate)

        groups: list[CandidateGroup] = []
        for type_signature_candidates in by_type.values():
            ordered = sorted(
                type_signature_candidates,
                key=lambda item: (-item.total_keys, len(item.path), item.path),
            )
            consumed: set[int] = set()

            for index, seed in enumerate(ordered):
                if index in consumed:
                    continue

                members = [seed]
                consumed.add(index)

                scored: list[tuple[float, int, SchemaCandidate]] = []
                for other_index, other in enumerate(ordered):
                    if other_index in consumed:
                        continue
                    score = config.similarity_metric(seed.tokens, other.tokens)
                    if score >= config.similarity_threshold:
                        scored.append((score, other_index, other))

                scored.sort(key=lambda item: (-item[0], -item[2].total_keys, item[2].path))

                for _, other_index, other in scored:
                    if all(
                        config.similarity_metric(existing.tokens, other.tokens)
                        >= config.similarity_threshold
                        for existing in members
                    ):
                        members.append(other)
                        consumed.add(other_index)

                if len(members) < config.min_occurrences:
                    continue

                merged_schema = cls._merge_group([member.schema for member in members], config)
                merged_tokens = cls._collect_structural_tokens(merged_schema)
                merged_total_keys = cls._count_total_keys(merged_tokens)
                benefit = sum(member.total_keys for member in members) - merged_total_keys
                if benefit <= 0:
                    continue

                groups.append(
                    CandidateGroup(
                        members=members,
                        merged_schema=merged_schema,
                        total_keys=merged_total_keys,
                        benefit=benefit,
                    )
                )

        groups.sort(
            key=lambda group: (
                -group.benefit,
                -len(group.members),
                -group.total_keys,
                group.members[0].path,
            )
        )
        return groups

    @classmethod
    def _merge_group(cls, schemas: list[dict], config: SchemaReferenceExtractionConfig) -> dict:
        merge_strategy = config.merge_strategy or cls._default_merge_strategy
        return merge_strategy(schemas, config)

    @staticmethod
    def _default_merge_strategy(
        schemas: list[dict], config: SchemaReferenceExtractionConfig
    ) -> dict:
        converter = Converter(
            pseudo_handler=config.merge_pseudo_handler,
            base_of=config.merge_base_of,
        )
        for schema in schemas:
            converter.add_schema(copy.deepcopy(schema))
        for factory in config.merge_comparator_factories:
            converter.register(factory())
        if config.preserve_common_keywords:
            converter.register(PreserveCommonKeywordsComparator())
        return converter.run()

    @classmethod
    def _select_groups(
        cls, groups: list[CandidateGroup], config: SchemaReferenceExtractionConfig
    ) -> list[CandidateGroup]:
        selected: list[CandidateGroup] = []
        occupied_paths: list[SchemaPath] = []

        for group in groups:
            available_members = [
                member
                for member in group.members
                if not any(cls._paths_overlap(member.path, occupied) for occupied in occupied_paths)
            ]
            if len(available_members) < config.min_occurrences:
                continue

            if len(available_members) != len(group.members):
                merged_schema = cls._merge_group(
                    [member.schema for member in available_members], config
                )
                merged_total_keys = cls._count_total_keys(
                    cls._collect_structural_tokens(merged_schema)
                )
                benefit = sum(member.total_keys for member in available_members) - merged_total_keys
                if benefit <= 0:
                    continue
                group = CandidateGroup(
                    members=available_members,
                    merged_schema=merged_schema,
                    total_keys=merged_total_keys,
                    benefit=benefit,
                )

            selected.append(group)
            occupied_paths.extend(member.path for member in group.members)

        return selected

    @staticmethod
    def _paths_overlap(left: SchemaPath, right: SchemaPath) -> bool:
        shortest = min(len(left), len(right))
        return left[:shortest] == right[:shortest]

    @classmethod
    def _replace_at_path(cls, document: dict, path: SchemaPath, new_value: dict) -> None:
        if not path:
            document.clear()
            document.update(new_value)
            return

        parent: object = document
        for segment in path[:-1]:
            if isinstance(segment, int):
                if not isinstance(parent, list):
                    raise TypeError("Path points to a list index inside a non-list container")
                parent = parent[segment]
            else:
                if not isinstance(parent, dict):
                    raise TypeError("Path points to a dict key inside a non-dict container")
                parent = parent[segment]

        last = path[-1]
        if isinstance(last, int):
            if not isinstance(parent, list):
                raise TypeError("Path points to a list index inside a non-list container")
            parent[last] = new_value
            return

        if not isinstance(parent, dict):
            raise TypeError("Path points to a dict key inside a non-dict container")
        parent[last] = new_value

    @classmethod
    def _default_name_factory(
        cls,
        index: int,
        group: CandidateGroup,
        config: SchemaReferenceExtractionConfig,
    ) -> str:
        meaningful_tail_parts: list[str] = []
        for member in group.members:
            meaningful = [
                str(part)
                for part in member.path
                if isinstance(part, str)
                and part not in MEANINGFUL_PATH_PARTS_BLACKLIST
                and not part.startswith("$")
            ]
            if meaningful:
                meaningful_tail_parts.append(meaningful[-1])

        if meaningful_tail_parts:
            name, count = Counter(meaningful_tail_parts).most_common(1)[0]
            if count == len(group.members) or count >= 2:
                normalized = cls._normalize_definition_name(name)
                if normalized:
                    return normalized

        root_type = (
            group.members[0].type_signature[0] if group.members[0].type_signature else "schema"
        )
        return f"{cls._normalize_definition_name(root_type)}{index}"

    @staticmethod
    def _normalize_definition_name(value: str) -> str:
        parts = [part for part in re.split(r"[^0-9A-Za-z]+", value) if part]
        if not parts:
            return "SharedSchema"
        normalized = "".join(part[:1].upper() + part[1:] for part in parts)
        if normalized[0].isdigit():
            return f"Shared{normalized}"
        return normalized

    @staticmethod
    def _ensure_unique_definition_name(defs: dict, base_name: str) -> str:
        candidate = base_name
        index = 2
        while candidate in defs:
            candidate = f"{base_name}{index}"
            index += 1
        return candidate
