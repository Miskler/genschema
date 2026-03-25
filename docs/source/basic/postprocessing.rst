Postprocessing
==============

genschema can optionally run an additional **independent** postprocessing step
after schema generation. This stage does not modify ``Converter`` and does not
require the converter to know anything about reference extraction.

The main entry point is:

- :class:`genschema.postprocessing.SchemaReferencePostprocessor`

It analyzes an already generated JSON Schema, finds repeated or highly similar
subschemas, merges each candidate group through the regular genschema pipeline,
then moves the result into ``$defs`` and replaces occurrences with ``$ref``.

Why this is separate
--------------------

The generator and the postprocessor solve different problems:

- ``Converter`` builds the schema from JSON instances and input schemas
- ``SchemaReferencePostprocessor`` reorganizes the resulting schema for reuse

That separation makes the postprocessing stage reusable for:

- schemas produced by one JSON input
- schemas produced by many JSON inputs
- schemas loaded from elsewhere, as long as they are ordinary JSON Schema dicts

Basic example
-------------

.. code-block:: python

   from genschema import Converter, PseudoArrayHandler
   from genschema.comparators import (
       DeleteElement,
       EmptyComparator,
       FormatComparator,
       RequiredComparator,
   )
   from genschema.postprocessing import (
       SchemaReferenceExtractionConfig,
       SchemaReferencePostprocessor,
   )

   conv = Converter(
       pseudo_handler=PseudoArrayHandler(),
       base_of="anyOf",
   )

   conv.add_json("input1.json")
   conv.add_json("input2.json")
   conv.add_json("input3.json")

   conv.register(FormatComparator())
   conv.register(RequiredComparator())
   conv.register(EmptyComparator())
   conv.register(DeleteElement())
   conv.register(DeleteElement("isPseudoArray"))

   schema = conv.run()

   schema = SchemaReferencePostprocessor.process(
       schema,
       SchemaReferenceExtractionConfig(
           similarity_threshold=0.8,
           min_total_keys=3,
       ),
   )

Single JSON also works
----------------------

The postprocessor does **not** require multiple input files.

If one document contains repeated or highly similar nested structures, those
fragments can still be extracted into shared references:

.. code-block:: python

   conv = Converter(pseudo_handler=PseudoArrayHandler(), base_of="anyOf")
   conv.add_json("input.json")

   conv.register(FormatComparator())
   conv.register(RequiredComparator())
   conv.register(EmptyComparator())
   conv.register(DeleteElement())
   conv.register(DeleteElement("isPseudoArray"))

   schema = conv.run()
   schema = SchemaReferencePostprocessor.process(schema)

For example, one input document may still contain:

- repeated address objects
- similar person-like objects such as ``customer`` and ``manager``
- similar location-like objects such as ``warehouse`` and ``pickupPoint``

CLI support
-----------

Common reference-extraction settings are also available from the CLI:

.. code-block:: bash

   genschema input.json --extract-refs -o schema.json

   genschema input.json \
       --extract-refs \
       --refs-similarity-threshold 0.9 \
       --refs-min-total-keys 4 \
       --refs-min-occurrences 2 \
       -o schema.json

For custom merge strategies, naming strategies, or non-default merge
comparators, use the Python API.

Configuration
-------------

Use :class:`genschema.postprocessing.SchemaReferenceExtractionConfig` to adjust
the extraction behavior.

Important options:

- ``similarity_threshold``: similarity score in the ``(0, 1]`` range
- ``min_total_keys``: minimum combined number of structural keys before a node is worth extracting
- ``min_occurrences``: minimum number of matching nodes in a group
- ``defs_key``: output container for extracted definitions, default ``$defs``
- ``ref_prefix``: custom prefix for created references
- ``merge_base_of``: ``anyOf`` / ``oneOf`` / ``allOf`` for the merge stage
- ``merge_comparator_factories``: comparators used during group merge
- ``preserve_common_keywords``: enables a final comparator that restores
  identical non-structural schema keywords such as ``title`` or ``description``
- ``merge_strategy``: custom full merge implementation
- ``name_factory``: custom naming strategy for created definitions

How similarity works
--------------------

The default strategy compares structural tokens collected from a subschema:

- object property names
- pattern-property names
- nested object and array shape
- type signatures
- selected keywords such as ``format`` and ``enum``

That means structures may still be merged when they are not perfectly equal.

Example:

- object A has ``id``, ``fullName``, ``email``, ``phone``
- object B has ``id``, ``fullName``, ``email``, ``phone``, ``department``

With a relaxed enough ``similarity_threshold``, both can become one shared
definition. The merged result is then built through the normal genschema merge
pipeline, so conflicts are represented using the configured combinator logic.

Minimum structure size
----------------------

Extraction is intentionally conservative. Very small fragments are often not
worth moving into shared refs because the schema becomes harder to read without
meaningful deduplication.

By default:

- ``min_total_keys = 3``

So two tiny objects with only one or two keys will stay inline unless you lower
that threshold.

Result shape
------------

The postprocessor returns a new schema dict. It does not mutate the original
input object in place.

Typical result:

.. code-block:: python

   {
       "$defs": {
           "Address": {
               "type": "object",
               "properties": {
                   "street": {"type": "string"},
                   "city": {"type": "string"},
                   "postalCode": {"type": "string"},
               },
           }
       },
       "properties": {
           "billingAddress": {"$ref": "#/$defs/Address"},
           "shippingAddress": {"$ref": "#/$defs/Address"},
       },
   }

Notes
-----

- existing ``$ref`` nodes are not treated as extraction candidates
- existing definition sections can be skipped during candidate discovery
- overlapping candidate groups are resolved so the same fragment is not extracted twice
- definition names can be customized
