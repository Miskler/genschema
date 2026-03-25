.. _python_quick_start:

Python Interface
================

The library provides a flexible Python API for generating JSON Schema from one or more JSON documents.

Basic usage example:

.. code-block:: python

    from genschema import Converter, PseudoArrayHandler
    from genschema.comparators import (
        EnumComparator,
        FormatComparator,
        RequiredComparator,
        EmptyComparator,
        DeleteElement,
        TypeComparator,
    )
    from genschema.postprocessing import (
        SchemaReferenceExtractionConfig,
        SchemaReferencePostprocessor,
    )
    import time

    start = time.time()

    # Initialize the converter (reusable instance)
    conv = Converter(
        pseudo_handler=PseudoArrayHandler(),     # Supports detection & handling of pseudo-array structures
                                                 # (custom handlers can be implemented if needed)
        base_of="anyOf",                         # Combinator used for conflicting types/values:
                                                 # anyOf / oneOf / allOf
        core_comparator=TypeComparator()         # The 'type' attribute is mandatory for schema building,
                                                 # therefore it is handled separately as the core comparator
    )

    # You can add JSON data in several ways:
    # 1. From file path (string)
    conv.add_json("ClassCatalog.tree.json")

    # 2. From Python dict / list
    conv.add_json({
        "name": "alice@example.com",
        "email": "alice@example.com",
        "identifier": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
        "created": "2024-01-31"
    })

    # You can also add existing schemas (they will be merged)
    conv.add_schema({
        "type": "object",
        "properties": {
            "name": {
                "type": "object",
                "properties": {
                    "name": {"type": "integer"}
                }
            }
        }
    })

    # The core logic is driven by a chain of comparators / transformers
    conv.register(FormatComparator())          # Infers format keywords (date, email, uuid, uri, etc.)
    conv.register(EnumComparator())            # Infers enum for low-cardinality string fields
                                               # after format detection and persists free-text rejections
    conv.register(RequiredComparator())        # Determines the "required" array
    conv.register(EmptyComparator())           # Handles min/maxProperties, min/maxItems,
                                               # and completely empty values/objects/arrays
    conv.register(DeleteElement())             # Removes technical attributes
                                               # (in particular — j2sElementTrigger list)
    conv.register(DeleteElement("isPseudoArray"))  # Removes the isPseudoArray marker
                                                   # (appears when pseudo_handler is active)

    # Execute the schema generation pipeline
    result = conv.run()

    # Optional independent postprocessing step:
    # extract repeated / similar fragments into $defs + $ref
    result = SchemaReferencePostprocessor.process(
        result,
        SchemaReferenceExtractionConfig(
            similarity_threshold=0.85,
            min_total_keys=3,
        ),
    )

    print(result)

    # Optional: show execution time
    print(f"Generated in {time.time() - start:.4f} seconds")

``EnumComparator`` intentionally ignores integer fields. In practice numeric
values are too ambiguous: low-cardinality ids, years, counters, indexes, and
various external codes are common and cannot be separated from true enums by a
simple safe heuristic.

Postprocessing shared references
--------------------------------

``SchemaReferencePostprocessor`` runs **after** ``conv.run()``. It is
intentionally independent from ``Converter`` itself and can be applied to any
generated schema dict.

Typical use cases:

- extract repeated fragments into ``$defs``
- merge highly similar fragments, not only exact duplicates
- reduce schema duplication after generation

Minimal example:

.. code-block:: python

    schema = conv.run()
    schema = SchemaReferencePostprocessor.process(schema)

Important settings:

- ``similarity_threshold`` — how close structures must be to be grouped
- ``min_total_keys`` — minimum total number of structural keys before extraction is worth it
- ``min_occurrences`` — minimum number of occurrences in one group

This also works for **one input JSON** if that document contains repeated or
sufficiently similar nested structures.

See also
--------

- :mod:`genschema.pipeline` — detailed documentation of the internal pipeline and comparator system
- :class:`genschema.pseudo_arrays` — pseudo-array detection and normalization logic
- :mod:`genschema.postprocessing.schema_references` — reference extraction postprocessor
