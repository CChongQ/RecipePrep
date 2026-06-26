"""Filter scored recipe files from the command line."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

from recipeprep.config import get_config
from recipeprep.data.recipe_filtering import filter_recipe_files


def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description=(
            "Combine scored recipe JSON files from a folder and keep recipes "
            "that meet a minimum health score."
        )
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help="Folder containing scored recipe files. Default: datasets/scored_recipes.",
    )
    parser.add_argument(
        "--pattern",
        default="scored_recipes_*.json",
        help="Glob pattern for scored files. Default: scored_recipes_*.json.",
    )
    parser.add_argument(
        "--input",
        nargs="+",
        type=Path,
        default=None,
        help="Optional explicit scored recipe files. Overrides --input-dir/--pattern.",
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

    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    config = get_config()
    if args.input:
        input_paths = [config.resolve_path(path) for path in args.input]
    else:
        input_dir = (
            config.datasets_dir / "scored_recipes"
            if args.input_dir is None
            else config.resolve_path(args.input_dir)
        )
        input_paths = sorted(input_dir.glob(args.pattern))
        if not input_paths:
            raise FileNotFoundError(f"No files matched {args.pattern!r} in {input_dir}")

    result = filter_recipe_files(
        input_paths,
        config.resolve_path(args.output),
        args.min_score,
        score_field=args.score_field,
        strict=args.strict,
    )
    print(
        f"Kept {result.kept_count} of {result.total_count} recipes "
        f"from {len(input_paths)} files and skipped "
        f"{result.skipped_invalid_count} invalid records."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
