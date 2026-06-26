"""Evaluate one generated recipe from the command line."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Sequence

from recipeprep.config import get_config
from recipeprep.evaluation import evaluate_recipe
from recipeprep.retrieval import build_nutrient_retriever


def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description="Run health, relevance, and consistency checks for one recipe."
    )
    parser.add_argument(
        "--recipe",
        required=True,
        type=Path,
        help="Generated recipe JSON file.",
    )
    parser.add_argument(
        "--ingredients",
        nargs="+",
        required=True,
        help="User-provided ingredients used for generation.",
    )
    parser.add_argument(
        "--tools",
        nargs="+",
        required=True,
        help="User-provided cooking tools used for generation.",
    )
    parser.add_argument(
        "--focused-tools",
        nargs="*",
        default=None,
        help="Tools that must appear in the generated recipe. Default: same as --tools.",
    )
    parser.add_argument(
        "--time",
        required=True,
        type=float,
        help="Target cooking time in minutes used for generation.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to save the evaluation JSON result.",
    )
    return parser


def _load_recipe(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Expected one generated recipe object: {path}")
    return data


def main(argv: Sequence[str] | None = None) -> int:
    """Run evaluation for one generated recipe."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    config = get_config()
    recipe_path = config.resolve_path(args.recipe)
    output_path = None if args.output is None else config.resolve_path(args.output)

    # Reuse the saved nutrient retriever to evaluate health and ingredient overlap.
    nutrient_retriever = build_nutrient_retriever(config=config)

    # focused_tools defaults to all user-provided tools when no stricter subset is given.
    focused_tools = args.focused_tools if args.focused_tools is not None else args.tools
    result = evaluate_recipe(
        _load_recipe(recipe_path),
        nutrient_retriever=nutrient_retriever,
        focused_tools=focused_tools,
        input_tools=args.tools,
        input_time=args.time,
        input_ingredients=args.ingredients,
    ).model_dump()

    output_text = json.dumps(result, indent=2)
    if output_path is None:
        print(output_text)
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_text, encoding="utf-8")
        print(f"Saved evaluation result to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
