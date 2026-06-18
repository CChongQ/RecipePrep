import pytest

from recipeprep.nutrition import (
    QuantityParseError,
    UnitConversionError,
    convert_to_grams,
    grams_for,
    parse_processed_ingredient,
    parse_quantity,
)


def test_parse_decimal_fraction_and_mixed_number() -> None:
    assert parse_quantity("1.5") == 1.5
    assert parse_quantity("1/2") == 0.5
    assert parse_quantity("1 1/2") == 1.5


def test_parse_processed_ingredient_uses_name_override() -> None:
    parsed = parse_processed_ingredient(
        "1 1/2 cups chopped tomatoes",
        name_override="tomato",
    )

    assert parsed.value == 1.5
    assert parsed.unit == "cups"
    assert parsed.name == "tomato"


def test_invalid_quantity_is_rejected_without_eval() -> None:
    with pytest.raises(QuantityParseError):
        parse_quantity("__import__('os').system('echo unsafe')")


def test_supported_unit_conversion() -> None:
    assert grams_for("2", "oz") == pytest.approx(56.7)
    assert convert_to_grams({"value": "1/2", "unit": "kg", "name": "rice"})[
        "value"
    ] == pytest.approx(500)


def test_unknown_unit_is_not_silently_converted() -> None:
    with pytest.raises(UnitConversionError):
        grams_for(1, "handful")

