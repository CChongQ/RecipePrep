"""Sample, filter, combine, and inspect recipe datasets."""

from __future__ import annotations

import json
import logging
import random
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd  # type: ignore[import-untyped]

from recipeprep.config import AppConfig, get_config
from recipeprep.retrieval.preprocessing import preprocess_text

LOGGER = logging.getLogger(__name__)


def _processed_recipe_files(config: AppConfig) -> list[Path]:
    """Return processed recipe JSON files that should not be sampled again."""
    
    if not config.processed_recipes_dir.is_dir():
        return []
    return sorted(config.processed_recipes_dir.glob("*.json"))


def get_testing_dataset(
    in_filename: str | Path,
    samp_size: int,
    long_percnt: float = 0,
    *,
    config: AppConfig | None = None,
) -> tuple[list[tuple[str, dict[str, Any]]], list[tuple[str, dict[str, Any]]] | None]:
    """Sample raw recipes, optionally with a fixed % of long recipes."""
    
    settings = config or get_config()
    existing_ids: set[str] = set()

    # Collect recipe IDs from already processed datasets
    for file_path in _processed_recipe_files(settings):
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        existing_ids.update(recipe["recipe_id"] for recipe in data)

    # Load the raw recipe dataset
    with Path(in_filename).open("r", encoding="utf-8") as file:
        recipe_data: dict[str, dict[str, Any]] = json.load(file)

    filtered_recipes: dict[str, dict[str, Any]] = {}
    for recipe_id, recipe in recipe_data.items():
        # Skip recipes that have already been processed.
        if recipe_id in existing_ids:
            continue

        instructions = recipe.get("instructions")
        # recipe must have an 'instructions' key with a non-empty string value.
        if not isinstance(instructions, str) or not instructions.strip():
            continue

        filtered_recipes[recipe_id] = recipe
    recipe_data = filtered_recipes

    # When the dataset need to contain long_percnt of long recipes 
    if long_percnt != 0:
        long_recipes: dict[str, dict[str, Any]] = {}
        short_recipes: dict[str, dict[str, Any]] = {}

        # Categorize recipes as long or short based on instruction length.
        for recipe_id, recipe in recipe_data.items():
            instruction_length = len(recipe["instructions"])

            if instruction_length >= settings.pipeline.long_recipe_min_characters:
                long_recipes[recipe_id] = recipe
            else:
                short_recipes[recipe_id] = recipe

        # Calc how many long recipes and short recipes we want to sample.
        num_sample_long = int(samp_size * long_percnt)
        num_sample_short = samp_size - num_sample_long

        if num_sample_long == 0:
            raise ValueError(
                "The long-recipe sample is empty; increase the sample size or percentage."
            )

        LOGGER.info(
            "Sampling %s long recipes and %s short recipes.",
            num_sample_long,
            num_sample_short,
        )

        # Randomly sample long recipes.
        sampled_long_items = random.sample(
            list(long_recipes.items()),
            min(num_sample_long, len(long_recipes)),
        )

        # Randomly sample short recipes.
        sampled_short_items = random.sample(
            list(short_recipes.items()),
            min(num_sample_short, len(short_recipes)),
        )

        return sampled_short_items, sampled_long_items

    # If no percentage for long recipes is given, return a random sample of the specified size.
    return random.sample(list(recipe_data.items()), samp_size), None


def filter_recipe_ingre_frequency(
    recipes_list: Sequence[Mapping[str, Any]],
    min_freq: int = 3,
) -> list[Mapping[str, Any]]:
    """Keep recipes whose ingredients all meet the minimum frequency."""
    ingredient_counts: Counter[str] = Counter()
    for recipe in recipes_list:
        ingredient_counts.update(recipe.get("pure_ingredients", []))

    valid_ingredients = {
        ingredient
        for ingredient, count in ingredient_counts.items()
        if count >= min_freq
    }
    filtered_out = set(ingredient_counts) - valid_ingredients
    if filtered_out:
        LOGGER.info("Filtered out %s low-frequency ingredients.", len(filtered_out))

    return [
        recipe
        for recipe in recipes_list
        if all(
            ingredient in valid_ingredients
            for ingredient in recipe.get("pure_ingredients", [])
        )
    ]


def normalize_word(word: str) -> str:
    """Lowercase a word and remove a simple plural ending."""
    word = word.lower().strip()
    if word.endswith("es"):
        return word[:-2]
    if word.endswith("s"):
        return word[:-1]
    return word


