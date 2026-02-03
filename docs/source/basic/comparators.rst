Writing Custom Comparators
==========================

This section explains how to extend genschema with your own comparators.
Comparators are small, focused components that add or adjust fields in the
generated JSON Schema.

Overview
--------

A comparator is a class that implements two methods:

* ``can_process(ctx, env, prev_result) -> bool``
* ``process(ctx, env, prev_result) -> (updates, alternatives)``

Comparators are executed for every node of the schema tree. The pipeline
passes the current context and the partial schema node being built. The
core ``TypeComparator`` always runs first to establish the node ``type``,
then all registered comparators run in registration order. The
comparator can:

* Add or update fields in the current node.
* Provide alternative nodes (for ``anyOf`` / ``oneOf``).
* Mark fields for deletion using ``ToDelete``.

Where Comparators Run
---------------------

The pipeline descends into the schema based on the inferred ``type``:

* ``object`` -> each property is processed in its own sub-context.
* ``array`` -> the ``items`` sub-context is processed.
* pseudo-arrays -> handled by the pseudo-array handler.

The ``env`` argument is a path-like string showing where you are in the tree:

* ``/`` (root)
* ``/properties/name``
* ``/items``
* ``/patternProperties/<pattern>``

Use this to scope your comparator to a specific level.

Core Types and Interfaces
-------------------------

The base classes live in ``genschema/comparators/template.py``:

* ``Comparator``: base class.
* ``ComparatorResult``: return type alias.
* ``ProcessingContext``: current inputs.
* ``Resource``: wrapper for each input schema or JSON instance.
* ``ToDelete``: marker for fields that should be removed.

Important fields in ``ProcessingContext``:

* ``schemas``: list of input JSON Schemas (if any).
* ``jsons``: list of input JSON instances (if any).
* ``sealed``: when ``True``, comparators should avoid introducing ``anyOf``.

Comparator Result Contract
--------------------------

``process()`` returns a pair ``(updates, alternatives)``:

* ``updates``: a ``dict`` merged into the current node.
* ``alternatives``: a list of schema nodes that become ``anyOf`` or ``oneOf``.

Return ``(None, None)`` when nothing should be changed.

Notes:

* If ``ctx.sealed`` is ``True``, comparators should not emit alternatives.
* The pipeline merges ``updates`` into the current node using ``dict.update``.
* If you return a ``ToDelete`` value for a key, the pipeline removes it later.

Minimal Comparator Example
--------------------------

The simplest comparator just adds a field:

.. code-block:: python

   from genschema.comparators.template import Comparator, ComparatorResult, ProcessingContext


   class TitleComparator(Comparator):
       name = "title"

       def can_process(self, ctx: ProcessingContext, env: str, prev_result: dict) -> bool:
           # Only at the root node, and only if not already set.
           return env == "/" and "title" not in prev_result

       def process(self, ctx: ProcessingContext, env: str, prev_result: dict) -> ComparatorResult:
           return {"title": "Generated schema"}, None

Adding JSON Schema Version
--------------------------

To set the JSON Schema version at the top level (root only):

.. code-block:: python

   from genschema.comparators.template import Comparator, ComparatorResult, ProcessingContext


   class SchemaVersionComparator(Comparator):
       name = "schema_version"

       def __init__(self, version: str = "https://json-schema.org/draft/2020-12/schema"):
           self._version = version

       def can_process(self, ctx: ProcessingContext, env: str, prev_result: dict) -> bool:
           return env == "/" and "$schema" not in prev_result

       def process(self, ctx: ProcessingContext, env: str, prev_result: dict) -> ComparatorResult:
           return {"$schema": self._version}, None

Working With Alternatives (anyOf / oneOf)
-----------------------------------------

If a comparator needs to emit alternatives, return them in the second tuple item.
Each alternative is a schema node fragment.

.. code-block:: python

   def process(self, ctx: ProcessingContext, env: str, prev_result: dict) -> ComparatorResult:
       variants = [
           {"type": "string"},
           {"type": "integer"},
       ]
       if ctx.sealed:
           # In sealed context, choose a deterministic single option.
           return variants[0], None
       return None, variants

When alternatives are returned, the pipeline will wrap them into the configured
base combinator (``anyOf`` or ``oneOf``).

Using Input Data
----------------

The context provides both schemas and JSON instances. Each entry is a ``Resource``
with ``id``, ``type``, and ``content``:

.. code-block:: python

   for s in ctx.schemas:
       if isinstance(s.content, dict):
           # Use s.content to inspect schema fields.
           pass

   for j in ctx.jsons:
       # j.content is a raw JSON value.
       pass

Best Practices
--------------

* Keep ``can_process`` fast and side-effect free.
* Avoid mutating ``prev_result`` or ``ctx`` in-place.
* Scope behavior using ``env`` to avoid unintended changes in nested nodes.
* Respect ``ctx.sealed`` to avoid creating new unions.
* Return ``None`` when no changes are required.

Registering a Comparator (Python)
---------------------------------

``TypeComparator`` is the core comparator and must be passed via ``core_comparator``
when creating a ``Converter``. All other comparators are registered via ``register``:

.. code-block:: python

   from genschema import Converter
   from genschema.comparators import RequiredComparator, SchemaVersionComparator

   conv = Converter()
   conv.register(RequiredComparator())
   conv.register(SchemaVersionComparator())

Registering a Comparator (CLI)
------------------------------

The CLI registers a default set of comparators. To disable one, use the flags
shown by ``genschema --help``. If you add your own comparator, you can:

* Register it in your own Python script (recommended), or
* Extend ``genschema/cli.py`` to include it in the CLI pipeline.

Troubleshooting
---------------

* If your comparator never runs, check ``can_process`` and ``env``.
* If fields disappear, ensure you are not returning ``ToDelete`` accidentally.
* If you see unexpected unions, verify when you are returning alternatives.
