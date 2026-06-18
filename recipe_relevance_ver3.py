"""Compatibility imports for the extracted relevance evaluation package.

New code should import from ``recipeprep.evaluation`` directly.
"""

from recipeprep.evaluation import (
    check_cooking_time,
    check_cooking_tools,
    compare_ingredient_list,
    get_matched_list,
    get_similarity,
    parse_cooking_time_minutes,
    relevance_evaluation as _relevance_evaluation,
)
from recipeprep.retrieval import build_nutrient_retriever

__all__ = [
    "build_nutrient_retriever",
    "check_cooking_time",
    "check_cooking_tools",
    "compare_ingredient_list",
    "get_matched_list",
    "get_similarity",
    "parse_cooking_time_minutes",
    "relevance_evaluation",
]


def relevance_evaluation(
    focused_tools,
    input_tools,
    input_time,
    input_ingredients,
    recipe,
    nutrient_map_path,
):
    """Keep the old file-path interface while using the extracted evaluator."""
    retriever = build_nutrient_retriever(nutrient_map_path)
    return _relevance_evaluation(
        focused_tools,
        input_tools,
        input_time,
        input_ingredients,
        recipe,
        retriever,
    )
