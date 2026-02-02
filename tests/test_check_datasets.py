import glob
import json
import time

import pytest
from jsonschema import validate
from jsonschema.validators import Draft202012Validator

from json2schema2schema import Converter, PseudoArrayHandler
from json2schema2schema.comparators import (
    DeleteElement,
    EmptyComparator,
    FormatComparator,
    NoAdditionalProperties,
    RequiredComparator,
)

dataset_dir = "tests/datasets/"
dataset_files = glob.glob(f"{dataset_dir}*.json")
assert dataset_files, "No dataset files found in tests/datasets/"


@pytest.mark.parametrize("file_path", dataset_files)
def test_schema_generation_and_validation(file_path):
    print(f"\nProcessing dataset: {file_path}")

    # Step 1: Load the JSON data
    start_load = time.time()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    load_time = time.time() - start_load
    print(f"Time to load data: {round(load_time, 4)} seconds")

    # Step 2: Generate the schema
    start_gen = time.time()
    conv = Converter(pseudo_handler=PseudoArrayHandler(), base_of="anyOf")
    conv.add_json(
        data
    )  # Assuming add_json accepts data; if it requires filename, use conv.add_json(file_path)
    conv.register(FormatComparator())
    conv.register(RequiredComparator())
    conv.register(EmptyComparator())
    conv.register(NoAdditionalProperties())
    conv.register(DeleteElement())
    conv.register(DeleteElement("isPseudoArray"))
    schema = conv.run()
    gen_time = time.time() - start_gen
    print(f"Time to generate schema: {round(gen_time, 4)} seconds")

    # Step 3: Validate the schema itself (check if it's a valid JSON Schema)
    start_schema_val = time.time()
    try:
        Draft202012Validator.check_schema(schema)
        schema_val_time = time.time() - start_schema_val
        print(f"Time to validate schema: {round(schema_val_time, 4)} seconds")
        print("Schema is valid as a JSON Schema.")
    except Exception as e:  # Catch SchemaError or others
        pytest.fail(f"Generated schema for {file_path} is invalid: {str(e)}")

    # Step 4: Validate the data against the generated schema
    start_data_val = time.time()
    try:
        validate(instance=data, schema=schema)
        data_val_time = time.time() - start_data_val
        print(f"Time to validate data against schema: {round(data_val_time, 4)} seconds")
        print("Data validates successfully against the schema.")
    except Exception as e:  # Catch ValidationError or others
        pytest.fail(f"Data for {file_path} does not validate against schema: {str(e)}")
