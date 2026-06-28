"""Collect unique ingredient names from processed recipe batches."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Sequence
from pathlib import Path

from recipeprep.config import get_config
from recipeprep.data import get_ingre_list_from_dataset


def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description="Collect unique processed ingredients into a JSON list."
    )
    parser.add_argument(
        "--pattern",
        default="processed_recipes_*.json",
        help="Glob pattern under the processed recipes directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON list. Default: datasets/ingredient_list.json.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run ingredient collection."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    config = get_config()
    config.ensure_output_directories()
    ingredients: set[str] = set()

    # Read each processed recipe batch that matches the requested pattern
    for path in config.processed_recipes_dir.glob(args.pattern):
        ingredients.update(get_ingre_list_from_dataset(path))

    # Sort the set so repeated runs produce stable JSON output
    ingredient_list = sorted(ingredients)
    
    # write the ingredient list to output file
    output_path = (
        config.datasets_dir / "ingredient_list.json"
        if args.output is None
        else config.resolve_path(args.output)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(ingredient_list, file, indent=2)

    print(f"Saved {len(ingredient_list)} unique ingredients to {output_path}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
