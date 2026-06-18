"""Build tuning and test ingredient lists for recipe evaluation."""

from __future__ import annotations

import csv
import logging
import math
import random
from itertools import combinations
from pathlib import Path
from typing import TypedDict

import pandas as pd  # type: ignore[import-untyped]

LOGGER = logging.getLogger(__name__)


class IngredientExample(TypedDict):
    """One generated evaluation example."""

    category: str
    ingredients: list[str]


def generate_mix_examples(
    categorized_data: dict[str, list[str] | list[list[str]]],
    num_examples: int,
    ingredient_range: tuple[int, int],
) -> list[IngredientExample]:
    """Create examples from mixed and single ingredient categories."""
    examples: list[IngredientExample] = []
    mixed_examples = categorized_data.get("Mixed", [])

    for _ in range(num_examples // 5):
        if mixed_examples:
            selected = random.choice(mixed_examples)
            if isinstance(selected, list):
                ingredients = selected[: random.randint(*ingredient_range)]
                examples.append({"category": "Mixed", "ingredients": ingredients})

    single_categories = [name for name in categorized_data if name != "Mixed"]
    for _ in range(num_examples - len(examples)):
        category = random.choice(single_categories)
        category_ingredients = categorized_data[category]
        if (
            category_ingredients
            and isinstance(category_ingredients[0], str)
            and len(category_ingredients) >= ingredient_range[0]
        ):
            string_ingredients = [
                item for item in category_ingredients if isinstance(item, str)
            ]
            examples.append(
                {
                    "category": category,
                    "ingredients": random.sample(
                        string_ingredients,
                        random.randint(*ingredient_range),
                    ),
                }
            )
    return examples


def create_examples(
    categorized_data: dict[str, list[str] | list[list[str]]],
    mid_percnt: float,
    total_size: int,
) -> tuple[list[IngredientExample], list[IngredientExample], list[IngredientExample]]:
    """Create short, medium, and long ingredient examples."""
    mid_num = round(total_size * mid_percnt)
    short_num = (total_size - mid_num) // 2
    long_num = total_size - mid_num - short_num
    LOGGER.info(
        "Creating %s short, %s medium, and %s long examples.",
        short_num,
        mid_num,
        long_num,
    )
    return (
        generate_mix_examples(categorized_data, short_num, (1, 3)),
        generate_mix_examples(categorized_data, mid_num, (4, 7)),
        generate_mix_examples(categorized_data, long_num, (8, 12)),
    )


def split_with_mixed(
    samples: list[IngredientExample],
    tune_num: int,
) -> tuple[list[IngredientExample], list[IngredientExample]]:
    """Split examples while keeping mixed examples in the tuning set."""
    mixed_samples = [sample for sample in samples if sample["category"] == "Mixed"]
    non_mixed_samples = [sample for sample in samples if sample["category"] != "Mixed"]
    num_mixed_tune = min(len(mixed_samples), tune_num // 2)
    num_non_mixed_tune = tune_num - num_mixed_tune
    tuning = (
        mixed_samples[:num_mixed_tune] + non_mixed_samples[:num_non_mixed_tune]
    )
    testing = (
        mixed_samples[num_mixed_tune:] + non_mixed_samples[num_non_mixed_tune:]
    )
    return tuning, testing


def generate_datasets(
    file_path: str | Path,
    mid_percnt: float,
    total_size: int,
    tune_size: float,
) -> tuple[list[IngredientExample], list[IngredientExample]]:
    """Build sorted tuning and test examples from an ingredient CSV."""
    data = pd.read_csv(file_path)
    categories = data["Category"].unique().tolist()
    categorized_data: dict[str, list[str] | list[list[str]]] = {
        category: [] for category in categories
    }
    categorized_data["Mixed"] = []

    for _, row in data.iterrows():
        category = row["Category"]
        category_values = categorized_data[category]
        if isinstance(category_values, list):
            category_values.append(row["Food"])

    mixed_values = categorized_data["Mixed"]
    for category_count in range(2, len(categories) + 1):
        for category_group in combinations(categories, category_count):
            combined: list[str] = []
            for category in category_group:
                values = categorized_data[category]
                string_values = [item for item in values if isinstance(item, str)]
                if string_values:
                    combined.append(random.choice(string_values))
            if combined:
                mixed_values.append(combined)  # type: ignore[arg-type]

    short, medium, long = create_examples(
        categorized_data,
        mid_percnt,
        total_size,
    )
    tuning_parts: list[list[IngredientExample]] = []
    testing_parts: list[list[IngredientExample]] = []
    for samples in (short, medium, long):
        tune_count = math.floor(len(samples) * tune_size)
        tuning, testing = split_with_mixed(samples, tune_count)
        tuning_parts.append(tuning)
        testing_parts.append(testing)

    tuning_dataset = sorted(
        [item for part in tuning_parts for item in part],
        key=lambda item: len(item["ingredients"]),
    )
    testing_dataset = sorted(
        [item for part in testing_parts for item in part],
        key=lambda item: len(item["ingredients"]),
    )
    LOGGER.info(
        "Created %s tuning examples and %s test examples.",
        len(tuning_dataset),
        len(testing_dataset),
    )
    return tuning_dataset, testing_dataset


def save_to_csv(data: list[IngredientExample], file_path: str | Path) -> None:
    """Save evaluation examples as category and ingredient CSV rows."""
    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["Category", "Ingredients"])
        writer.writeheader()
        for entry in data:
            writer.writerow(
                {
                    "Category": entry["category"],
                    "Ingredients": ", ".join(entry["ingredients"]),
                }
            )
