from types import SimpleNamespace

from recipeprep.nutrition import evaluate_recipe_health, score_nutrient_totals


BALANCED_NUTRIENTS = [
    {"value": 10.0, "nutrient_name": "Protein", "unit": "g"},
    {"value": 30.0, "nutrient_name": "Carbohydrate", "unit": "g"},
    {"value": 2.0, "nutrient_name": "Sugars, total", "unit": "g"},
    {"value": 1000.0, "nutrient_name": "Sodium, Na", "unit": "mg"},
    {"value": 5.0, "nutrient_name": "Total Fat", "unit": "g"},
    {
        "value": 1.0,
        "nutrient_name": "Fatty acids, saturated, total",
        "unit": "g",
    },
    {"value": 13.0, "nutrient_name": "Fibre, total dietary", "unit": "g"},
    {"value": 1000.0, "nutrient_name": "Energy (kJ)", "unit": "kJ"},
]


class FakeRetriever:
    def __init__(self, nutrients):
        self.nutrients = nutrients

    def invoke(self, _query):
        return [
            SimpleNamespace(
                metadata={
                    "ingredient_name": "test food",
                    "nutrients": str(self.nutrients),
                }
            )
        ]


def test_balanced_recipe_scores_all_points() -> None:
    recipe = {
        "processed_ingredients": ["100 g test food"],
        "pure_ingredients": ["test food"],
    }

    result = evaluate_recipe_health(FakeRetriever(BALANCED_NUTRIENTS), recipe)

    assert result.total_health_score == 7
    assert result.summary_of_points["Sodium"] == 1
    assert result.nutrient_totals["Sodium, Na"] == 1000


def test_sodium_uses_milligram_threshold() -> None:
    totals = {row["nutrient_name"]: row["value"] for row in BALANCED_NUTRIENTS}
    totals["Sodium, Na"] = 3000

    result = score_nutrient_totals(totals)

    assert result.total_health_score == 6
    assert result.summary_of_points["Sodium"] == 0


def test_unknown_unit_is_skipped_and_reported() -> None:
    recipe = {
        "processed_ingredients": ["1 handful test food"],
        "pure_ingredients": ["test food"],
    }

    result = evaluate_recipe_health(FakeRetriever(BALANCED_NUTRIENTS), recipe)

    assert result.total_health_score == 0
    assert result.warnings