def filter_raw_recipe_on_ingredient_list(
    raw_file_name: str | Path,
    key_word_filename: str | Path,
    output_filename: str | Path,
) -> None:
    """Keep raw recipes whose ingredients match the approved ingredient list."""
    keyword_data = pd.read_csv(key_word_filename)
    keywords = [normalize_word(word) for word in keyword_data["Food"].dropna().tolist()]

    with Path(raw_file_name).open("r", encoding="utf-8") as file:
        recipe_data: dict[str, dict[str, Any]] = json.load(file)
    LOGGER.info("Recipe count before filtering: %s", len(recipe_data))

    filtered_recipes: dict[str, dict[str, Any]] = {}
    for recipe_id, recipe in recipe_data.items():
        ingredients = recipe.get("ingredients", [])
        instructions = recipe.get("instructions")
        if not ingredients or not instructions:
            continue
        if all(
            any(keyword in normalize_word(ingredient) for keyword in keywords)
            for ingredient in ingredients
        ):
            filtered_recipes[recipe_id] = recipe

    LOGGER.info("Recipe count after filtering: %s", len(filtered_recipes))
    save_json_file(filtered_recipes, output_filename)


def get_pure_testing_ingre_list(
    data: pd.DataFrame,
    category_col: str,
    frac: float = 0.2,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split each ingredient category into test and remaining rows."""
    sampled_testing_data = data.groupby(category_col, group_keys=False).apply(
        lambda group: group.sample(frac=frac, random_state=random_state)
    )
    remaining_data = data.loc[~data.index.isin(sampled_testing_data.index)]
    return sampled_testing_data, remaining_data


def get_average_instruction_length(recipe_filename: str | Path) -> float:
    """Return the average instruction length in characters."""
    with Path(recipe_filename).open("r", encoding="utf-8") as file:
        recipe_data: dict[str, dict[str, Any]] = json.load(file)
    lengths = [len(recipe["instructions"]) for recipe in recipe_data.values()]
    return sum(lengths) / len(lengths) if lengths else 0.0


def save_json_file(in_data: Any, output_file_name: str | Path) -> None:
    """Save data as readable JSON."""
    output_path = Path(output_file_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(in_data, file, indent=4)


def get_long_short_recipe_dataset(
    recipe_filename: str | Path,
    sample_size: int,
    output_file_name: str | Path,
    long_recipe_percnt: float = 0.2,
) -> None:
    """Save a sample containing both short and long recipes."""
    short_recipes, long_recipes = get_testing_dataset(
        recipe_filename,
        sample_size,
        long_percnt=long_recipe_percnt,
    )
    sampled_data = dict(short_recipes + (long_recipes or []))
    save_json_file(sampled_data, output_file_name)
    LOGGER.info("Saved %s sampled recipes to %s", len(sampled_data), output_file_name)


def get_rand_recipe_dataset(
    recipe_filename: str | Path,
    sample_size: int,
    output_file_name: str | Path,
    long_recipe_percnt: float = 0,
) -> None:
    """Save a random recipe sample."""
    all_recipes, _ = get_testing_dataset(
        recipe_filename,
        sample_size,
        long_percnt=long_recipe_percnt,
    )
    save_json_file(dict(all_recipes), output_file_name)
    LOGGER.info("Saved %s sampled recipes to %s", len(all_recipes), output_file_name)


def get_ingre_list_from_dataset(file_path: str | Path) -> list[str]:
    """Return the sorted unique ingredient names in a processed dataset."""
    with Path(file_path).open("r", encoding="utf-8") as file:
        processed_recipes: list[dict[str, Any]] = json.load(file)

    ingredients = {
        ingredient
        for recipe in processed_recipes
        for ingredient in recipe.get("pure_ingredients", [])
    }
    return [preprocess_text(ingredient) for ingredient in sorted(ingredients)]


def combine_two_json(
    file_1: str | Path,
    file_2: str | Path,
    out_filename: str | Path,
) -> None:
    """Merge two JSON dictionaries and save the result."""
    with Path(file_1).open("r", encoding="utf-8") as file:
        data_1 = json.load(file)
    with Path(file_2).open("r", encoding="utf-8") as file:
        data_2 = json.load(file)
    save_json_file({**data_1, **data_2}, out_filename)
    LOGGER.info("Combined JSON saved to %s", out_filename)
