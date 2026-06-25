"""Create a balanced raw recipe sample from the command line."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

from recipeprep.config import get_config
from recipeprep.data import get_long_short_recipe_dataset


def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description="Create a balanced long/short sample from raw recipe dataset."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Raw recipe JSON file. Default: recipes_raw/recipes_raw_processed.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Sample output JSON file. Default: datasets/recipe_dataset_init_200.json.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=200,
        help="Number of recipes to sample. Default: 200.",
    )
    parser.add_argument(
        "--long-recipe-percent",
        type=float,
        default=0.2,
        help="Fraction of sampled recipes that should be long recipes. Default: 0.2.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:

    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    config = get_config()
    config.ensure_output_directories()

    input_path = (
        config.raw_recipes_dir / "recipes_raw_processed.json"
        if args.input is None
        else config.resolve_path(args.input)
    )
    output_path = (
        config.datasets_dir / f"recipe_dataset_init_{args.sample_size}.json"
        if args.output is None
        else config.resolve_path(args.output)
    )
    
    
    """
    Sampling rule:
    - skip recipes without valid instruction text;
    - skip recipes already present in datasets/Processed_Recipes
    - long_recipe_percent is used to keep the sampled output balanced
    """
    get_long_short_recipe_dataset(
        recipe_filename=input_path,
        sample_size=args.sample_size,
        output_file_name=output_path,
        long_recipe_percnt=args.long_recipe_percent,
    )
    print(f"Saved sampled recipes to {output_path}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
