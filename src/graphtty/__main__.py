"""CLI entry-point: ``uv run graphtty <file.json>``."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .renderer import RenderOptions, render
from .themes import get_theme, list_themes
from .types import AsciiGraph


def _map_legacy_metadata(node_data: dict[str, Any]) -> dict[str, Any]:
    """Map legacy ``metadata`` fields to ``description`` for display.

    Handles the UiPath runtime graph JSON format where metadata contains
    ``model_name`` and ``tool_names`` fields.
    """
    if not isinstance(node_data, dict):
        return node_data

    meta = node_data.get("metadata")
    if not isinstance(meta, dict) or node_data.get("description"):
        return node_data

    node_type = node_data.get("type", "")

    if node_type == "model" and "model_name" in meta:
        node_data["description"] = str(meta["model_name"])
    elif node_type == "tool" and "tool_names" in meta:
        names = meta["tool_names"]
        if isinstance(names, list) and names:
            node_data["description"] = ", ".join(str(n) for n in names)
        elif isinstance(names, str):
            node_data["description"] = names

    return node_data


def _preprocess_nodes(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively preprocess node dicts in a graph, mapping legacy metadata."""
    if "nodes" in data and isinstance(data["nodes"], list):
        for node_data in data["nodes"]:
            if isinstance(node_data, dict):
                _map_legacy_metadata(node_data)
                sub = node_data.get("subgraph")
                if isinstance(sub, dict):
                    _preprocess_nodes(sub)
    return data


def main(argv: list[str] | None = None) -> None:
    """Parse command-line arguments and render the graph."""
    parser = argparse.ArgumentParser(
        prog="graphtty",
        description="Render a directed graph JSON file as ASCII/Unicode art.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Path to a graph JSON file",
    )
    parser.add_argument(
        "-t",
        "--theme",
        default="default",
        help="Color theme (use --list-themes to see options)",
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="Use plain ASCII instead of Unicode box-drawing characters",
    )
    parser.add_argument(
        "--no-types",
        action="store_true",
        help="Hide node type labels",
    )
    parser.add_argument(
        "--list-themes",
        action="store_true",
        help="List available themes and exit",
    )

    args = parser.parse_args(argv)

    if args.list_themes:
        for name in list_themes():
            print(name)
        return

    if args.file is None:
        parser.error("the following arguments are required: file")

    # Ensure UTF-8 output on Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        theme = get_theme(args.theme)
    except ValueError as exc:
        parser.error(str(exc))

    try:
        with open(args.file, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error reading {args.file}: {exc}", file=sys.stderr)
        sys.exit(1)

    _preprocess_nodes(data)
    graph = AsciiGraph(**data)

    options = RenderOptions(
        use_unicode=not args.ascii,
        show_types=not args.no_types,
        theme=theme,
    )

    print(render(graph, options))


if __name__ == "__main__":
    main()
