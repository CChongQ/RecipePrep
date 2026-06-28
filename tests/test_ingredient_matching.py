from recipeprep.retrieval.ingredient_matcher import (
    IngredientMatcher,
    get_food_code_for_ingredients,
)


def test_exact_match_does_not_call_embedding_api() -> None:
    matcher = IngredientMatcher(
        client=None,
        index=None,
        food_descriptions=["tomato"],
        food_codes=[123],
        food_descriptions_ori=["Tomato, raw"],
    )

    result = get_food_code_for_ingredients(["tomato"], matcher)

    assert result["tomato"] == {
        "food_code": 123,
        "description": "Tomato, raw",
        "similarity": 1.0,
    }

