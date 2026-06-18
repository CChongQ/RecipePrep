import json

from recipeprep.config import load_config
from recipeprep.retrieval.index import (
    get_normalized_foodCode_dataset,
    get_regular_foodCode_dataset,
)


def test_food_code_loaders_return_matching_codes(tmp_path) -> None:
    config = load_config(project_root=tmp_path)
    config.cnf_food_code_path.parent.mkdir(parents=True, exist_ok=True)
    config.cnf_food_code_path.write_text(
        json.dumps(
            [
                {"food_description": "Tomatoes, raw", "food_code": 10},
                {"food_description": "Olive oil", "food_code": 20},
            ]
        ),
        encoding="utf-8",
    )

    normalized, normalized_codes = get_normalized_foodCode_dataset(config=config)
    original, original_codes = get_regular_foodCode_dataset(config=config)

    assert normalized == ["tomato raw", "olive oil"]
    assert original == ["Tomatoes, raw", "Olive oil"]
    assert normalized_codes == original_codes == [10, 20]

