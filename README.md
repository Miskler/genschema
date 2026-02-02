<div align="center">

# 🔍 json2schema

<img src="https://via.placeholder.com/800x200.png?text=json2schema+Logo" width="70%" alt="json2schema logo" />

*A powerful, intelligent library for generating JSON Schema from multiple JSON instances with **smart merging**, **advanced inference**, and **modular refinements**.*

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](https://github.com/Miskler/json2schema/actions)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen)](https://github.com/Miskler/json2schema)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://python.org)
[![PyPI - Package Version](https://img.shields.io/pypi/v/json2schema?color=blue)](https://pypi.org/project/json2schema/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![BlackCode](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)
[![mypy](https://img.shields.io/badge/type--checked-mypy-blue?logo=python)](https://mypy.readthedocs.io/en/stable/index.html)

**[⭐ Star us on GitHub](https://github.com/Miskler/json2schema)** | **[📚 Read the Docs](https://miskler.github.io/json2schema/)** | **[🐛 Report Bug](https://github.com/Miskler/json2schema/issues)**
</div>

## ✨ Features

- 🎯 **Intelligent Merging** – Combines multiple JSON instances into a single schema
- 🔗 **Configurable Combinators** – Use `anyOf` or `oneOf` for conflicting types/properties
- 🧠 **Advanced Inference** – Automatic format detection (email, uuid, date-time, etc.)
- 📍 **Required & Empty Handling** – Smart inference of `required`, `minProperties`, `minItems`, etc.
- 🔍 **Pseudo-Array Detection** – Treats inhomogeneous arrays as object-like structures when needed
- ⚡ **Modular Pipeline** – Chain of configurable comparators for full control
- 🛠️ **CLI & Python API** – Flexible usage from command line or code
- 📝 **Rich Output** – Colored console feedback with timing and instance count

<div align="center">

## 🚀 Quick Start

</div>

### Installation

```bash
pip install json2schema
```

### 30-Second Python Example

```python
from json2schema import Converter, PseudoArrayHandler
from json2schema.comparators import (
    FormatComparator,
    RequiredComparator,
    EmptyComparator,
    DeleteElement,
)

conv = Converter(
    pseudo_handler=PseudoArrayHandler(),
    base_of="anyOf",  # or "oneOf"
)

# Add JSON data (files, dicts, or existing schemas)
conv.add_json("example1.json")
conv.add_json("example2.json")
conv.add_json({"name": "Alice", "email": "alice@example.com"})

# Register optional refinements
conv.register(FormatComparator())
conv.register(RequiredComparator())
conv.register(EmptyComparator())
conv.register(DeleteElement())
conv.register(DeleteElement("isPseudoArray"))

# Generate schema
result = conv.run()

print(result)  # Pretty-printed JSON Schema
```

### CLI Usage

```bash
# Basic: single or multiple files
json2schema input1.json input2.json -o schema.json

# Use oneOf instead of anyOf
json2schema *.json --base-of oneOf -o schema.json

# Disable refinements
json2schema data.json --no-format --no-required --no-pseudo-array

# Read from stdin
cat data.json | json2schema - -o schema.json
```

<div align="center">

## 📊 Comparison with GenSON

</div>

| Feature                     | json2schema                                              | GenSON                                                   |
|-----------------------------|----------------------------------------------------------|----------------------------------------------------------|
| Multiple Instance Merging   | Yes                                                      | Yes                                                      |
| Variant Type Handling       | Configurable `anyOf` or `oneOf`                           | `anyOf` only                                             |
| Format Inference            | Yes (email, date-time, uuid, uri, etc.)                  | No                                                       |
| Required Properties         | Configurable inference                                   | Yes (present in all objects)                             |
| Empty/Min-Max Handling      | Yes (`minProperties`, `minItems`, etc.)                  | Limited                                                  |
| Pseudo-Array Detection      | Yes                                                      | No                                                       |
| Modular Extensions          | Comparator pipeline (easy to add/remove)                 | `SchemaStrategy` subclasses                               |
| CLI Support                 | Full-featured with rich output                           | Basic (`genson`)                                         |
| Performance (avg. benchmark)| ~2.1× slower                                             | Faster                                                   |

> **Note**: Performance measured on static datasets of varying complexity. json2schema prioritizes richer inference and flexibility over raw speed.

<div align="center">

## 🏗️ Architecture

</div>

Modular pipeline design for clean, extensible code:

```
┌─────────────────┐      ┌─────────────────┐
│   Input JSONs   │      │  Input Schemas  │
└─────────────────┘      └─────────────────┘
         │                       │
         └──────────┬────────────┘
                    ▼
            ┌───────────────┐
            │ Pipeline Run  │
            └───────────────┘
                    ▼
         ┌───────────────────┐
         │  Process Layer    │◀─────┐
         └───────────────────┘      │
                    │               │
                    ▼               │
        ┌─────────────────────┐     │
        │ Comparators Chain   │─────┘
        └─────────────────────┘
                    │
                    ▼
            ┌───────────────┐
            │    Result     │
            └───────────────┘
```

<div align="center">

## 🛠️ Development

</div>

### Setup

```bash
git clone https://github.com/Miskler/json2schema.git
cd json2schema
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"    # or make install-dev if Makefile exists
```

### Common Commands

```bash
make test          # Run tests with coverage
make lint          # Lint code
make type-check    # mypy checking
make format        # Format with black
make docs          # Build documentation
```

<div align="center">

## 📚 Documentation

</div>

- **[📖 Full Documentation](https://miskler.github.io/json2schema/)**
- **[🚀 Quick Start Guide](https://miskler.github.io/json2schema/basic/quick_start/)**
- **[🔧 API Reference](https://miskler.github.io/json2schema/reference/api/)**
- **[🆚 Comparison Details](https://miskler.github.io/json2schema/advanced/comparison/)**

<div align="center">

## 🤝 Contributing
### ***We welcome contributions!***

</div>

Fork the repository, create a feature branch, and submit a pull request.  
Ensure tests pass and code follows black/mypy style.

```bash
make test
make lint
make type-check
```

<div align="center">

## 📄 License

</div>

AGPL-3.0 License – see [LICENSE](LICENSE) file for details.

*Made with ❤️ for developers working with evolving JSON data*