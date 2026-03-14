import unittest

from genschema import Converter, PseudoArrayHandler
from genschema.comparators import (
    DeleteElement,
    FormatComparator,
    RequiredComparator,
    SchemaVersionComparator,
)
from genschema.comparators.template import ProcessingContext, Resource


def _old_pattern_schema(pattern: str = "^[0-9]+$") -> dict:
    return {
        "type": "object",
        "patternProperties": {
            pattern: {
                "type": "object",
                "properties": {
                    "catalogImage": {
                        "anyOf": [{"type": "string", "format": "uri"}, {"type": "null"}]
                    },
                    "hover": {
                        "anyOf": [
                            {
                                "anyOf": [
                                    {"type": "string"},
                                    {"type": "string", "format": "uri"},
                                ]
                            },
                            {"type": "null"},
                        ]
                    },
                    "icon": {"anyOf": [{"type": "string"}, {"type": "string", "format": "uri"}]},
                },
            }
        },
    }


def _new_pseudo_array_json() -> dict:
    return {
        "0": {
            "catalogImage": "https://example.com/a",
            "hover": "https://example.com/h",
            "icon": "https://example.com/i",
        },
        "1": {
            "catalogImage": "https://example.com/a2",
            "hover": "https://example.com/h2",
            "icon": "https://example.com/i2",
        },
    }


def _mixed_pseudo_and_non_pattern_json() -> dict:
    return {
        "0": {
            "catalogImage": "https://example.com/a",
            "hover": "https://example.com/h",
            "icon": "https://example.com/i",
        },
        "meta": {
            "catalogImage": "https://example.com/a2",
            "hover": "https://example.com/h2",
            "icon": "https://example.com/i2",
        },
    }


def _multiple_matching_patterns_schema() -> dict:
    return {
        "type": "object",
        "patternProperties": {
            "^\\d+$": {"type": "object", "properties": {"a": {"type": "string"}}},
            "^[0-9]+$": {"type": "object", "properties": {"b": {"type": "integer"}}},
        },
    }


def _multiple_matching_patterns_json() -> dict:
    return {
        "0": {"a": "x", "b": 1},
        "1": {"a": "y", "b": 2},
    }


def _schema_with_invalid_pattern() -> dict:
    return {
        "type": "object",
        "patternProperties": {
            "[0-9": {"type": "object", "properties": {"broken": {"type": "string"}}},
            "^\\d+$": {"type": "object", "properties": {"ok": {"type": "string"}}},
        },
    }


def _json_for_invalid_pattern_schema() -> dict:
    return {"0": {"ok": "v"}}


def _make_converter() -> Converter:
    conv = Converter(pseudo_handler=PseudoArrayHandler(), base_of="anyOf")
    conv.register(FormatComparator())
    conv.register(RequiredComparator())
    conv.register(SchemaVersionComparator())
    conv.register(DeleteElement())
    conv.register(DeleteElement("isPseudoArray"))
    return conv


class TestPatternPropertiesPseudoArrayMerge(unittest.TestCase):
    def test_split_array_ctx_uses_item_schema_from_pattern_properties(self) -> None:
        conv = Converter(pseudo_handler=PseudoArrayHandler(), base_of="anyOf")
        ctx = ProcessingContext(
            schemas=[Resource("s0", "schema", _old_pattern_schema())],
            jsons=[Resource("j0", "json", _new_pseudo_array_json())],
            sealed=False,
        )

        obj_ctx, items_ctx = conv._split_array_ctx(ctx)

        self.assertEqual(obj_ctx.schemas, [])
        self.assertEqual(len(items_ctx.schemas), 1)
        self.assertTrue(items_ctx.schemas[0].id.startswith("s0/patternProperties/"))
        self.assertIn("catalogImage", items_ctx.schemas[0].content.get("properties", {}))

    def test_merge_preserves_nullable_branch_in_pattern_properties(self) -> None:
        conv = _make_converter()
        conv.add_schema(_old_pattern_schema())
        conv.add_json(_new_pseudo_array_json())
        merged = conv.run()

        item_schema = merged["patternProperties"]["^[0-9]+$"]["properties"]
        catalog_variants = item_schema["catalogImage"].get("anyOf", [])
        hover_variants = item_schema["hover"].get("anyOf", [])

        self.assertTrue(
            any(v.get("type") == "null" for v in catalog_variants if isinstance(v, dict))
        )
        self.assertTrue(any(v.get("type") == "null" for v in hover_variants if isinstance(v, dict)))

    def test_split_array_ctx_drops_pattern_properties_for_mixed_keys(self) -> None:
        conv = Converter(pseudo_handler=PseudoArrayHandler(), base_of="anyOf")
        ctx = ProcessingContext(
            schemas=[Resource("s0", "schema", _old_pattern_schema())],
            jsons=[Resource("j0", "json", _mixed_pseudo_and_non_pattern_json())],
            sealed=False,
        )

        obj_ctx, items_ctx = conv._split_array_ctx(ctx)

        self.assertEqual([s.id for s in obj_ctx.schemas], ["s0"])
        self.assertEqual(items_ctx.schemas, [])
        self.assertEqual([j.id for j in obj_ctx.jsons], ["j0"])
        self.assertEqual(items_ctx.jsons, [])

    def test_merge_drops_pattern_properties_for_non_pattern_data(self) -> None:
        conv = Converter(pseudo_handler=PseudoArrayHandler(), base_of="anyOf")
        conv.add_schema(_old_pattern_schema())
        conv.add_json(_mixed_pseudo_and_non_pattern_json())

        merged = conv.run()

        self.assertNotIn("patternProperties", merged)
        self.assertIn("properties", merged)
        self.assertIn("0", merged["properties"])
        self.assertIn("meta", merged["properties"])

    def test_merge_handles_equivalent_regex_pattern(self) -> None:
        conv = _make_converter()
        conv.add_schema(_old_pattern_schema("^\\d+$"))
        conv.add_json(_new_pseudo_array_json())

        merged = conv.run()

        item_schema = merged["patternProperties"]["^[0-9]+$"]["properties"]
        catalog_variants = item_schema["catalogImage"].get("anyOf", [])
        self.assertTrue(
            any(v.get("type") == "null" for v in catalog_variants if isinstance(v, dict))
        )

    def test_merge_uses_all_matching_patterns_when_no_non_pattern_keys(self) -> None:
        conv = Converter(pseudo_handler=PseudoArrayHandler(), base_of="anyOf")
        conv.add_schema(_multiple_matching_patterns_schema())
        conv.add_json(_multiple_matching_patterns_json())

        merged = conv.run()

        item_props = merged["patternProperties"]["^[0-9]+$"]["properties"]
        self.assertIn("a", item_props)
        self.assertIn("b", item_props)

    def test_invalid_pattern_does_not_crash_and_is_not_selected(self) -> None:
        conv = Converter(pseudo_handler=PseudoArrayHandler(), base_of="anyOf")
        conv.add_schema(_schema_with_invalid_pattern())
        conv.add_json(_json_for_invalid_pattern_schema())

        merged = conv.run()

        item_props = merged["patternProperties"]["^[0-9]+$"]["properties"]
        self.assertIn("ok", item_props)
        self.assertNotIn("broken", item_props)
