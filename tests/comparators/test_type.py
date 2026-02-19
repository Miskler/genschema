import unittest

from genschema.comparators.template import ProcessingContext, Resource
from genschema.comparators.type import (
    TypeComparator,
    infer_json_type,
    infer_schema_type,
    infer_schema_types,
)


class TestInferJsonType(unittest.TestCase):
    def test_null(self):
        self.assertEqual(infer_json_type(None), "null")

    def test_boolean_true(self):
        self.assertEqual(infer_json_type(True), "boolean")

    def test_boolean_false(self):
        self.assertEqual(infer_json_type(False), "boolean")

    def test_integer_positive(self):
        self.assertEqual(infer_json_type(42), "integer")

    def test_integer_negative(self):
        self.assertEqual(infer_json_type(-42), "integer")

    def test_integer_zero(self):
        self.assertEqual(infer_json_type(0), "integer")

    def test_number_float(self):
        self.assertEqual(infer_json_type(3.14), "number")

    def test_number_nan(self):
        # NaN is float
        import math

        self.assertEqual(infer_json_type(math.nan), "number")

    def test_number_inf(self):
        # Inf is float
        import math

        self.assertEqual(infer_json_type(math.inf), "number")

    def test_string(self):
        self.assertEqual(infer_json_type("hello"), "string")

    def test_empty_string(self):
        self.assertEqual(infer_json_type(""), "string")

    def test_array_empty(self):
        self.assertEqual(infer_json_type([]), "array")

    def test_array_non_empty(self):
        self.assertEqual(infer_json_type([1, 2]), "array")

    def test_object_empty(self):
        self.assertEqual(infer_json_type({}), "object")

    def test_object_non_empty(self):
        self.assertEqual(infer_json_type({"key": "value"}), "object")

    def test_other_types(self):
        self.assertEqual(infer_json_type((1, 2)), "any")  # tuple
        self.assertEqual(infer_json_type(set()), "any")  # set
        self.assertEqual(infer_json_type(frozenset()), "any")  # frozenset
        self.assertEqual(infer_json_type(bytes(b"")), "any")  # bytes
        self.assertEqual(infer_json_type(bytearray()), "any")  # bytearray
        self.assertEqual(infer_json_type(object()), "any")  # custom object


class TestInferSchemaType(unittest.TestCase):
    def test_non_dict_input(self):
        self.assertIsNone(infer_schema_type("not a dict"))
        self.assertIsNone(infer_schema_type(123))
        self.assertIsNone(infer_schema_type([]))
        self.assertIsNone(infer_schema_type(None))

    def test_empty_dict(self):
        self.assertIsNone(infer_schema_type({}))

    def test_type_as_string(self):
        self.assertEqual(infer_schema_type({"type": "string"}), "string")
        self.assertEqual(infer_schema_type({"type": "integer"}), "integer")

    def test_type_not_string(self):
        self.assertIsNone(infer_schema_type({"type": 123}))
        self.assertIsNone(infer_schema_type({"type": []}))
        self.assertIsNone(infer_schema_type({"type": {}}))
        self.assertIsNone(infer_schema_type({"type": None}))

    def test_properties_present(self):
        self.assertEqual(infer_schema_type({"properties": {}}), "object")
        self.assertEqual(infer_schema_type({"properties": {"key": {}}}), "object")

    def test_items_present(self):
        self.assertEqual(infer_schema_type({"items": {}}), "array")
        self.assertEqual(infer_schema_type({"items": {"type": "string"}}), "array")

    def test_type_and_properties(self):
        # Type takes precedence
        self.assertEqual(infer_schema_type({"type": "object", "properties": {}}), "object")
        self.assertEqual(infer_schema_type({"type": "string", "properties": {}}), "string")

    def test_type_and_items(self):
        # Type takes precedence
        self.assertEqual(infer_schema_type({"type": "array", "items": {}}), "array")
        self.assertEqual(infer_schema_type({"type": "string", "items": {}}), "string")

    def test_properties_and_items(self):
        # Properties checked before items
        self.assertEqual(infer_schema_type({"properties": {}, "items": {}}), "object")

    def test_type_not_string_with_properties(self):
        self.assertEqual(infer_schema_type({"type": 123, "properties": {}}), "object")

    def test_type_not_string_with_items(self):
        self.assertEqual(infer_schema_type({"type": 123, "items": {}}), "array")

    def test_no_type_with_other_keys(self):
        self.assertIsNone(infer_schema_type({"other": "key"}))


