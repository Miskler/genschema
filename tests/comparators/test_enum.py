import unittest

from genschema.comparators.enum import EnumComparator
from genschema.comparators.format import FormatComparator
from genschema.pipeline import Converter

ENUM_REJECT_FLAG = "j2sEnumRejected"


class TestEnumComparatorUnit(unittest.TestCase):
    def setUp(self):
        self.comparator = EnumComparator()

    def test_name(self):
        self.assertEqual(self.comparator.name, "enum")

    def test_can_process_string_type(self):
        self.assertTrue(self.comparator.can_process(None, "/properties/status", {"type": "string"}))

    def test_can_process_rejects_integer_type(self):
        self.assertFalse(
            self.comparator.can_process(None, "/properties/status", {"type": "integer"})
        )

    def test_can_process_rejects_non_scalar_type(self):
        self.assertFalse(
            self.comparator.can_process(None, "/properties/status", {"type": "object"})
        )
        self.assertFalse(self.comparator.can_process(None, "/properties/status", {"type": "array"}))

    def test_can_process_allows_excluded_property_names_for_flagging(self):
        for field_name in ("name", "title", "description", "message", "text"):
            with self.subTest(field_name=field_name):
                self.assertTrue(
                    self.comparator.can_process(
                        None, f"/properties/{field_name}", {"type": "string"}
                    )
                )

    def test_can_process_rejects_when_format_is_already_set(self):
        self.assertFalse(
            self.comparator.can_process(
                None,
                "/properties/email",
                {"type": "string", "format": "email"},
            )
        )

    def test_can_process_rejects_when_enum_already_rejected(self):
        self.assertFalse(
            self.comparator.can_process(
                None,
                "/properties/status",
                {"type": "string", ENUM_REJECT_FLAG: True},
            )
        )

    def test_can_process_rejects_when_enum_is_already_set(self):
        self.assertFalse(
            self.comparator.can_process(
                None,
                "/properties/status",
                {"type": "string", "enum": ["draft", "published"]},
            )
        )

    def test_can_process_rejects_union_nodes(self):
        for keyword in ("anyOf", "oneOf", "allOf"):
            with self.subTest(keyword=keyword):
                self.assertFalse(
                    self.comparator.can_process(
                        None,
                        "/properties/status",
                        {"type": "string", keyword: [{"type": "string"}]},
                    )
                )


