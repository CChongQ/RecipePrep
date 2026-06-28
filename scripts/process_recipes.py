"""Convert raw recipes to structured processed recipe batches."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from openai import OpenAI

from recipeprep.config import get_config
from recipeprep.data import get_processed_recipe_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Use the configured chat model to structure raw recipe records."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Sampled raw recipe JSON. Default: datasets/recipe_dataset_init_200.json.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for processed recipe batches. Default: configured processed recipes dir.",
    )
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size. Default: 50.")
    parser.add_argument("--temperature", type=float, default=0.7, help="Model temperature.")
    parser.add_argument("--top-p", type=float, default=1.0, help="Model top_p value.")
    parser.add_argument("--model", default=None, help="Optional chat model override.")
    return parser


def _load_raw_recipes(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
        
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return data


def main(argv: Sequence[str] | None = None) -> int:

    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    config = get_config()
    config.ensure_output_directories()
    input_path = (
        config.datasets_dir / "recipe_dataset_200.json"
        if args.input is None
        else config.resolve_path(args.input)
    )
    output_dir = None if args.output_dir is None else config.resolve_path(args.output_dir)
    model_name = args.model or config.openai.chat_model
    print(f"Using model: {model_name}")
    
    """
    Output batches contains:
    - recipe metadata, original text
    - structured ingredients, pure ingredient names, step-by-step instructions
    - cooking time, tools...
    """
    batch_count = get_processed_recipe_dataset(
        client=OpenAI(),
        temp=args.temperature,
        topp=args.top_p,
        recipe_dataset=_load_raw_recipes(input_path),
        batch_size=args.batch_size,
        output_dir=output_dir,
        model=model_name,
    )
    print(f"Created {batch_count} processed recipe batches")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

