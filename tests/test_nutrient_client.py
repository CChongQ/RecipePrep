from unittest.mock import Mock, patch

from recipeprep.data.nutrient_client import get_nut_map


def test_get_nutrient_map_uses_cached_unit() -> None:
    nutrient_rows = [
        {
            "nutrient_web_name": "Protein",
            "nutrient_name_id": 1,
            "nutrient_value": 2.5,
        }
    ]
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = nutrient_rows

    with patch("recipeprep.data.nutrient_client.requests.get", return_value=response):
        result, unit_map = get_nut_map(123, "tomato", {"1": "g"})

    assert result == {
        "ingredient_name": "tomato",
        "nutrients": [{"value": 2.5, "nutrient_name": "Protein", "unit": "g"}],
    }
    assert unit_map == {"1": "g"}

