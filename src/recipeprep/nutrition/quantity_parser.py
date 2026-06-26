"""Parse ingredient amounts without running input as Python code."""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction


class QuantityParseError(ValueError):
    """Raised when an ingredient amount cannot be read safely."""


@dataclass(frozen=True)
class ParsedIngredient:
    """A processed ingredient split into amount, unit, and name."""

    value: float
    unit: str
    name: str
    original_text: str


_INGREDIENT_PATTERN = re.compile(
    r"^\s*(?P<amount>\d+(?:\.\d+)?(?:\s+\d+/\d+)?|\d+/\d+)"
    r"\s*(?P<unit>[A-Za-z]+)?\s+(?P<name>.+?)\s*$"
)


def parse_quantity(value: str | int | float) -> float:
    """Parse a decimal, fraction, or mixed number such as '1 1/2'."""
    
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        raise QuantityParseError("Quantity is empty.")

    try:
        if " " in text:
            whole, fraction = text.split(maxsplit=1)
            return float(int(whole) + Fraction(fraction))
        if "/" in text:
            return float(Fraction(text))
        return float(text)
    except (ValueError, ZeroDivisionError) as error:
        raise QuantityParseError(f"Invalid quantity: {value}") from error


def parse_processed_ingredient(
    ingredient_text: str,
    *,
    name_override: str | None = None,
) -> ParsedIngredient:
    """Parse the standard 'amount unit ingredient' recipe format."""
    
    match = _INGREDIENT_PATTERN.match(ingredient_text)
    if match is None:
        raise QuantityParseError(
            f"Ingredient must use 'amount unit name' format: {ingredient_text}"
        )

    unit = (match.group("unit") or "").lower()
    name = (name_override or match.group("name")).strip()
    if not name:
        raise QuantityParseError(f"Ingredient name is empty: {ingredient_text}")

    return ParsedIngredient(
        value=parse_quantity(match.group("amount")),
        unit=unit,
        name=name,
        original_text=ingredient_text,
    )

