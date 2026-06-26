"""Build or load the persistent Chroma retrievers."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

from recipeprep.config import get_config
from recipeprep.retrieval import build_retrievers


def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description="Build the nutrient and recipe Chroma vector stores."
    )
    parser.add_argument(
        "--recipes",
        required=True,
        type=Path,
        help="Filtered/scored recipe JSON file used for the recipe retriever.",
    )
    parser.add_argument(
        "--nutrient-map",
        type=Path,
        default=None,
        help="Ingredient nutrient map. Default: configured nutrient map path.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild stores even when saved stores already exist.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run retriever creation."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    config = get_config()
    config.ensure_output_directories()
    nutrient_map = None if args.nutrient_map is None else config.resolve_path(args.nutrient_map)
    
    build_retrievers(
        config.resolve_path(args.recipes),
        nutrient_map,
        rebuild=args.rebuild,
        config=config,
    )
    print(f"Nutrient store: {config.nutrient_vectorstore_dir}")
    print(f"Recipe store: {config.recipe_vectorstore_dir}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
