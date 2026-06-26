"""Match ingredient names to Canadian Nutrient File food codes."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Sequence

from openai import OpenAI

from recipeprep.config import get_config
from recipeprep.retrieval import (
    IngredientMatcher,
    get_food_code_for_ingredients,
    get_normalized_foodCode_dataset,
    get_regular_foodCode_dataset,
    load_FAISS_Index,
)


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Use exact matching, embeddings, and FAISS to map ingredients "
            "to CNF food codes."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Ingredient JSON list. Default: datasets/ingredient_list.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON mapping. Default: datasets/ingredient_food_code_matches.json.",
    )
    parser.add_argument("--top-k", type=int, default=30, help="FAISS candidates per ingredient.")
    parser.add_argument("--model", default=None, help="Optional embedding model override.")
    return parser


def _load_ingredients(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON ingredient list: {path}")
    return [str(item) for item in data]


def main(argv: Sequence[str] | None = None) -> int:
    """Run ingredient matching.
    
    Core Logic: Match each ingredient by exact text first, then embedding search if needed.
    """
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    config = get_config()
    input_path = (
        config.datasets_dir / "ingredient_list.json"
        if args.input is None
        else config.resolve_path(args.input)
    )
    output_path = (
        config.datasets_dir / "ingredient_food_code_matches.json"
        if args.output is None
        else config.resolve_path(args.output)
    )
    model_name = args.model or config.openai.embedding_model
    print(f"Using embedding model for unmatched ingredients: {model_name}")

    # Load the normalized/original CNF descriptions and saved FAISS index.
    normalized_descriptions, food_codes = get_normalized_foodCode_dataset(config=config)
    original_descriptions, _ = get_regular_foodCode_dataset(config=config)
    
    # Weak matches are filtered out
    # matches against the main CNF description are preferred when possible.
    matcher = IngredientMatcher(
        client=OpenAI(),
        index=load_FAISS_Index(config=config),
        food_descriptions=normalized_descriptions,
        food_codes=food_codes,
        food_descriptions_ori=original_descriptions,
        top_k=args.top_k,
        embedding_model=model_name,
    )
   
    matches = get_food_code_for_ingredients(_load_ingredients(input_path), matcher)

    # Save matches keyed by the original ingredient name.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(matches, file, indent=2)

    print(f"Saved {len(matches)} ingredient matches to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

