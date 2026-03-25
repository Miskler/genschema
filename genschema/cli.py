import argparse
import json
import sys
import time

from rich.console import Console

from . import Converter, PseudoArrayHandler
from .comparators import (
    DeleteElement,
    EmptyComparator,
    EnumComparator,
    FormatComparator,
    RequiredComparator,
    SchemaVersionComparator,
)
from .postprocessing import (
    SchemaReferenceExtractionConfig,
    SchemaReferencePostprocessor,
)

console = Console()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate JSON Schema from JSON input using genschema.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  genschema input.json -o schema.json
  genschema input1.json input2.json --base-of oneOf
  genschema input.json --extract-refs -o schema.json
  cat input.json | genschema -
  genschema --base-of anyOf < input.json
  genschema dir/file1.json dir/file2.json -o schema.json
        """,
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Paths to input JSON files. Use '-' for stdin. "
        "If no arguments are provided, show this help message.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Path to output JSON Schema file. If not specified, output to stdout.",
    )
    parser.add_argument(
        "--base-of",
        choices=["anyOf", "oneOf"],
        default="anyOf",
        help="Combinator for differing types (default: anyOf).",
    )
    parser.add_argument(
        "--no-pseudo-array", action="store_true", help="Disable pseudo-array handling."
    )
    parser.add_argument("--no-format", action="store_true", help="Disable FormatComparator.")
    parser.add_argument("--no-enum", action="store_true", help="Disable EnumComparator.")
    parser.add_argument("--no-required", action="store_true", help="Disable RequiredComparator.")
    parser.add_argument("--no-empty", action="store_true", help="Disable EmptyComparator.")
    parser.add_argument(
        "--no-schema-version",
        action="store_true",
        help="Disable SchemaVersionComparator.",
    )
    parser.add_argument(
        "--no-delete-element", action="store_true", help="Disable DeleteElement comparators."
    )
    parser.add_argument(
        "--extract-refs",
        action="store_true",
        help="Run reference-extraction postprocessing and emit shared $defs/$ref blocks.",
    )
    parser.add_argument(
        "--refs-similarity-threshold",
        type=float,
        default=0.85,
        help="Similarity threshold for grouping shared-reference candidates (default: 0.85).",
    )
    parser.add_argument(
        "--refs-min-total-keys",
        type=int,
        default=3,
        help="Minimum total number of structural keys before extraction is applied (default: 3).",
    )
    parser.add_argument(
        "--refs-min-occurrences",
        type=int,
        default=2,
        help="Minimum number of similar occurrences required for extraction (default: 2).",
    )
    parser.add_argument(
        "--refs-defs-key",
        default="$defs",
        help="Definition container key used for extracted shared refs (default: $defs).",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    raw_args = sys.argv[1:] if argv is None else argv

    # If no arguments, show help and exit
    if not raw_args:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args(raw_args)

    # Collect input data
    datas = []
    if not args.inputs:
        # This case shouldn't happen due to the check above, but for safety
        try:
            data = json.load(sys.stdin)
            datas.append(data)
        except json.JSONDecodeError as e:
            console.print(f"[red]Error reading JSON from stdin: {e}[/red]")
            sys.exit(1)
    else:
        for input_path in args.inputs:
            if input_path == "-":
                try:
                    data = json.load(sys.stdin)
                    datas.append(data)
                except json.JSONDecodeError as e:
                    console.print(f"[red]Error reading JSON from stdin: {e}[/red]")
                    sys.exit(1)
            else:
                try:
                    with open(input_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    datas.append(data)
                except FileNotFoundError:
                    console.print(f"[red]File not found: {input_path}[/red]")
                    sys.exit(1)
                except json.JSONDecodeError as e:
                    console.print(f"[red]Invalid JSON in file {input_path}: {e}[/red]")
                    sys.exit(1)

    if not datas:
        console.print("[red]No valid JSON provided.[/red]")
        sys.exit(1)

    # Converter setup
    pseudo_handler = None if args.no_pseudo_array else PseudoArrayHandler()
    conv = Converter(pseudo_handler=pseudo_handler, base_of=args.base_of)

    for data in datas:
        conv.add_json(data)

    # Register comparators conditionally
    if not args.no_format:
        conv.register(FormatComparator())
    if not args.no_enum:
        conv.register(EnumComparator())
    if not args.no_schema_version:
        conv.register(SchemaVersionComparator())
    if not args.no_required:
        conv.register(RequiredComparator())
    if not args.no_empty:
        conv.register(EmptyComparator())
    if not args.no_delete_element:
        conv.register(DeleteElement())
        conv.register(DeleteElement("isPseudoArray"))

    # Generate schema
    start_time = time.time()
    try:
        result = conv.run()
    except Exception as e:
        console.print(f"[red]Error generating schema: {e}[/red]")
        sys.exit(1)

    if args.extract_refs:
        try:
            refs_config = SchemaReferenceExtractionConfig(
                similarity_threshold=args.refs_similarity_threshold,
                min_total_keys=args.refs_min_total_keys,
                min_occurrences=args.refs_min_occurrences,
                defs_key=args.refs_defs_key,
                merge_base_of=args.base_of,
                merge_pseudo_handler=pseudo_handler,
            )
            result = SchemaReferencePostprocessor.process(result, refs_config)
        except Exception as e:
            console.print(f"[red]Error extracting schema references: {e}[/red]")
            sys.exit(1)

    elapsed = round(time.time() - start_time, 4)

    # Output result
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            console.print(f"[green]Schema successfully written to {args.output}[/green]")
        except Exception as e:
            console.print(f"[red]Error writing file {args.output}: {e}[/red]")
            sys.exit(1)
    else:
        console.print(result)

    # Execution info
    instances_word = "instance" if len(datas) == 1 else "instances"
    console.print(f"Generated from {len(datas)} JSON {instances_word}.")
    if args.extract_refs:
        defs = result.get(args.refs_defs_key, {})
        defs_count = len(defs) if isinstance(defs, dict) else 0
        console.print(f"Extracted {defs_count} shared definitions into {args.refs_defs_key}.")
    console.print(f"Elapsed time: {elapsed} sec.")


if __name__ == "__main__":
    main()
