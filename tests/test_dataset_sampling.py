import json

from recipeprep.data.dataset_sampling import (
    combine_two_json,
    get_average_instruction_length,
    get_ingre_list_from_dataset,
)


def test_get_average_instruction_length(tmp_path) -> None:
    dataset = {
        "one": {"instructions": "abcd"},
        "two": {"instructions": "abcdefgh"},
    }
    path = tmp_path / "recipes.json"
    path.write_text(json.dumps(dataset), encoding="utf-8")

    assert get_average_instruction_length(path) == 6


def test_get_ingredient_list_from_processed_dataset(tmp_path) -> None:
    dataset = [
        {"pure_ingredients": ["Tomatoes", "olive oil"]},
        {"pure_ingredients": ["tomato", "Olive Oil"]},
    ]
    path = tmp_path / "processed.json"
    path.write_text(json.dumps(dataset), encoding="utf-8")

    assert get_ingre_list_from_dataset(path) == [
        "olive oil",
        "tomato",
        "olive oil",
        "tomato",
    ]


def test_combine_two_json(tmp_path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    output = tmp_path / "combined.json"
    first.write_text(json.dumps({"one": 1}), encoding="utf-8")
    second.write_text(json.dumps({"two": 2}), encoding="utf-8")

    combine_two_json(first, second, output)

    assert json.loads(output.read_text(encoding="utf-8")) == {"one": 1, "two": 2}
