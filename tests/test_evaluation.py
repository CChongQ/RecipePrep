from types import SimpleNamespace

from recipeprep.evaluation import (
    check_cooking_time,
    check_cooking_tools,
    compare_ingredient_list,
    consistency_evaluation,
    parse_cooking_time_minutes,
    relevance_evaluation,
)


class IdentityRetriever:
    def invoke(self, query):
        return [
            SimpleNamespace(
                metadata={"ingredient_name": query.lower(), "nutrients": "[]"}
            )
        ]


def test_time_parser_handles_ranges_and_hours() -> None:
    assert parse_cooking_time_minutes("20-30 minutes") == 30
    assert parse_cooking_time_minutes("1.5 hours") == 90
    assert parse_cooking_time_minutes("1 hour 30 minutes") == 90
    assert check_cooking_time(20, {"cooking_time": "20-30 minutes"}) == 10


def test_tool_check_is_case_insensitive() -> None:
    recipe = {"required_tools": ["Oven", "Pan"]}

    assert check_cooking_tools(["pan"], recipe, ["oven", "pan"]) is False
    assert check_cooking_tools(["OVEN", "pan"], recipe, ["oven", "pan"]) is True


def test_empty_recipe_ingredient_list_is_not_full_coverage() -> None:
    assert compare_ingredient_list(["tomato"], []) == (False, 0.0)


def test_relevance_uses_existing_retriever() -> None:
    recipe = {
        "required_tools": ["pan"],
        "cooking_time": 20,
        "pure_ingredients": ["tomato", "egg"],
    }

    result = relevance_evaluation(
        ["pan", "oven"],
        ["pan"],
        20,
        ["tomato"],
        recipe,
        IdentityRetriever(),
    )

    assert result == {
        "cooking_tools": True,
        "cooking_time": 0,
        "ingredient_overlap_rate": 50.0,
    }


def test_consistency_checks_recipe_structure() -> None:
    valid = {
        "processed_ingredients": ["100 g tomato"],
        "instructions": ["Chop the tomato.", "Serve."],
    }
    invalid = {
        "processed_ingredients": ["tomato to taste"],
        "instructions": [],
    }

    assert consistency_evaluation(valid).model_dump() == {
        "instructional_clarity": True,
        "measurement_consistency": True,
        "logical_step_sequence": True,
    }
    assert consistency_evaluation(invalid).model_dump() == {
        "instructional_clarity": False,
        "measurement_consistency": False,
        "logical_step_sequence": False,
    }
