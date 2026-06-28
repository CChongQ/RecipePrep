import json
from types import SimpleNamespace

from recipeprep.generation.recipe_generator import (
    build_user_prompt,
    get_API_response,
    get_generate_sys_prompt,
    get_recipe,
)
from recipeprep.generation.structured_output import parse_generated_recipe

GENERATED_RECIPE = {
    "title": "Tomato Toast",
    "processed_ingredients": ["1 tomato", "1 slice bread"],
    "pure_ingredients": ["tomato", "bread"],
    "instructions": ["Toast the bread.", "Add tomato."],
    "required_tools": ["toaster"],
    "cooking_time": 5,
    "suggestions": [],
}


class FakeCompletions:
    def __init__(self, content):
        self.content = content
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeClient:
    def __init__(self, content):
        self.completions = FakeCompletions(content)
        self.chat = SimpleNamespace(completions=self.completions)


class FakeRetriever:
    def __init__(self, documents):
        self.documents = documents

    def invoke(self, _query):
        return self.documents


def test_parse_generated_recipe_removes_code_fence() -> None:
    response = f"```json\n{json.dumps(GENERATED_RECIPE)}\n```"

    recipe = parse_generated_recipe(response)

    assert recipe.title == "Tomato Toast"
    assert recipe.cooking_time == 5


def test_api_response_uses_supplied_prompts() -> None:
    client = FakeClient("recipe text")

    result = get_API_response(client, "system", "user", 0.2, 0.9)

    assert result == "recipe text"
    assert client.completions.calls[0]["messages"][0]["content"] == "system"


def test_generation_prompt_uses_recipe_and_nutrient_retrievers(tmp_path) -> None:
    recipes_path = tmp_path / "recipes.json"
    recipes_path.write_text(
        json.dumps(
            [
                {
                    "recipe_id": "one",
                    "recipe_title": "Tomato Toast",
                    "processed_ingredients": ["1 tomato", "1 slice bread"],
                    "pure_ingredients": ["tomato", "bread"],
                    "step_by_step_instructions": ["Toast bread.", "Add tomato."],
                    "summary_of_points": {"Protein": 0},
                    "cooking_time": "5 minutes",
                    "required_tools": ["toaster"],
                    "total_health_score": 4,
                }
            ]
        ),
        encoding="utf-8",
    )
    nutrient_document = SimpleNamespace(
        metadata={"ingredient_name": "tomato", "nutrients": "nutrient data"}
    )
    recipe_document = SimpleNamespace(metadata={"recipe_id": "one"})

    prompt = get_generate_sys_prompt(
        recipes_path,
        ["tomato"],
        FakeRetriever([nutrient_document]),
        FakeRetriever([recipe_document]),
    )

    assert "Tomato Toast" in prompt
    assert "nutrient data" in prompt


def test_get_recipe_returns_model_text(tmp_path) -> None:
    recipes_path = tmp_path / "recipes.json"
    recipes_path.write_text("[]", encoding="utf-8")
    client = FakeClient(json.dumps(GENERATED_RECIPE))
    empty_retriever = FakeRetriever([])

    result = get_recipe(
        client,
        ["tomato"],
        ["toaster"],
        10,
        0.8,
        1.0,
        recipes_path,
        retriever_nutrient=empty_retriever,
        retriever_recipe=empty_retriever,
        provide_example=False,
    )

    assert json.loads(result)["title"] == "Tomato Toast"
    assert "toaster" in build_user_prompt(["tomato"], ["toaster"], 10)

