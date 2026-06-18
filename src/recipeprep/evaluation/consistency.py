"""Run simple deterministic checks on generated recipe structure."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from recipeprep.nutrition.quantity_parser import (
    QuantityParseError,
    parse_processed_ingredient,
)
from recipeprep.schemas import ConsistencyResult


def evaluate_instruction_clarity(recipe: Mapping[str, Any]) -> bool:
    """Check that the recipe has non-empty instruction steps."""
    instructions = recipe.get("instructions") or recipe.get("step_by_step_instructions")
    return bool(
        isinstance(instructions, Sequence)
        and not isinstance(instructions, str)
        and all(str(step).strip() for step in instructions)
    )


def evaluate_measurement_consistency(recipe: Mapping[str, Any]) -> bool:
    """Check that each processed ingredient starts with an amount and unit."""
    ingredients = recipe.get("processed_ingredients") or []
    if not isinstance(ingredients, Sequence) or isinstance(ingredients, str):
        return False
    if not ingredients:
        return False
    try:
        for ingredient in ingredients:
            parse_processed_ingredient(str(ingredient))
    except QuantityParseError:
        return False
    return True


def evaluate_step_sequence(recipe: Mapping[str, Any]) -> bool:
    """Check that the recipe has at least one ordered instruction step."""
    instructions = recipe.get("instructions") or recipe.get("step_by_step_instructions")
    return bool(
        isinstance(instructions, Sequence)
        and not isinstance(instructions, str)
        and len(instructions) > 0
    )


def consistency_evaluation(recipe: Mapping[str, Any]) -> ConsistencyResult:
    """Return the three documented consistency checks."""
    return ConsistencyResult(
        instructional_clarity=evaluate_instruction_clarity(recipe),
        measurement_consistency=evaluate_measurement_consistency(recipe),
        logical_step_sequence=evaluate_step_sequence(recipe),
    )

