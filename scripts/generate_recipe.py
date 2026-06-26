"""Generate a recipe from command-line ingredients, tools, and time."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Sequence

from openai import OpenAI

from recipeprep.config import get_config
from recipeprep.generation import RecipeGenerator
from recipeprep.retrieval import build_retrievers


def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description="Generate a recipe using the RAG pipeline."
    )
    parser.add_argument(
        "--recipes",
        required=True,
        type=Path,
        help="Filtered recipe JSON file.",
    )
    parser.add_argument(
        "--ingredients",
        nargs="+",
        required=True,
        help="Ingredients to use.",
    )
    parser.add_argument(
        "--tools",
        nargs="+",
        required=True,
        help="Available cooking tools.",
    )
    parser.add_argument(
        "--time",
        required=True,
        type=int,
        help="Available cooking time in minutes.",
    )
    parser.add_argument(
        "--validated-json",
        action="store_true",
        help="Return validated recipe JSON instead of plain generated text.",
    )
    parser.add_argument(
        "--no-example",
        action="store_true",
        help="Disable example recipe retrieval in text generation.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run recipe generation."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    config = get_config()
    recipes_path = config.resolve_path(args.recipes)
    print(f"Using model: {config.openai.chat_model}")
    print(f"Using embedding model for retrievers: {config.openai.embedding_model}")

    # Load the nutrient and recipe retrievers built during pipeline setup
    retrievers = build_retrievers(recipes_path, config=config)

    generator = RecipeGenerator(
        client=OpenAI(),
        nutrient_retriever=retrievers.nutrient,
        recipe_retriever=retrievers.recipes,
        recipes_path=recipes_path,
    )

    # Validated mode parses the model JSON into the GeneratedRecipe schema
    if args.validated_json:
        recipe = generator.generate(
            ingredients=args.ingredients,
            tools=args.tools,
            time=args.time,
        )
        print(json.dumps(recipe.model_dump(), indent=2))
    else:
        # Text mode prints the raw model JSON string for quick CLI testing
        print(
            generator.generate_text(
                ingredients=args.ingredients,
                tools=args.tools,
                time=args.time,
                provide_example=not args.no_example,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

