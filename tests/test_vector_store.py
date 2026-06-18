import json
from types import SimpleNamespace

from recipeprep.retrieval.vector_store import (
    get_recipe_by_id,
    load_and_process_json,
    retrieve_food_and_nutrients,
    retrieve_similar_recipe_id,
)


class FakeRetriever:
    def __init__(self, documents):
        self.documents = documents
        self.queries = []

    def invoke(self, query):
        self.queries.append(query)
        return self.documents


def test_load_and_process_recipe_json(tmp_path) -> None:
    path = tmp_path / "recipes.json"
    path.write_text(
        json.dumps(
            [
                {
                    "recipe_id": "one",
                    "recipe_title": "Soup",
                    "pure_ingredients": ["carrot", "water"],
                }
            ]
        ),
        encoding="utf-8",
    )

    result = load_and_process_json(path)

    assert result == [
        {
            "page_content": "carrot, water",
            "metadata": {
                "recipe_title": "Soup",
                "recipe_id": "one",
                "pure_ingredients": "carrot, water",
            },
        }
    ]


def test_retrieve_nutrients_uses_first_result() -> None:
    document = SimpleNamespace(
        metadata={"ingredient_name": "tomato", "nutrients": "protein data"}
    )

    assert retrieve_food_and_nutrients(FakeRetriever([document]), "tomato") == (
        "tomato",
        "protein data",
    )


def test_retrieve_recipe_ids_builds_sorted_query() -> None:
    documents = [
        SimpleNamespace(metadata={"recipe_id": "one"}),
        SimpleNamespace(metadata={"recipe_id": "two"}),
    ]
    retriever = FakeRetriever(documents)

    result = retrieve_similar_recipe_id(retriever, ["tomato", "beef"])

    assert result == {"one", "two"}
    assert retriever.queries == ["beef,tomato"]


def test_get_recipe_by_id_returns_matching_recipe() -> None:
    recipes = [{"recipe_id": "one"}, {"recipe_id": "two"}]

    assert get_recipe_by_id(recipes, "two") == {"recipe_id": "two"}
    assert get_recipe_by_id(recipes, "missing") is None

