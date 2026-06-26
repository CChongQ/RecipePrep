"""Filter and combine scored recipe JSON files."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class FilterResult:
    """Summary of one filtering run."""

    recipes: list[dict[str, Any]]
    total_count: int
    kept_count: int
    skipped_invalid_count: int


def load_recipe_file(file_path: str | Path) -> list[dict[str, Any]]:
    """Load a recipe JSON file and check that it contains a list."""
    path = Path(file_path)
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"Recipe file must contain a JSON list: {path}")
    if not all(isinstance(recipe, dict) for recipe in data):
        raise ValueError(f"Every recipe must be a JSON object: {path}")
    return data


def filter_recipes(
    recipes: Sequence[Mapping[str, Any]],
    min_score: float = 3,
    *,
    score_field: str = "total_health_score",
    strict: bool = False,
) -> FilterResult:
    """Keep recipes whose numeric health score meets the minimum."""
    
    filtered: list[dict[str, Any]] = []
    skipped_invalid = 0

    for index, recipe in enumerate(recipes):
        score = recipe.get(score_field)
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            message = f"Recipe {index} has an invalid '{score_field}' value: {score!r}"
            if strict:
                raise ValueError(message)
            LOGGER.warning("%s; skipping it.", message)
            skipped_invalid += 1
            continue

        if score >= min_score:
            filtered.append(dict(recipe))

    return FilterResult(
        recipes=filtered,
        total_count=len(recipes),
        kept_count=len(filtered),
        skipped_invalid_count=skipped_invalid,
    )


def filter_recipe_files(
    input_paths: Sequence[str | Path],
    output_path: str | Path,
    min_score: float = 3,
    *,
    score_field: str = "total_health_score",
    strict: bool = False,
) -> FilterResult:
    """Load one or more files, filter their recipes, and save one result file."""
    
    if not input_paths:
        raise ValueError("At least one input file is required.")

    all_recipes: list[dict[str, Any]] = []
    for input_path in input_paths:
        recipes = load_recipe_file(input_path)
        LOGGER.info("Loaded %s recipes from %s", len(recipes), input_path)
        all_recipes.extend(recipes)

    result = filter_recipes(
        all_recipes,
        min_score,
        score_field=score_field,
        strict=strict,
    )

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as file:
        json.dump(result.recipes, file, indent=2)

    LOGGER.info(
        "Saved %s of %s recipes to %s",
        result.kept_count,
        result.total_count,
        destination,
    )
    return result

