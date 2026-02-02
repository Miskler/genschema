.. _python_quick_start:

Python Interface
================

The library provides a flexible Python API for generating JSON Schema from one or more JSON documents.

Basic usage example:

.. code-block:: python

    from json2schema import Converter, PseudoArrayHandler
    from json2schema.comparators import (
        FormatComparator,
        RequiredComparator,
        EmptyComparator,
        DeleteElement,
        TypeComparator,
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
    conv.register(RequiredComparator())        # Determines the "required" array
    conv.register(EmptyComparator())           # Handles min/maxProperties, min/maxItems,
                                               # and completely empty values/objects/arrays
    conv.register(DeleteElement())             # Removes technical attributes
                                               # (in particular — j2sElementTrigger list)
    conv.register(DeleteElement("isPseudoArray"))  # Removes the isPseudoArray marker
                                                   # (appears when pseudo_handler is active)

    # Execute the schema generation pipeline
    result = conv.run()

    print(result)

    # Optional: show execution time
    print(f"Generated in {time.time() - start:.4f} seconds")

See also
--------

- :mod:`json2schema.pipeline` — detailed documentation of the internal pipeline and comparator system
- :class:`json2schema.pseudo_arrays` — pseudo-array detection and normalization logic
