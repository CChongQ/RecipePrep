"""Compatibility imports for the extracted nutrition scoring package.

New code should import from ``recipeprep.nutrition`` directly.
"""

from recipeprep.nutrition import (
    calculate_nutrient_totals,
    convert_to_grams,
    evaluate_recipe_health,
    get_health_score_with_rag,
    parse_nutrient_metadata,
    parse_processed_ingredient,
    parse_quantity,
    score_nutrient_totals,
)
from recipeprep.retrieval import (
    build_nutrient_retriever,
    retrieve_food_and_nutrients,
)

__all__ = [
    "build_nutrient_retriever",
    "calculate_nutrient_totals",
    "convert_to_grams",
    "evaluate_recipe_health",
    "get_health_score_with_rag",
    "parse_nutrient_metadata",
    "parse_processed_ingredient",
    "parse_quantity",
    "retrieve_food_and_nutrients",
    "score_nutrient_totals",
]
