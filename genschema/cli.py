import argparse
import json
import sys
import time

from rich.console import Console

from . import Converter, PseudoArrayHandler
from .comparators import (
    DeleteElement,
    EmptyComparator,
    FormatComparator,
    RequiredComparator,
)

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate JSON Schema from JSON input using genschema.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  genschema input.json -o schema.json
  genschema input1.json input2.json --base-of oneOf
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
    parser.add_argument("--no-required", action="store_true", help="Disable RequiredComparator.")
    parser.add_argument("--no-empty", action="store_true", help="Disable EmptyComparator.")
    parser.add_argument(
        "--no-delete-element", action="store_true", help="Disable DeleteElement comparators."
    )

    # If no arguments, show help and exit
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

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
    console.print(f"Elapsed time: {elapsed} sec.")


if __name__ == "__main__":
    main()
