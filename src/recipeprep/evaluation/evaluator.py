"""Run health, relevance, and consistency evaluation together."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from recipeprep.evaluation.consistency import consistency_evaluation
from recipeprep.evaluation.relevance import relevance_evaluation
from recipeprep.nutrition.health_score import evaluate_recipe_health
from recipeprep.schemas import EvaluationResult, RelevanceResult


def evaluate_recipe(
    recipe: Mapping[str, Any],
    *,
    nutrient_retriever: Any,
    focused_tools: Sequence[str],
    input_tools: Sequence[str],
    input_time: int | float,
    input_ingredients: Sequence[str],
) -> EvaluationResult:
    """Run all deterministic recipe checks with one existing retriever."""
    health = evaluate_recipe_health(nutrient_retriever, recipe)
    relevance = RelevanceResult.model_validate(
        relevance_evaluation(
            focused_tools,
            input_tools,
            input_time,
            input_ingredients,
            recipe,
            nutrient_retriever,
        )
    )
    consistency = consistency_evaluation(recipe)
    return EvaluationResult(
        health=health,
        relevance=relevance,
        consistency=consistency,
    )

