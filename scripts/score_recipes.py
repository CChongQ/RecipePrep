"""Score processed recipes using the nutrient retriever."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Sequence

from recipeprep.config import get_config
from recipeprep.nutrition import evaluate_recipe_health
from recipeprep.retrieval import build_nutrient_retriever


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(description="Add nutrition health scores to recipes.")
    parser.add_argument("--input", required=True, type=Path, help="Processed recipe JSON file.")
    parser.add_argument("--output", required=True, type=Path, help="Scored recipe JSON output.")
    parser.add_argument(
        "--rebuild-retriever",
        action="store_true",
        help="Rebuild the nutrient vector store before scoring.",
    )
    return parser


def _load_recipes(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON recipe list: {path}")
    return data


def main(argv: Sequence[str] | None = None) -> int:
    """Run scoring on recipes"""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    config = get_config()
    retriever = build_nutrient_retriever(rebuild=args.rebuild_retriever, config=config)
    input_path = config.resolve_path(args.input)
    output_path = config.resolve_path(args.output)

    recipes = _load_recipes(input_path)
    for recipe in recipes:
        result = evaluate_recipe_health(retriever, recipe)
        recipe["total_health_score"] = result.total_health_score
        recipe["summary_of_points"] = result.summary_of_points
        recipe["nutrient_totals"] = result.nutrient_totals
        recipe["nutrition_warnings"] = result.warnings

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(recipes, file, indent=2)
    print(f"Saved {len(recipes)} scored recipes to {output_path}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
