import unittest

from genschema.postprocessing import SchemaReferenceExtractionConfig, SchemaReferencePostprocessor


def _address_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "street": {"type": "string"},
            "city": {"type": "string"},
            "zip": {"type": "string"},
        },
        "required": ["street", "city"],
    }


class TestSchemaReferencePostprocessor(unittest.TestCase):
    def test_extracts_identical_objects_into_shared_defs(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "billingAddress": _address_schema(),
                "shippingAddress": _address_schema(),
            },
        }

        result = SchemaReferencePostprocessor.process(
            schema,
            SchemaReferenceExtractionConfig(similarity_threshold=1.0),
        )

        self.assertIn("$defs", result)
        self.assertEqual(len(result["$defs"]), 1)

        billing_ref = result["properties"]["billingAddress"]["$ref"]
        shipping_ref = result["properties"]["shippingAddress"]["$ref"]
        self.assertEqual(billing_ref, shipping_ref)

        definition = next(iter(result["$defs"].values()))
        self.assertEqual(definition["type"], "object")
        self.assertEqual(sorted(definition["properties"].keys()), ["city", "street", "zip"])
        self.assertEqual(definition["required"], ["city", "street"])

    def test_similarity_threshold_controls_near_duplicate_grouping(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "author": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                    },
                    "required": ["id", "email"],
                },
                "owner": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                        "phone": {"type": "string"},
                    },
                    "required": ["id", "phone"],
                },
            },
        }

        strict_result = SchemaReferencePostprocessor.process(
            schema,
            SchemaReferenceExtractionConfig(similarity_threshold=0.95),
        )
        self.assertNotIn("$defs", strict_result)

        relaxed_result = SchemaReferencePostprocessor.process(
            schema,
            SchemaReferenceExtractionConfig(similarity_threshold=0.85),
        )

        self.assertIn("$defs", relaxed_result)
        self.assertEqual(
            relaxed_result["properties"]["author"]["$ref"],
            relaxed_result["properties"]["owner"]["$ref"],
        )

        merged_definition = next(iter(relaxed_result["$defs"].values()))
        self.assertEqual(
            sorted(merged_definition["properties"].keys()), ["email", "id", "name", "phone"]
        )
        self.assertEqual(merged_definition["required"], ["id"])
        self.assertEqual(merged_definition["properties"]["email"]["format"], "email")

    def test_min_total_keys_defaults_to_three(self) -> None:
        tiny = {
            "type": "object",
            "properties": {
                "first": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "string"},
                        "b": {"type": "string"},
                    },
                },
                "second": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "string"},
                        "b": {"type": "string"},
                    },
                },
            },
        }

        default_result = SchemaReferencePostprocessor.process(tiny)
        self.assertNotIn("$defs", default_result)

        lowered_result = SchemaReferencePostprocessor.process(
            tiny,
            SchemaReferenceExtractionConfig(min_total_keys=2, similarity_threshold=1.0),
        )
        self.assertIn("$defs", lowered_result)
        self.assertEqual(
            lowered_result["properties"]["first"]["$ref"],
            lowered_result["properties"]["second"]["$ref"],
        )

    def test_merge_pipeline_keeps_type_conflicts_inside_shared_definition(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "warehouse": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "code": {"type": "string"},
                    },
                },
                "pickupPoint": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "code": {"type": "integer"},
                    },
                },
            },
        }

        result = SchemaReferencePostprocessor.process(
            schema,
            SchemaReferenceExtractionConfig(similarity_threshold=0.8),
        )

        definition = next(iter(result["$defs"].values()))
        code_schema = definition["properties"]["code"]

        self.assertIn("anyOf", code_schema)
        variant_types = {variant["type"] for variant in code_schema["anyOf"]}
        self.assertEqual(variant_types, {"string", "integer"})

    def test_merge_pipeline_restores_shared_metadata_via_last_comparator(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "billingAddress": {
                    "type": "object",
                    "title": "Address",
                    "description": "Postal address",
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"},
                        "zip": {"type": "string"},
                    },
                },
                "shippingAddress": {
                    "type": "object",
                    "title": "Address",
                    "description": "Postal address",
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"},
                        "zip": {"type": "string"},
                    },
                },
            },
        }

        result = SchemaReferencePostprocessor.process(
            schema,
            SchemaReferenceExtractionConfig(similarity_threshold=1.0),
        )

        definition = next(iter(result["$defs"].values()))
        self.assertEqual(definition["title"], "Address")
        self.assertEqual(definition["description"], "Postal address")


if __name__ == "__main__":
    unittest.main()