class TestEnumComparatorIntegration(unittest.TestCase):
    def _make_converter(self, *comparators):
        converter = Converter()
        for comparator in comparators:
            converter.register(comparator)
        return converter

    def _property_schema(self, schema, name):
        return schema["properties"][name]

    def test_builds_string_enum_from_json_values(self):
        converter = self._make_converter(EnumComparator())
        converter.add_json({"status": "draft"})
        converter.add_json({"status": "published"})
        converter.add_json({"status": "draft"})

        result = converter.run()
        status_schema = self._property_schema(result, "status")

        self.assertEqual(status_schema["type"], "string")
        self.assertCountEqual(status_schema["enum"], ["draft", "published"])
        self.assertNotIn(ENUM_REJECT_FLAG, status_schema)

    def test_does_not_build_integer_enum_from_json_values(self):
        converter = self._make_converter(EnumComparator())
        converter.add_json({"code": 1})
        converter.add_json({"code": 2})
        converter.add_json({"code": 1})

        result = converter.run()
        code_schema = self._property_schema(result, "code")

        self.assertEqual(code_schema["type"], "integer")
        self.assertNotIn("enum", code_schema)
        self.assertNotIn(ENUM_REJECT_FLAG, code_schema)

    def test_merges_enum_candidates_from_schema_and_json(self):
        converter = self._make_converter(EnumComparator())
        converter.add_schema(
            {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["draft", "published"],
                    }
                },
            }
        )
        converter.add_json({"status": "archived"})
        converter.add_json({"status": "draft"})

        result = converter.run()
        status_schema = self._property_schema(result, "status")

        self.assertEqual(status_schema["type"], "string")
        self.assertCountEqual(status_schema["enum"], ["draft", "published", "archived"])
        self.assertNotIn(ENUM_REJECT_FLAG, status_schema)

    def test_does_not_build_enum_for_excluded_field_names(self):
        converter = self._make_converter(EnumComparator())
        converter.add_json({"name": "Alice"})
        converter.add_json({"name": "Bob"})
        converter.add_json({"name": "Alice"})

        result = converter.run()
        name_schema = self._property_schema(result, "name")

        self.assertEqual(name_schema["type"], "string")
        self.assertNotIn("enum", name_schema)
        self.assertTrue(name_schema.get(ENUM_REJECT_FLAG))

    def test_does_not_build_enum_when_format_keyword_exists_in_schema(self):
        converter = self._make_converter(EnumComparator())
        converter.add_schema(
            {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "format": "email",
                    }
                },
            }
        )
        converter.add_json({"email": "alpha@example.com"})
        converter.add_json({"email": "beta@example.com"})

        result = converter.run()
        email_schema = self._property_schema(result, "email")

        self.assertEqual(email_schema["type"], "string")
        self.assertEqual(email_schema.get("format"), "email")
        self.assertNotIn("enum", email_schema)

    def test_does_not_build_enum_for_datetime_strings_detected_by_format_comparator(self):
        converter = self._make_converter(FormatComparator(), EnumComparator())
        converter.add_json({"updatedAt": "2025-02-24 11:30:47"})
        converter.add_json({"updatedAt": "2024-12-19 10:53:15"})

        result = converter.run()
        updated_at_schema = self._property_schema(result, "updatedAt")

        self.assertEqual(updated_at_schema["type"], "string")
        self.assertEqual(updated_at_schema.get("format"), "date-time")
        self.assertNotIn("enum", updated_at_schema)

    def test_rejects_when_unique_values_exceed_default_threshold(self):
        converter = self._make_converter(EnumComparator())
        for index in range(17):
            converter.add_json({"status": f"value-{index}"})

        result = converter.run()
        status_schema = self._property_schema(result, "status")

        self.assertEqual(status_schema["type"], "string")
        self.assertNotIn("enum", status_schema)
        self.assertTrue(status_schema.get(ENUM_REJECT_FLAG))

    def test_rejects_long_free_text_by_average_length(self):
        converter = self._make_converter(EnumComparator())
        converter.add_json({"comment": "this is a very long free text fragment"})
        converter.add_json({"comment": "another long free text fragment here"})
        converter.add_json({"comment": "third long free text fragment as well"})

        result = converter.run()
        comment_schema = self._property_schema(result, "comment")

        self.assertEqual(comment_schema["type"], "string")
        self.assertNotIn("enum", comment_schema)
        self.assertTrue(comment_schema.get(ENUM_REJECT_FLAG))

    def test_rejects_blank_string_values_instead_of_building_empty_enum_item(self):
        converter = self._make_converter(EnumComparator())
        converter.add_json({"carbohydrates": ""})
        converter.add_json({"carbohydrates": ""})

        result = converter.run()
        carbohydrates_schema = self._property_schema(result, "carbohydrates")

        self.assertEqual(carbohydrates_schema["type"], "string")
        self.assertNotIn("enum", carbohydrates_schema)
        self.assertTrue(carbohydrates_schema.get(ENUM_REJECT_FLAG))

    def test_rejects_whitespace_only_string_values(self):
        converter = self._make_converter(EnumComparator())
        converter.add_json({"protein": "   "})
        converter.add_json({"protein": "\t"})

        result = converter.run()
        protein_schema = self._property_schema(result, "protein")

        self.assertEqual(protein_schema["type"], "string")
        self.assertNotIn("enum", protein_schema)
        self.assertTrue(protein_schema.get(ENUM_REJECT_FLAG))

    def test_rejects_digit_only_string_values(self):
        converter = self._make_converter(EnumComparator())
        converter.add_json({"year": "2023"})
        converter.add_json({"year": "2024"})

        result = converter.run()
        year_schema = self._property_schema(result, "year")

        self.assertEqual(year_schema["type"], "string")
        self.assertNotIn("enum", year_schema)
        self.assertTrue(year_schema.get(ENUM_REJECT_FLAG))

    def test_preserves_reject_flag_and_blocks_enum_on_next_run(self):
        first = self._make_converter(EnumComparator())
        for index in range(17):
            first.add_json({"status": f"value-{index}"})
        first_result = first.run()

        status_schema = self._property_schema(first_result, "status")
        self.assertTrue(status_schema.get(ENUM_REJECT_FLAG))
        self.assertNotIn("enum", status_schema)

        second = self._make_converter(EnumComparator())
        second.add_schema(first_result)
        second.add_json({"status": "draft"})
        second.add_json({"status": "published"})

        second_result = second.run()
        second_status_schema = self._property_schema(second_result, "status")

        self.assertEqual(second_status_schema["type"], "string")
        self.assertTrue(second_status_schema.get(ENUM_REJECT_FLAG))
        self.assertNotIn("enum", second_status_schema)

    def test_drops_existing_schema_enum_and_sets_reject_flag_when_new_data_breaks_rules(self):
        converter = self._make_converter(EnumComparator())
        converter.add_schema(
            {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["draft", "published"],
                    }
                },
            }
        )
        for index in range(17):
            converter.add_json({"status": f"value-{index}"})

        result = converter.run()
        status_schema = self._property_schema(result, "status")

        self.assertEqual(status_schema["type"], "string")
        self.assertNotIn("enum", status_schema)
        self.assertTrue(status_schema.get(ENUM_REJECT_FLAG))

    def test_supports_nested_properties(self):
        converter = self._make_converter(EnumComparator())
        converter.add_json({"meta": {"status": "draft"}})
        converter.add_json({"meta": {"status": "published"}})
        converter.add_json({"meta": {"status": "draft"}})

        result = converter.run()
        meta_schema = self._property_schema(result, "meta")
        status_schema = self._property_schema(meta_schema, "status")

        self.assertEqual(meta_schema["type"], "object")
        self.assertEqual(status_schema["type"], "string")
        self.assertCountEqual(status_schema["enum"], ["draft", "published"])
