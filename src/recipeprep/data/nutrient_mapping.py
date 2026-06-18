"""Ingredient nutrient-map orchestration extracted from the notebook."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Callable, Mapping, cast

from recipeprep.schemas import FoodCodeMatch, IngredientNutrientRecord

NutrientLookup = Callable[
    [int | str | None, str, dict[str, Any]],
    tuple[dict[str, Any] | None, dict[str, Any] | None],
]
"""Function shape used to look up CNF nutrients for one ingredient."""


def get_all_ingredient_mapping(
    ingre_food_code_dict: Mapping[str, Mapping[str, Any]],
    untri_unit_map: dict[str, Any],
    *,
    nutrient_lookup: NutrientLookup | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Create nutrient-map records from ingredient-to-food-code matches."""

    # Use the existing CNF helper unless a test or caller provides another lookup.
    if nutrient_lookup is None:
        legacy_helper = import_module("Helpers.food_nutrient_mapping_helpder")
        nutrient_lookup = cast(NutrientLookup, legacy_helper.get_nut_map)

    all_mapping: list[dict[str, Any]] = []
    current_unit_map = untri_unit_map

    # Look up and validate one nutrient record for each matched ingredient.
    for ingredient, details in ingre_food_code_dict.items():
        match = FoodCodeMatch.model_validate(details)
        map_created, updated_unit_map = nutrient_lookup(
            match.food_code,
            ingredient,
            current_unit_map,
        )
        if updated_unit_map is not None:
            current_unit_map = updated_unit_map

        if map_created:
            validated_mapping = IngredientNutrientRecord.model_validate(map_created)
            all_mapping.append(validated_mapping.model_dump())
        else:
            print(f"Ingredient: {ingredient} - No nutrient amount found")

    print("All ingredients processed!")
    return all_mapping, current_unit_map
