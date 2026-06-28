"""Ingredient nutrient-map orchestration extracted from the notebook."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from recipeprep.data.nutrient_client import get_nut_map
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

    if nutrient_lookup is None:
        nutrient_lookup = get_nut_map

    all_mapping: list[dict[str, Any]] = []

    # Carry the unit cache through the full ingredient loop.
    current_unit_map = untri_unit_map

    # for each ingredient, look up and validate its nutrients 
    for ingredient, details in ingre_food_code_dict.items():
        # Validate the saved match before using its CNF food code.
        match = FoodCodeMatch.model_validate(details)

        # nutrient_lookup calls CNF by default through get_nut_map().
        map_created, updated_unit_map = nutrient_lookup(
            match.food_code,
            ingredient,
            current_unit_map,
        )
        if updated_unit_map is not None:
            current_unit_map = updated_unit_map

        if map_created:
            # Validate the generated nutrient record before saving it.
            validated_mapping = IngredientNutrientRecord.model_validate(map_created)
            all_mapping.append(validated_mapping.model_dump())
        else:
            print(f"Ingredient: {ingredient} - No nutrient amount found")

    print("All ingredients processed!")
    
    return all_mapping, current_unit_map
