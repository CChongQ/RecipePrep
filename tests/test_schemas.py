import json
from pathlib import Path
from typing import Any

from recipeprep.schemas import IngredientNutrientRecord, ProcessedRecipe, RawRecipe

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "schema_records.json"


def load_schema_records() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_raw_recipe_schema_accepts_fixture_recipe_data() -> None:
    data = load_schema_records()["raw_recipes"]
    recipe_id, recipe = next(iter(data.items()))

    validated = RawRecipe.model_validate(recipe)

    assert recipe_id
    assert validated.title
    assert validated.ingredients
    assert validated.instructions


def test_processed_recipe_schema_accepts_fixture_processed_data() -> None:
    data = load_schema_records()["processed_recipes"]

    validated = ProcessedRecipe.model_validate(data[0])

    assert validated.recipe_id
    assert validated.processed_ingredients
    assert validated.pure_ingredients


def test_nutrient_schema_accepts_fixture_nutrient_map() -> None:
    data = load_schema_records()["ingredient_nutrients"]

    validated = IngredientNutrientRecord.model_validate(data[0])

    assert validated.ingredient_name
    assert validated.nutrients
