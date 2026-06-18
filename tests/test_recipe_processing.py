import json
from types import SimpleNamespace

from recipeprep.data.recipe_processing import (
    get_processed_recipe_dataset,
    process_API_res_get_processed_recipe,
)


RAW_RECIPE = {
    "title": "Test Soup",
    "ingredients": ["1 cup water", "1 carrot"],
    "instructions": "Boil the water. Add the carrot.",
    "picture_link": None,
}

PROCESSED_RESPONSE = {
    "step_by_step_instructions": ["Boil the water.", "Add the carrot."],
    "processed_ingredients": ["1 cup water", "100 g carrot"],
    "pure_ingredients": ["water", "carrot"],
    "cooking_time": "10 minutes",
    "required_tools": ["pot"],
}


class FakeChatCompletions:
    def create(self, **_: object) -> SimpleNamespace:
        message = SimpleNamespace(content=json.dumps(PROCESSED_RESPONSE))
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])


class FakeClient:
    chat = SimpleNamespace(completions=FakeChatCompletions())


def test_process_response_returns_existing_dictionary_shape() -> None:
    result = process_API_res_get_processed_recipe(
        json.dumps(PROCESSED_RESPONSE),
        "recipe-1",
        RAW_RECIPE,
    )

    assert result["recipe_id"] == "recipe-1"
    assert result["recipe_title"] == "Test Soup"
    assert result["processed_ingredients"] == ["1 cup water", "100 g carrot"]


def test_invalid_response_returns_empty_dictionary() -> None:
    assert process_API_res_get_processed_recipe("not json", "recipe-1", RAW_RECIPE) == {}


def test_batch_processing_does_not_write_empty_trailing_batch(tmp_path) -> None:
    recipes = {
        "recipe-1": RAW_RECIPE,
        "recipe-2": RAW_RECIPE,
    }

    batch_count = get_processed_recipe_dataset(
        FakeClient(),
        temp=0.0,
        topp=1.0,
        recipe_dataset=recipes,
        batch_size=1,
        output_dir=tmp_path,
    )

    output_files = sorted(tmp_path.glob("*.json"))
    assert batch_count == 2
    assert len(output_files) == 2
    assert all(json.loads(path.read_text(encoding="utf-8")) for path in output_files)

