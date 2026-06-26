"""Calculate recipe nutrient totals and a deterministic health score."""

from __future__ import annotations

import ast
import json
import logging
from typing import Any, Mapping, Sequence

from recipeprep.config import AppConfig, get_config
from recipeprep.nutrition.quantity_parser import (
    QuantityParseError,
    parse_processed_ingredient,
)
from recipeprep.nutrition.unit_conversion import (
    UnitConversionError,
    parsed_ingredient_to_grams,
)
from recipeprep.retrieval.vector_store import retrieve_food_and_nutrients
from recipeprep.schemas import HealthScoreResult

LOGGER = logging.getLogger(__name__)

NUTRIENT_NAMES = (
    "Protein",
    "Carbohydrate",
    "Sugars, total",
    "Sodium, Na",
    "Total Fat",
    "Fatty acids, saturated, total",
    "Fibre, total dietary",
    "Energy (kJ)",
)


def parse_nutrient_metadata(nutrients: Any) -> list[dict[str, Any]]:
    """Read nutrients stored as a list or as the retriever's string metadata."""
    if isinstance(nutrients, list):
        data = nutrients
    elif isinstance(nutrients, str):
        try:
            data = json.loads(nutrients)
        except json.JSONDecodeError:
            try:
                data = ast.literal_eval(nutrients)
            except (SyntaxError, ValueError) as error:
                raise ValueError("Nutrient metadata is not a valid list.") from error
    else:
        raise ValueError("Nutrient metadata is missing.")

    if not isinstance(data, list):
        raise ValueError("Nutrient metadata must be a list.")
    return [item for item in data if isinstance(item, dict)]


def calculate_nutrient_totals(
    retriever: Any,
    recipe: Mapping[str, Any],
) -> tuple[dict[str, float], list[str]]:
    """Sum supported nutrients for all parseable recipe ingredients."""
    
    processed = recipe.get("processed_ingredients") or []
    pure = recipe.get("pure_ingredients") or []
    if not isinstance(processed, Sequence) or isinstance(processed, str):
        raise ValueError("processed_ingredients must be a list.")
    if not isinstance(pure, Sequence) or isinstance(pure, str):
        raise ValueError("pure_ingredients must be a list.")

    totals = {name: 0.0 for name in NUTRIENT_NAMES}
    warnings: list[str] = []

    for index, ingredient_text in enumerate(processed):
        name_override = str(pure[index]) if len(pure) == len(processed) else None
        try:
            parsed = parse_processed_ingredient(
                str(ingredient_text),
                name_override=name_override,
            )
            grams = parsed_ingredient_to_grams(parsed)
            _, nutrient_data = retrieve_food_and_nutrients(retriever, parsed.name)
            nutrient_rows = parse_nutrient_metadata(nutrient_data)
        except (QuantityParseError, UnitConversionError, ValueError) as error:
            warning = f"Skipped '{ingredient_text}': {error}"
            warnings.append(warning)
            LOGGER.warning(warning)
            continue

        for nutrient in nutrient_rows:
            nutrient_name = nutrient.get("nutrient_name")
            if nutrient_name in totals:
                totals[nutrient_name] += float(nutrient.get("value", 0)) * grams / 100

    return totals, warnings


def score_nutrient_totals(
    totals: Mapping[str, float],
    *,
    config: AppConfig | None = None,
    warnings: list[str] | None = None,
) -> HealthScoreResult:
    """Apply configured nutrition thresholds to pre-calculated totals."""
    
    settings = config or get_config()
    thresholds = settings.nutrition
    total_energy = float(totals.get("Energy (kJ)", 0))
    has_nutrition_data = total_energy > 0

    protein_energy = float(totals.get("Protein", 0)) * 17
    carbohydrate_energy = float(totals.get("Carbohydrate", 0)) * 17
    sugar_energy = float(totals.get("Sugars, total", 0)) * 17
    fat_energy = float(totals.get("Total Fat", 0)) * 37
    saturated_fat_energy = (
        float(totals.get("Fatty acids, saturated, total", 0)) * 37
    )

    # Each nutrition metric is scored 1 if it meets the rule, otherwise 0
    summary = {
        "Proteins": int(
            total_energy > 0
            and thresholds.protein_energy_min
            <= protein_energy / total_energy
            <= thresholds.protein_energy_max
        ),
        "Carbohydrates": int(
            total_energy > 0
            and thresholds.carbohydrate_energy_min
            <= carbohydrate_energy / total_energy
            <= thresholds.carbohydrate_energy_max
        ),
        "Sugars": int(
            total_energy > 0
            and sugar_energy / total_energy <= thresholds.sugar_energy_max
        ),
        "Sodium": int(
            has_nutrition_data
            and float(totals.get("Sodium, Na", 0)) <= thresholds.sodium_max_mg
        ),
        "Fats": int(
            total_energy > 0
            and thresholds.fat_energy_min
            <= fat_energy / total_energy
            <= thresholds.fat_energy_max
        ),
        "Saturated Fats": int(
            total_energy > 0
            and saturated_fat_energy / total_energy
            <= thresholds.saturated_fat_energy_max
        ),
        "Fibers": int(
            has_nutrition_data
            and float(totals.get("Fibre, total dietary", 0)) >= thresholds.fiber_min_g
        ),
    }
    return HealthScoreResult(
        total_health_score=sum(summary.values()),
        summary_of_points=summary,
        nutrient_totals={key: float(value) for key, value in totals.items()},
        warnings=warnings or [],
    )


def evaluate_recipe_health(
    retriever: Any,
    recipe: Mapping[str, Any],
    *,
    config: AppConfig | None = None,
) -> HealthScoreResult:
    """Calculate nutrient totals and return the full health-score result."""
    
    totals, warnings = calculate_nutrient_totals(retriever, recipe)
    
    return score_nutrient_totals(totals, config=config, warnings=warnings)


def get_health_score_with_rag(
    retriever: Any,
    recipe: Mapping[str, Any],
) -> tuple[int, dict[str, int]]:
    """Compatibility wrapper returning the old score-and-summary tuple."""
    result = evaluate_recipe_health(retriever, recipe)
    return result.total_health_score, result.summary_of_points
