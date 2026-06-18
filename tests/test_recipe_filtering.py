import json

import pytest

from recipeprep.data.recipe_filtering import (
    filter_recipe_files,
    filter_recipes,
    load_recipe_file,
)


def test_filter_recipes_keeps_scores_at_or_above_minimum() -> None:
    recipes = [
        {"recipe_id": "one", "total_health_score": 2},
        {"recipe_id": "two", "total_health_score": 3},
        {"recipe_id": "three", "total_health_score": 5},
    ]

    result = filter_recipes(recipes, min_score=3)

    assert [recipe["recipe_id"] for recipe in result.recipes] == ["two", "three"]
    assert result.total_count == 3
    assert result.kept_count == 2
    assert result.skipped_invalid_count == 0


def test_invalid_scores_are_skipped_by_default() -> None:
    recipes = [
        {"recipe_id": "missing"},
        {"recipe_id": "text", "total_health_score": "4"},
        {"recipe_id": "valid", "total_health_score": 4},
    ]

    result = filter_recipes(recipes)

    assert result.recipes == [{"recipe_id": "valid", "total_health_score": 4}]
    assert result.skipped_invalid_count == 2


def test_strict_mode_rejects_invalid_scores() -> None:
    with pytest.raises(ValueError, match="invalid"):
        filter_recipes([{"recipe_id": "missing"}], strict=True)


def test_filter_recipe_files_combines_inputs_in_order(tmp_path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    output = tmp_path / "filtered.json"
    first.write_text(
        json.dumps([{"recipe_id": "one", "total_health_score": 4}]),
        encoding="utf-8",
    )
    second.write_text(
        json.dumps(
            [
                {"recipe_id": "two", "total_health_score": 2},
                {"recipe_id": "three", "total_health_score": 6},
            ]
        ),
        encoding="utf-8",
    )

    result = filter_recipe_files([first, second], output, min_score=3)

    assert result.kept_count == 2
    assert json.loads(output.read_text(encoding="utf-8")) == [
        {"recipe_id": "one", "total_health_score": 4},
        {"recipe_id": "three", "total_health_score": 6},
    ]


def test_recipe_file_must_contain_a_list(tmp_path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps({"recipe": "not a list"}), encoding="utf-8")

    with pytest.raises(ValueError, match="JSON list"):
        load_recipe_file(path)

