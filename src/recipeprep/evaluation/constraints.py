"""Check recipe tool and cooking-time constraints."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


def _normalized_set(values: Sequence[str] | None) -> set[str]:
    """Lowercase and trim a list of names."""
    return {str(value).strip().lower() for value in values or [] if str(value).strip()}


def check_cooking_tools(
    input_tools: Sequence[str],
    recipe: Mapping[str, Any],
    focused_tools: Sequence[str],
) -> bool:
    """Return False when a focused required tool is not available."""
    
    recipe_tools = _normalized_set(recipe.get("required_tools", []))
    available_tools = _normalized_set(input_tools)
    focused = _normalized_set(focused_tools)
    missing = (recipe_tools & focused) - available_tools
    return not missing


def parse_cooking_time_minutes(value: Any) -> int:
    """Parse minutes, hours, and time ranges; ranges use the upper value."""
    
    if isinstance(value, (int, float)):
        if value < 0:
            raise ValueError("Cooking time cannot be negative.")
        return int(round(value))

    text = str(value or "").strip().lower()
    if not text:
        raise ValueError("Cooking time is missing.")

    numbers = [float(item) for item in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        raise ValueError(f"Cooking time has no number: {value}")

    hour_values = [
        float(item)
        for item in re.findall(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|hr)\b", text)
    ]
    minute_values = [
        float(item)
        for item in re.findall(r"(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|min)\b", text)
    ]
    if hour_values and minute_values:
        amount = max(hour_values) * 60 + max(minute_values)
    elif hour_values:
        amount = max(numbers) * 60
    else:
        amount = max(numbers)
    return int(round(amount))


def check_cooking_time(input_time: int | float, recipe: Mapping[str, Any]) -> int:
    """Return zero when within the limit, otherwise the exceeded minutes."""
    
    cooking_time = parse_cooking_time_minutes(recipe.get("cooking_time"))
    
    return max(0, cooking_time - int(input_time))
