"""Filter scored recipe files from the command line."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

from recipeprep.data.recipe_filtering import filter_recipe_files


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Combine one or more scored recipe JSON files and keep recipes "
            "that meet a minimum health score."
        )
    )
    parser.add_argument(
        "--input",
        nargs="+",
        required=True,
        type=Path,
        help="One or more scored recipe JSON files.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path for the filtered JSON output.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=3,
        help="Minimum total health score to keep. Default: 3.",
    )
    parser.add_argument(
        "--score-field",
        default="total_health_score",
        help="Recipe field containing the health score.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail instead of skipping recipes with missing or invalid scores.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the recipe filtering command."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    result = filter_recipe_files(
        args.input,
        args.output,
        args.min_score,
        score_field=args.score_field,
        strict=args.strict,
    )
    print(
        f"Kept {result.kept_count} of {result.total_count} recipes "
        f"and skipped {result.skipped_invalid_count} invalid records."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

