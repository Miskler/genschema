import json
import tempfile
import unittest
from pathlib import Path

from genschema.cli import main


class TestCliReferenceExtraction(unittest.TestCase):
    def test_cli_keeps_base_schema_without_extract_refs_flag(self) -> None:
        payload = {
            "billingAddress": {
                "street": "1 Main St",
                "city": "Boston",
                "zip": "02108",
            },
            "shippingAddress": {
                "street": "2 Main St",
                "city": "Boston",
                "zip": "02109",
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "input.json"
            output_path = tmp_path / "schema.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")

            main([str(input_path), "-o", str(output_path)])

            schema = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertNotIn("$defs", schema)
            self.assertIn("properties", schema)
            self.assertIn("billingAddress", schema["properties"])
            self.assertIn("shippingAddress", schema["properties"])

    def test_cli_extract_refs_emits_defs_and_ref_replacements(self) -> None:
        payload = {
            "billingAddress": {
                "street": "1 Main St",
                "city": "Boston",
                "zip": "02108",
            },
            "shippingAddress": {
                "street": "2 Main St",
                "city": "Boston",
                "zip": "02109",
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "input.json"
            output_path = tmp_path / "schema.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")

            main(
                [
                    str(input_path),
                    "-o",
                    str(output_path),
                    "--extract-refs",
                    "--refs-similarity-threshold",
                    "1.0",
                ]
            )

            schema = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("$defs", schema)
            self.assertEqual(len(schema["$defs"]), 1)

            billing = schema["properties"]["billingAddress"]
            shipping = schema["properties"]["shippingAddress"]
            self.assertEqual(billing["$ref"], shipping["$ref"])


if __name__ == "__main__":
    unittest.main()
