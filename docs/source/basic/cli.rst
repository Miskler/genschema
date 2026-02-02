json2schema CLI Tool
====================

**json2schema** is a command-line utility that generates JSON Schema from one or more JSON documents.  
It supports multiple input files, stdin input, smart type merging with ``anyOf``/``oneOf``, pseudo-array detection, and several optional schema refinement comparators.

Features
--------

- Generate JSON Schema from single or multiple JSON instances
- Merge schemas using ``anyOf`` or ``oneOf`` combinators
- Automatic detection of pseudo-arrays (inhomogeneous arrays treated as object-like structures)
- Optional comparators:
  - Format detection (``format`` keyword)
  - Required properties inference
  - Empty value handling (``null`` vs absence)
  - Element deletion in special cases (e.g. pseudo-array markers)
- Output to file or stdout
- Rich console output with error reporting and timing

Installation
------------

.. code-block:: bash

   pip install json2schema

(adjust according to your actual package name / distribution method)

Usage
-----

.. code-block:: text

   json2schema [OPTIONS] [INPUTS]...

Arguments
~~~~~~~~~

``INPUTS``
    Paths to JSON files, or ``-`` to read from stdin.  
    Multiple files are allowed.  
    If no inputs are provided, help is shown and program exits.

Options
~~~~~~~

``-o``, ``--output`` OUTPUT
    Path to the output JSON Schema file.  
    If omitted, schema is printed to stdout.

``--base-of`` {anyOf,oneOf}
    Schema combination strategy when types differ across instances.  
    Default: ``anyOf``

``--no-pseudo-array``
    Disable pseudo-array detection and handling.

``--no-format``
    Disable inference of ``format`` keywords (email, date, uri, etc.).

``--no-required``
    Disable automatic population of the ``required`` array.

``--no-empty``
    Disable special handling of empty values / missing properties.

``--no-delete-element``
    Disable all ``DeleteElement`` comparators (including pseudo-array cleanup).

Examples
--------

Read single file and write schema to disk
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   json2schema data.json -o schema.json

Multiple files → anyOf combination
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   json2schema user1.json user2.json user3.json --base-of anyOf -o schema.json

Read from stdin
~~~~~~~~~~~~~~~

.. code-block:: bash

   cat record.json | json2schema -

   # or with redirection
   json2schema - < record.json

   # piping from another command
   curl https://api.example.com/data | json2schema -o api-schema.json

Use oneOf instead of anyOf
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   json2schema event-log-*.json --base-of oneOf -o events.schema.json

Disable most refinements (minimal schema)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   json2schema messy-data.json --no-format --no-required --no-empty --no-pseudo-array -o minimal.json

Exit Codes
----------

- ``0`` — success
- ``1`` — invalid JSON, file not found, schema generation error, etc.

Output
------

When writing to stdout, the schema is printed as formatted JSON (indent=2).  
When writing to file, the same formatted JSON is saved and a success message is shown.

Console also reports:

- number of processed JSON instances
- elapsed generation time

Implementation Notes
--------------------

The tool is built around a modular ``Converter`` class that:

1. Accepts multiple JSON documents
2. Applies a chain of comparators/transformers
3. Supports optional pseudo-array flattening
4. Uses configurable base combinator (``anyOf`` / ``oneOf``)

Comparators can be selectively disabled via CLI flags.

See also for more: :mod:`json2schema.cli`
