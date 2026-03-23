<div align="center">

# 🔍 genschema

<img src="https://raw.githubusercontent.com/Miskler/genschema/refs/heads/main/assets/logo.webp" width="70%" alt="logo.webp" />

*A powerful, intelligent library for generating JSON Schema from multiple JSON instances with **smart merging**, **advanced inference**, and **modular refinements**.*

[![Tests](https://miskler.github.io/genschema/tests-badge.svg)](https://miskler.github.io/genschema/tests/tests-report.html)
[![Coverage](https://miskler.github.io/genschema/coverage.svg)](https://miskler.github.io/genschema/coverage/)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://python.org)
[![PyPI - Package Version](https://img.shields.io/pypi/v/genschema?color=blue)](https://pypi.org/project/genschema/)
[![License](https://img.shields.io/github/license/Miskler/genschema.svg)](https://github.com/Miskler/genschema?tab=AGPL-3.0-1-ov-file)
[![BlackCode](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)
[![mypy](https://img.shields.io/badge/type--checked-mypy-blue?logo=python)](https://mypy.readthedocs.io/en/stable/index.html)

**[⭐ Star us on GitHub](https://github.com/Miskler/genschema)** | **[📚 Read the Docs](https://miskler.github.io/genschema/)** | **[🐛 Report Bug](https://github.com/Miskler/genschema/issues)**
</div>

<div align="center">

## ✨ Features

</div>

- 🎯 **Intelligent Merging** – Combines multiple JSON instances into a single schema
- 🔗 **Configurable Combinators** – Use `anyOf` or `oneOf` for conflicting types/properties
- 🧠 **Advanced Inference** – Automatic format detection (email, uuid, date-time, etc.)
- 🏷️ **Enum Inference** – Promotes compact string and integer fields to `enum` with safety guards
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
pip install genschema
```

### 30-Second Python Example

```python
from genschema import Converter, PseudoArrayHandler
from genschema.comparators import (
    EnumComparator,
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
conv.register(FormatComparator())  # Run format detection first
conv.register(EnumComparator())  # Then infer enum for short low-cardinality string/integer fields
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
genschema input1.json input2.json -o schema.json

# Use oneOf instead of anyOf
genschema *.json --base-of oneOf -o schema.json

# Disable refinements
genschema data.json --no-format --no-enum --no-required --no-pseudo-array

# Read from stdin
cat data.json | genschema - -o schema.json
```

<div align="center">

## 📊 Comparison with GenSON

</div>

| Feature                     | genschema                                              | GenSON                                                   |
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

> **Note**: Performance measured on static datasets of varying complexity. genschema prioritizes richer inference and flexibility over raw speed.

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
git clone https://github.com/Miskler/genschema.git
cd genschema
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

- **[📖 Full Documentation](https://miskler.github.io/genschema/)**
- **[🚀 Quick Start Guide](https://miskler.github.io/genschema/basic/quick_start/)**
- **[🔧 API Reference](https://miskler.github.io/genschema/reference/api/)**

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
