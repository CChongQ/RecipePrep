from types import SimpleNamespace

import pytest

from app.gradio_app import (
    AppServices,
    generate_recipe,
    parse_comma_separated,
    parse_time_minutes,
)
from recipeprep.schemas import GeneratedRecipe


class FakeGenerator:
    def __init__(self):
        self.calls = []

    def generate(self, ingredients, tools, time, **options):
        self.calls.append((ingredients, tools, time, options))
        return GeneratedRecipe(
            title="Test Recipe",
            processed_ingredients=["1 tomato", "1 egg"],
            pure_ingredients=["tomato", "egg"],
            instructions=["Cook the egg.", "Add tomato."],
            required_tools=["pan", "stove"],
            cooking_time=20,
            suggestions=[],
        )


def test_parse_comma_separated_removes_empty_items() -> None:
    assert parse_comma_separated(" tomato, , egg ") == ["tomato", "egg"]
    assert parse_comma_separated(None) == []


def test_parse_time_minutes_validates_input() -> None:
    assert parse_time_minutes(29.6) == 30
    with pytest.raises(ValueError, match="greater than zero"):
        parse_time_minutes(0)
    with pytest.raises(ValueError, match="number"):
        parse_time_minutes("soon")


def test_generate_recipe_passes_clean_inputs_to_generator() -> None:
    generator = FakeGenerator()
    services = AppServices(generator=generator)  # type: ignore[arg-type]

    result = generate_recipe(
        "tomato, egg",
        "pan, stove",
        20,
        True,
        False,
        services=services,
    )

    assert "# Test Recipe" in result
    assert "1 tomato" in result
    assert "1. Cook the egg." in result
    assert generator.calls == [
        (
            ["tomato", "egg"],
            ["pan", "stove"],
            20,
            {
                "temperature": 0.8,
                "top_p": 1.0,
                "provide_example": True,
                "single_prompt": False,
            },
        )
    ]


def test_generate_recipe_returns_user_friendly_validation_error() -> None:
    services = AppServices(generator=SimpleNamespace())

    result = generate_recipe("", "pan", 20, True, False, services=services)

    assert result == "Error: Please enter at least one ingredient."
