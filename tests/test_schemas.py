import json
from pathlib import Path

from recipeprep.schemas import IngredientNutrientRecord, ProcessedRecipe, RawRecipe


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_raw_recipe_schema_accepts_existing_recipe_data() -> None:
    data = json.loads(
        (PROJECT_ROOT / "datasets" / "recipe_dataset_init_200.json").read_text(
            encoding="utf-8"
        )
    )
    recipe_id, recipe = next(iter(data.items()))

    validated = RawRecipe.model_validate(recipe)

    assert recipe_id
    assert validated.title
    assert validated.ingredients
    assert validated.instructions


def test_processed_recipe_schema_accepts_existing_processed_data() -> None:
    data = json.loads(
        (
            PROJECT_ROOT
            / "datasets"
            / "Data_Processing_Agent_testing"
            / "processed_recipes_init_5.json"
        ).read_text(encoding="utf-8")
    )

    validated = ProcessedRecipe.model_validate(data[0])

    assert validated.recipe_id
    assert validated.processed_ingredients
    assert validated.pure_ingredients


def test_nutrient_schema_accepts_existing_map() -> None:
    data = json.loads(
        (
            PROJECT_ROOT
            / "ingre_nutrition_map"
            / "ingredient_nutrient_map.json"
        ).read_text(encoding="utf-8")
    )

    validated = IngredientNutrientRecord.model_validate(data[0])

    assert validated.ingredient_name
    assert validated.nutrients
