"""Clean and validate recipe JSON returned by the model."""

from __future__ import annotations

import json
from typing import Any

from recipeprep.schemas import GeneratedRecipe


def clean_json_text(response_text: str) -> str:
    """Remove common Markdown code fences around a JSON response."""
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def parse_generated_recipe(response_text: str) -> GeneratedRecipe:
    """Parse model text and return a validated generated recipe."""
    data: dict[str, Any] = json.loads(clean_json_text(response_text))
    if "processed_ingredients" not in data and "ingredients" in data:
        data["processed_ingredients"] = data.pop("ingredients")
    if isinstance(data.get("instructions"), str):
        data["instructions"] = [
            line.strip()
            for line in data["instructions"].splitlines()
            if line.strip()
        ]
    for field in ("processed_ingredients", "pure_ingredients", "required_tools"):
        if isinstance(data.get(field), str):
            data[field] = [
                item.strip() for item in data[field].splitlines() if item.strip()
            ]
    return GeneratedRecipe.model_validate(data)

