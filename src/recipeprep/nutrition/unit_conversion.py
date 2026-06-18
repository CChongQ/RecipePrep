"""Convert supported recipe units to approximate grams."""

from __future__ import annotations

from collections.abc import Mapping

from recipeprep.nutrition.quantity_parser import ParsedIngredient, parse_quantity


class UnitConversionError(ValueError):
    """Raised when a unit has no safe conversion rule."""


# Volume conversions are project-wide estimates, not ingredient-specific densities.
GRAMS_PER_UNIT: dict[str, float] = {
    "tablespoon": 17.07,
    "teaspoon": 5.69,
    "ounce": 28.35,
    "cup": 150.0,
    "lb": 453.59,
    "pound": 453.59,
    "tbsp": 17.07,
    "tsp": 5.69,
    "oz": 28.35,
    "kg": 1000.0,
    "kilogram": 1000.0,
    "gram": 1.0,
    "g": 1.0,
    "mg": 0.001,
    "ml": 0.92,
    "clove": 4.0,
}

UNIT_ALIASES = {
    "tablespoons": "tablespoon",
    "teaspoons": "teaspoon",
    "ounces": "ounce",
    "cups": "cup",
    "pounds": "pound",
    "kilograms": "kilogram",
    "grams": "gram",
    "cloves": "clove",
}


def normalize_unit(unit: str) -> str:
    """Return the supported singular form of a unit."""
    normalized = unit.strip().lower()
    return UNIT_ALIASES.get(normalized, normalized)


def grams_for(value: str | int | float, unit: str) -> float:
    """Convert one supported amount to grams."""
    normalized_unit = normalize_unit(unit)
    factor = GRAMS_PER_UNIT.get(normalized_unit)
    if factor is None:
        raise UnitConversionError(f"Unsupported unit: {unit or '<missing>'}")
    return parse_quantity(value) * factor


def parsed_ingredient_to_grams(ingredient: ParsedIngredient) -> float:
    """Convert a parsed ingredient amount to grams."""
    return grams_for(ingredient.value, ingredient.unit)


def convert_to_grams(ingredient_dict: Mapping[str, object]) -> dict[str, object]:
    """Compatibility helper that returns a copied ingredient dictionary."""
    converted = dict(ingredient_dict)
    converted["value"] = grams_for(
        ingredient_dict["value"],  # type: ignore[arg-type]
        str(ingredient_dict.get("unit", "")),
    )
    converted["unit"] = "gram"
    return converted

