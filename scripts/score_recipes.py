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
    parser.add_argument("--input", type=Path, help="Processed recipe JSON file.")
    parser.add_argument("--output", type=Path, help="Scored recipe JSON output.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help=(
            "Directory of processed recipe files. "
            "Default: configured processed recipes directory."
        ),
    )
    parser.add_argument(
        "--pattern",
        default=None,
        help="Glob pattern for batch scoring, for example processed_recipes_*.json.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for batch scored outputs. Default: datasets/scored_recipes.",
    )
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


def _score_file(
    input_path: Path,
    output_path: Path,
    retriever: Any,
) -> int:
    """Score one processed recipe file and save the result."""

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
    return len(recipes)


def main(argv: Sequence[str] | None = None) -> int:
    """Run scoring on one file or a batch of processed recipe files."""

    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    config = get_config()
    retriever = build_nutrient_retriever(rebuild=args.rebuild_retriever, config=config)

    if args.pattern:
        input_dir = (
            config.processed_recipes_dir
            if args.input_dir is None
            else config.resolve_path(args.input_dir)
        )
        output_dir = (
            config.datasets_dir / "scored_recipes"
            if args.output_dir is None
            else config.resolve_path(args.output_dir)
        )
        input_paths = sorted(input_dir.glob(args.pattern))
        if not input_paths:
            raise FileNotFoundError(f"No files matched {args.pattern!r} in {input_dir}")

        total_recipes = 0
        for input_path in input_paths:
            output_path = output_dir / input_path.name.replace(
                "processed_recipes", "scored_recipes", 1
            )
            total_recipes += _score_file(input_path, output_path, retriever)
        print(f"Scored {total_recipes} recipes from {len(input_paths)} files.")
        return 0

    if args.input is None or args.output is None:
        raise ValueError("Use --input and --output, or use --pattern for batch scoring.")

    _score_file(
        config.resolve_path(args.input),
        config.resolve_path(args.output),
        retriever,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())