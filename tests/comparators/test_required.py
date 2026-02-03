import unittest

from genschema.comparators.required import RequiredComparator
from genschema.comparators.template import ProcessingContext, Resource


class TestRequiredComparator(unittest.TestCase):
    def setUp(self):
        self.comparator = RequiredComparator()

    # Tests for can_process
    def test_can_process_object_type_not_pseudo(self):
        ctx = ProcessingContext([], [], False)
        node = {"type": "object", "isPseudoArray": False}
        self.assertTrue(self.comparator.can_process(ctx, "", node))

    def test_can_process_object_type_pseudo(self):
        # Добавляем хотя бы один JSON, чтобы отключить условие "нет json"
        dummy_json = Resource("j1", "json", {})
        ctx = ProcessingContext([], [dummy_json], False)
        node = {"type": "object", "isPseudoArray": True}
        self.assertFalse(self.comparator.can_process(ctx, "", node))

    def test_can_process_type_none(self):
        ctx = ProcessingContext([], [], False)
        node = {}  # type is None
        self.assertTrue(self.comparator.can_process(ctx, "", node))

    def test_can_process_no_jsons(self):
        ctx = ProcessingContext([Resource("s1", "schema", {})], [], False)  # no jsons
        node = {"type": "array"}  # even non-object
        self.assertTrue(self.comparator.can_process(ctx, "", node))

    def test_can_process_non_object_with_jsons(self):
        ctx = ProcessingContext([], [Resource("j1", "json", {})], False)  # has jsons
        node = {"type": "array"}
        self.assertFalse(self.comparator.can_process(ctx, "", node))

    def test_can_process_object_without_isPseudoArray(self):
        ctx = ProcessingContext([], [], False)
        node = {"type": "object"}  # no isPseudoArray, assumes False
        self.assertTrue(self.comparator.can_process(ctx, "", node))

    # Tests for process
    def test_process_no_jsons(self):
        ctx = ProcessingContext([], [], False)
        general, alts = self.comparator.process(ctx, "", {})
        self.assertIsNone(general)
        self.assertIsNone(alts)

    def test_process_jsons_not_dicts(self):
        j1 = Resource("j1", "json", [1, 2])  # list
        j2 = Resource("j2", "json", "string")  # str
        ctx = ProcessingContext([], [j1, j2], False)
        general, alts = self.comparator.process(ctx, "", {})
        self.assertIsNone(general)  # no keys
        self.assertIsNone(alts)

    def test_process_single_json_dict(self):
        j1 = Resource("j1", "json", {"a": 1, "b": 2})
        ctx = ProcessingContext([], [j1], False)
        general, alts = self.comparator.process(ctx, "", {})
        self.assertEqual(
            general, {"required": ["a", "b"]}
        )  # all keys are required since only one json
        self.assertIsNone(alts)

    def test_process_multiple_jsons_common_keys(self):
        j1 = Resource("j1", "json", {"a": 1, "b": 2, "c": 3})
        j2 = Resource("j2", "json", {"a": 4, "b": 5})
        j3 = Resource("j3", "json", {"a": 6, "b": 7, "d": 8})
        ctx = ProcessingContext([], [j1, j2, j3], False)
        general, alts = self.comparator.process(ctx, "", {})
        self.assertEqual(general, {"required": ["a", "b"]})  # common to all
        self.assertIsNone(alts)

    def test_process_multiple_jsons_no_common_keys(self):
        j1 = Resource("j1", "json", {"a": 1})
        j2 = Resource("j2", "json", {"b": 2})
        ctx = ProcessingContext([], [j1, j2], False)
        general, alts = self.comparator.process(ctx, "", {})
        self.assertIsNone(general)  # no required
        self.assertIsNone(alts)

    def test_process_mixed_jsons_some_not_dicts(self):
        j1 = Resource("j1", "json", {"a": 1, "b": 2})
        j2 = Resource("j2", "json", {"a": 3})
        j3 = Resource("j3", "json", [4, 5])  # not dict, skipped for keys
        ctx = ProcessingContext([], [j1, j2, j3], False)
        general, alts = self.comparator.process(ctx, "", {})
        self.assertIsNone(general)  # no keys present in ALL (since j3 not dict, makes all False)
        self.assertIsNone(alts)

    def test_process_keys_sorted(self):
        j1 = Resource("j1", "json", {"c": 1, "a": 2, "b": 3})
        j2 = Resource("j2", "json", {"a": 4, "b": 5, "c": 6})
        ctx = ProcessingContext([], [j1, j2], False)
        general, alts = self.comparator.process(ctx, "", {})
        self.assertEqual(general, {"required": ["a", "b", "c"]})  # sorted
        self.assertIsNone(alts)

    def test_process_env_and_node_not_used(self):
        j1 = Resource("j1", "json", {"a": 1})
        ctx = ProcessingContext([], [j1], False)
        general, alts = self.comparator.process(ctx, "/some/path", {"type": "object"})
        self.assertEqual(general, {"required": ["a"]})
        self.assertIsNone(alts)

    def test_process_schemas_required_narrows(self):
        s1 = Resource("s1", "schema", {"required": ["a"]})
        j1 = Resource("j1", "json", {"a": 1, "b": 2})
        ctx = ProcessingContext([s1], [j1], False)
        general, alts = self.comparator.process(ctx, "", {})
        self.assertEqual(general, {"required": ["a"]})
        self.assertIsNone(alts)
