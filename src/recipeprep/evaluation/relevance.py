"""Evaluate tool, time, and ingredient relevance."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from recipeprep.evaluation.constraints import check_cooking_time, check_cooking_tools
from recipeprep.retrieval.vector_store import retrieve_food_and_nutrients
from recipeprep.schemas import RelevanceResult


def get_matched_list(ingredient_list: Sequence[str], retriever: Any) -> list[str]:
    """Map ingredient names to the closest names stored in the nutrient map."""
    matched: list[str] = []
    for ingredient in ingredient_list:
        matched_name, _ = retrieve_food_and_nutrients(retriever, ingredient)
        matched.append((matched_name or ingredient).strip().lower())
    return matched


def compare_ingredient_list(
    user_root_list: Sequence[str],
    recipe_root_list: Sequence[str],
) -> tuple[bool, float]:
    """Return full coverage and the percent of recipe ingredients available."""
    user_set = {item.strip().lower() for item in user_root_list if item}
    recipe_set = {item.strip().lower() for item in recipe_root_list if item}
    if not recipe_set:
        return False, 0.0
    common = user_set & recipe_set
    return recipe_set.issubset(user_set), len(common) / len(recipe_set) * 100


def get_similarity(
    input_ingredients: Sequence[str],
    recipe: Mapping[str, Any],
    retriever: Any,
) -> tuple[bool, float]:
    """Compare user ingredients with the generated recipe ingredients."""
    
    recipe_ingredients = recipe.get("pure_ingredients") or []
    if not isinstance(recipe_ingredients, Sequence) or isinstance(
        recipe_ingredients, str
    ):
        raise ValueError("pure_ingredients must be a list.")
    
    user_matches = get_matched_list(input_ingredients, retriever)
    recipe_matches = get_matched_list(
        [str(item) for item in recipe_ingredients],
        retriever,
    )
    
    return compare_ingredient_list(user_matches, recipe_matches)


def relevance_evaluation(
    focused_tools: Sequence[str],
    input_tools: Sequence[str],
    input_time: int | float,
    input_ingredients: Sequence[str],
    recipe: Mapping[str, Any],
    retriever: Any,
) -> dict[str, bool | int | float]:
    """Return relevance metrics using an existing ingredient retriever."""
    
    tool_result = check_cooking_tools(input_tools, recipe, focused_tools)
    time_result = check_cooking_time(input_time, recipe)
    _, overlap_rate = get_similarity(input_ingredients, recipe, retriever)
    result = RelevanceResult(
        cooking_tools=tool_result,
        cooking_time=time_result,
        ingredient_overlap_rate=overlap_rate,
    )
    return result.model_dump()

