import unittest

from genschema.comparators.preserve_common_keywords import (
    PreserveCommonKeywordsComparator,
)
from genschema.comparators.template import ProcessingContext, Resource


class TestPreserveCommonKeywordsComparator(unittest.TestCase):
    def setUp(self) -> None:
        self.comparator = PreserveCommonKeywordsComparator()

    def test_can_process_requires_schema_inputs(self) -> None:
        self.assertFalse(self.comparator.can_process(ProcessingContext([], [], False), "", {}))
        self.assertTrue(
            self.comparator.can_process(
                ProcessingContext([Resource("s1", "schema", {"type": "object"})], [], False),
                "",
                {},
            )
        )

    def test_process_restores_shared_non_structural_keywords(self) -> None:
        ctx = ProcessingContext(
            [
                Resource(
                    "s1",
                    "schema",
                    {
                        "type": "object",
                        "title": "Address",
                        "description": "Postal address",
                        "properties": {"street": {"type": "string"}},
                    },
                ),
                Resource(
                    "s2",
                    "schema",
                    {
                        "type": "object",
                        "title": "Address",
                        "description": "Postal address",
                        "properties": {"street": {"type": "string"}},
                    },
                ),
            ],
            [],
            False,
        )

        general, alts = self.comparator.process(ctx, "", {"type": "object"})

        self.assertEqual(
            general,
            {
                "description": "Postal address",
                "title": "Address",
            },
        )
        self.assertIsNone(alts)

    def test_process_does_not_override_merge_owned_keywords(self) -> None:
        ctx = ProcessingContext(
            [
                Resource(
                    "s1",
                    "schema",
                    {
                        "type": "object",
                        "required": ["id", "name"],
                        "properties": {"id": {"type": "integer"}},
                    },
                ),
                Resource(
                    "s2",
                    "schema",
                    {
                        "type": "object",
                        "required": ["id"],
                        "properties": {"id": {"type": "integer"}},
                    },
                ),
            ],
            [],
            False,
        )

        general, alts = self.comparator.process(ctx, "", {"type": "object"})

        self.assertIsNone(general)
        self.assertIsNone(alts)

    def test_process_does_not_replace_existing_node_value(self) -> None:
        ctx = ProcessingContext(
            [
                Resource("s1", "schema", {"title": "Address"}),
                Resource("s2", "schema", {"title": "Address"}),
            ],
            [],
            False,
        )

        general, _ = self.comparator.process(ctx, "", {"title": "Merged Address"})

        self.assertIsNone(general)


if __name__ == "__main__":
    unittest.main()