class TestInferSchemaTypes(unittest.TestCase):
    def test_non_dict_input(self):
        self.assertEqual(infer_schema_types("not a dict"), [])
        self.assertEqual(infer_schema_types(123), [])

    def test_single_type(self):
        self.assertEqual(infer_schema_types({"type": "string"}), ["string"])

    def test_type_list(self):
        self.assertEqual(infer_schema_types({"type": ["string", "null"]}), ["string", "null"])

    def test_anyof_union(self):
        schema = {"anyOf": [{"type": "string"}, {"type": "null"}]}
        self.assertEqual(infer_schema_types(schema), ["string", "null"])

    def test_oneof_union(self):
        schema = {"oneOf": [{"type": "integer"}, {"type": "null"}]}
        self.assertEqual(infer_schema_types(schema), ["integer", "null"])

    def test_allof_intersection(self):
        schema = {"allOf": [{"type": "string"}, {"type": "string", "format": "email"}]}
        self.assertEqual(infer_schema_types(schema), ["string"])

    def test_fallback_to_legacy_inference(self):
        self.assertEqual(infer_schema_types({"properties": {}}), ["object"])


class TestTypeComparator(unittest.TestCase):
    def setUp(self):
        self.comparator = TypeComparator()

    def test_name(self):
        self.assertEqual(self.comparator.name, "type")

    def test_can_process_no_type_in_prev_and_has_resources(self):
        ctx = ProcessingContext([Resource("s1", "schema", {})], [], False)
        self.assertTrue(self.comparator.can_process(ctx, "", {}))

        ctx = ProcessingContext([], [Resource("j1", "json", None)], False)
        self.assertTrue(self.comparator.can_process(ctx, "", {}))

        ctx = ProcessingContext(
            [Resource("s1", "schema", {})], [Resource("j1", "json", None)], False
        )
        self.assertTrue(self.comparator.can_process(ctx, "", {}))

    def test_can_process_type_in_prev(self):
        ctx = ProcessingContext([Resource("s1", "schema", {})], [], False)
        self.assertFalse(self.comparator.can_process(ctx, "", {"type": "string"}))

    def test_can_process_no_resources(self):
        ctx = ProcessingContext([], [], False)
        self.assertFalse(self.comparator.can_process(ctx, "", {}))

    def test_process_when_only_any_type_inferred_from_jsons(self):
        s1 = Resource("s1", "schema", "not dict")
        j1 = Resource("j1", "json", object())
        ctx = ProcessingContext([s1], [j1], False)

        general, alts = self.comparator.process(ctx, "", {})

        self.assertEqual(general, {"type": "any", "j2sElementTrigger": ["j1"]})
        self.assertIsNone(alts)

    def test_process_single_type_not_sealed(self):
        s1 = Resource("s1", "schema", {"type": "string"})
        ctx = ProcessingContext([s1], [], False)
        general, alts = self.comparator.process(ctx, "", {})
        self.assertEqual(general, {"type": "string", "j2sElementTrigger": ["s1"]})
        self.assertIsNone(alts)

    def test_process_single_type_sealed(self):
        s1 = Resource("s1", "schema", {"type": "string"})
        ctx = ProcessingContext([s1], [], True)
        general, alts = self.comparator.process(ctx, "", {})
        self.assertEqual(general, {"type": "string", "j2sElementTrigger": ["s1"]})
        self.assertIsNone(alts)

    def test_process_multiple_types_not_sealed(self):
        s1 = Resource("s1", "schema", {"type": "string"})
        s2 = Resource("s2", "schema", {"properties": {}})  # object
        j1 = Resource("j1", "json", [1, 2])  # array
        j2 = Resource("j2", "json", "text")  # string
        ctx = ProcessingContext([s1, s2], [j1, j2], False)
        general, alts = self.comparator.process(ctx, "", {})
        self.assertIsNone(general)
        # Order by first insertion:
        # string (s1), object (s2), array (j1), string again (j2 adds to existing)
        # So variants: string (s1,j2), object (s2), array (j1)
        expected_alts = [
            {"type": "string", "j2sElementTrigger": ["j2", "s1"]},  # sorted ids
            {"type": "object", "j2sElementTrigger": ["s2"]},
            {"type": "array", "j2sElementTrigger": ["j1"]},
        ]
        self.assertEqual(alts, expected_alts)

    def test_process_multiple_types_sealed(self):
        s1 = Resource("s1", "schema", {"type": "string"})
        s2 = Resource("s2", "schema", {"properties": {}})  # object
        ctx = ProcessingContext([s1, s2], [], True)
        general, alts = self.comparator.process(ctx, "", {})
        # First variant in insertion order: string first
        self.assertEqual(general, {"type": "string", "j2sElementTrigger": ["s1"]})
        self.assertIsNone(alts)

    def test_process_mixed_infer_from_schema_and_json(self):
        s1 = Resource("s1", "schema", {"items": {}})  # array
        j1 = Resource("j1", "json", {"key": "value"})  # object
        j2 = Resource("j2", "json", None)  # null
        ctx = ProcessingContext([s1], [j1, j2], False)
        general, alts = self.comparator.process(ctx, "", {})
        self.assertIsNone(general)
        expected_alts = [
            {"type": "array", "j2sElementTrigger": ["s1"]},
            {"type": "object", "j2sElementTrigger": ["j1"]},
            {"type": "null", "j2sElementTrigger": ["j2"]},
        ]
        self.assertEqual(alts, expected_alts)

    def test_process_ignored_schema_no_type(self):
        s1 = Resource("s1", "schema", {})  # None
        j1 = Resource("j1", "json", 42)  # integer
        ctx = ProcessingContext([s1], [j1], False)
        general, alts = self.comparator.process(ctx, "", {})
        self.assertEqual(general, {"type": "integer", "j2sElementTrigger": ["j1"]})
        self.assertIsNone(alts)

    def test_process_any_type_from_json(self):
        j1 = Resource("j1", "json", (1, 2))  # any
        ctx = ProcessingContext([], [j1], False)
        general, alts = self.comparator.process(ctx, "", {})
        self.assertEqual(general, {"type": "any", "j2sElementTrigger": ["j1"]})
        self.assertIsNone(alts)

    def test_process_duplicate_types_combined_ids(self):
        s1 = Resource("s1", "schema", {"type": "string"})
        j1 = Resource("j1", "json", "text")  # string
        s2 = Resource("s2", "schema", {"type": "string"})
        ctx = ProcessingContext([s1, s2], [j1], False)
        general, alts = self.comparator.process(ctx, "", {})
        self.assertEqual(
            general, {"type": "string", "j2sElementTrigger": ["j1", "s1", "s2"]}
        )  # sorted
        self.assertIsNone(alts)

    def test_process_env_and_prev_not_used(self):
        # env and prev_result are params but not used in logic, just to confirm
        s1 = Resource("s1", "schema", {"type": "string"})
        ctx = ProcessingContext([s1], [], False)
        general, alts = self.comparator.process(ctx, "/some/env", {"other": "data"})
        self.assertEqual(general, {"type": "string", "j2sElementTrigger": ["s1"]})
        self.assertIsNone(alts)

    def test_process_schema_anyof_keeps_all_types(self):
        s1 = Resource("s1", "schema", {"anyOf": [{"type": "string"}, {"type": "null"}]})
        ctx = ProcessingContext([s1], [], False)
        general, alts = self.comparator.process(ctx, "", {})
        self.assertIsNone(general)
        self.assertEqual(
            alts,
            [
                {"type": "string", "j2sElementTrigger": ["s1"]},
                {"type": "null", "j2sElementTrigger": ["s1"]},
            ],
        )

    def test_process_schema_anyof_and_json_string_keeps_nullable(self):
        s1 = Resource("s1", "schema", {"anyOf": [{"type": "string"}, {"type": "null"}]})
        j1 = Resource("j1", "json", "workday")
        ctx = ProcessingContext([s1], [j1], False)
        general, alts = self.comparator.process(ctx, "", {})
        self.assertIsNone(general)
        self.assertEqual(
            alts,
            [
                {"type": "string", "j2sElementTrigger": ["j1", "s1"]},
                {"type": "null", "j2sElementTrigger": ["s1"]},
            ],
        )
