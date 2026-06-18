"""Build recipe prompts and call the model to generate a recipe."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from recipeprep.config import AppConfig, get_config
from recipeprep.generation.structured_output import parse_generated_recipe
from recipeprep.retrieval.vector_store import (
    get_recipe_by_id,
    load_file_content,
    retrieve_food_and_nutrients,
    retrieve_similar_recipe_id,
)
from recipeprep.schemas import GeneratedRecipe

LOGGER = logging.getLogger(__name__)


def get_API_response(
    client: Any,
    sys_prompt: str,
    user_prompt: str,
    temp: float,
    top_p: float,
    *,
    model: str | None = None,
) -> str:
    """Send recipe prompts to the configured chat model."""
    config = get_config()
    completion = client.chat.completions.create(
        model=model or config.openai.chat_model,
        temperature=temp,
        top_p=top_p,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = completion.choices[0].message.content
    if content is None:
        raise ValueError("The recipe model returned no content.")
    return str(content).strip()


def _format_recipe_example(recipe: dict[str, Any]) -> str:
    """Format one saved recipe for use as an example in the prompt."""
    nutrient_points = recipe.get("summary_of_points", {})
    formatted_points = "\n".join(
        f"{nutrient}: {value}" for nutrient, value in nutrient_points.items()
    )
    return (
        f"Title: {recipe.get('recipe_title', 'Untitled Recipe')}\n"
        f"Processed Ingredients: {', '.join(recipe.get('processed_ingredients', []))}\n"
        f"Pure Ingredients: {', '.join(recipe.get('pure_ingredients', []))}\n"
        f"Instructions: {' '.join(recipe.get('step_by_step_instructions', []))}\n"
        f"Summary of Points:\n{formatted_points}\n"
        f"Cooking Time: {recipe.get('cooking_time', '')}\n"
        f"Required Tools: {', '.join(recipe.get('required_tools', []))}\n"
        f"Health Score: {recipe.get('total_health_score', 0)}\n"
    )


def get_generate_sys_prompt(
    recipes_file_path: str | Path,
    ingredients: Sequence[str],
    retriever_ingre: Any,
    retriever_recipe: Any,
    provide_example: bool = True,
    single_prompt: bool = False,
) -> str:
    """Build the balanced-recipe system prompt used by the active notebook."""
    normalized_ingredients = sorted(ingredient.lower() for ingredient in ingredients)

    sample_recipes_text = ""
    if provide_example:
        all_recipes = load_file_content(recipes_file_path)
        recipe_examples: list[str] = []
        similar_recipe_ids = retrieve_similar_recipe_id(
            retriever_recipe,
            normalized_ingredients,
        )
        for recipe_id in similar_recipe_ids:
            recipe = get_recipe_by_id(all_recipes, recipe_id)
            if recipe is not None:
                recipe_examples.append(_format_recipe_example(dict(recipe)))
        sample_recipes_text = "\n\n".join(recipe_examples)

    nutrient_map = [
        retrieve_food_and_nutrients(retriever_ingre, ingredient)[1]
        for ingredient in normalized_ingredients
    ]

    return f"""
    You are a culinary assistant specializing in generating single-serving, balanced recipes based on user preferences, available ingredients, and cooking tools.

    Here are some examples of balanced recipes:
    {f'sample recipes: {sample_recipes_text}' if provide_example else ''}

    Reference Material: Nutrient Map:
    {f'nutrient map: {nutrient_map}' if not single_prompt else ''}

    Generate a recipe following these guidelines:
    **Goals**:
    1. Create a recipe that satisfies all the listed **macronutrient requirements**. Adjust ingredient combinations and quantities as needed to meet these requirements:
      - Proteins: 10%-35% of total energy
      - Carbohydrates: 45%-65% of total energy
      - Sugars: < 10% of total energy
      - Sodium: < 2.5g
      - Fats: 15%-30% of total energy
      - Saturated Fats: <10% of total energy
      - Fibers: >12.5g
    2. Calculate the total macronutrient values using the **provided nutrient map**. (If there's no nutrient map provided, use your own interpreation to determine the nutrient map)
    3. Assign a **health score** from 0 to 7:
      - Each macronutrient that meets its requirement scores 1 point.
      - A score >3 is required for the recipe to be acceptable.

    **Constraint**:
    1. Ingredient Use:
      - Use only the ingredients provided by the user.
      - It is not mandatory to use all ingredients.
      - Suggest new ingredients only if the user-provided ones are insufficient to meet macronutrient requirements.
    2. Cooking Tools: Must adhere to user cooking tool requirements.
    3. Cooking Time: Ensure the recipe meets or is shorter than the user's preferred cooking time.
    4. Health Score: A recipe must achieve a health score greater than 3.
    5. Seriving size: The recipe must be designed for single-serving size.

    **Follow these steps to adjust**:
    1. Analyze the initial recipe for macronutrient balance.
    2. Double check carbohydrates and fiber. If they are low, increase whole grains or vegetables.
    3. If protein (especially from meat) exceeds the upper limit, scale it down and substitute with plant-based proteins or more vegetables.
    4. Reduce saturated fats by substituting with healthy fats (e.g., olive oil, nuts, seeds).
    5. Finalize the recipe and provide updated ingredients and instructions.

    The recipe also should follow *Consistency Guidelines**, that is to provide clear instructions with sufficient detail, including:
    - Specific temperatures (e.g., "heat to medium-high").
    - Times (e.g., "cook for 5-6 minutes").
    - Precise measurements for ingredients (e.g., "2 tablespoons of olive oil").

    The final output must have the following attributes:
    - **title**: Recipe title.
    - **processed_ingredients**: List of ingredients with measurement, including salt and pepper.
    - **pure_ingredients**: List of ingredients without measurements, **must exclude seasonings or oils**.
    - **instructions**: Step-by-step cooking instructions, numbered.
    - **required_tools**: List of tools needed for the recipe.
    - **cooking_time**: Total cooking time in minutes (only output the number).
    - **suggestions**: Suggestions for additional ingredients to meet macronutrient requirements, if applicable.

    **Final Output Rules**:
    1. Must be a string in **JSON format**encoded in UTF-8
    2. Exclude any code block markers (e.g., “json”)
    3. Include only the specified attributes, no extras.
    """


def build_user_prompt(
    ingredients: Sequence[str],
    tools: Sequence[str],
    time: int | str,
) -> str:
    """Build the short user prompt containing ingredients and constraints."""
    return (
        f"I have the following ingredients: {', '.join(ingredients)}.\n"
        f"I also have these cooking tools requirements: {', '.join(tools)}.\n"
        f"I prefer the cooking time to be within: {time} minutes.\n"
    )


def get_recipe(
    client: Any,
    ingredients: Sequence[str],
    tools: Sequence[str],
    time: int | str,
    temp: float,
    top_p: float,
    file_path: str | Path,
    *,
    retriever_nutrient: Any,
    retriever_recipe: Any,
    provide_example: bool = True,
    single_prompt: bool = False,
    model: str | None = None,
) -> str:
    """Generate a recipe and return the model's JSON text."""
    system_prompt = get_generate_sys_prompt(
        file_path,
        ingredients,
        retriever_nutrient,
        retriever_recipe,
        provide_example,
        single_prompt,
    )
    return get_API_response(
        client,
        system_prompt,
        build_user_prompt(ingredients, tools, time),
        temp,
        top_p,
        model=model,
    )


@dataclass
class RecipeGenerator:
    """Store shared clients and retrievers for repeated recipe generation."""

    client: Any
    nutrient_retriever: Any
    recipe_retriever: Any
    recipes_path: str | Path
    config: AppConfig | None = None

    def generate_text(
        self,
        ingredients: Sequence[str],
        tools: Sequence[str],
        time: int | str,
        *,
        temperature: float = 0.8,
        top_p: float = 1.0,
        provide_example: bool = True,
        single_prompt: bool = False,
    ) -> str:
        """Generate recipe JSON text for one user request."""
        settings = self.config or get_config()
        return get_recipe(
            self.client,
            ingredients,
            tools,
            time,
            temperature,
            top_p,
            self.recipes_path,
            retriever_nutrient=self.nutrient_retriever,
            retriever_recipe=self.recipe_retriever,
            provide_example=provide_example,
            single_prompt=single_prompt,
            model=settings.openai.chat_model,
        )

    def generate(
        self,
        ingredients: Sequence[str],
        tools: Sequence[str],
        time: int | str,
        **options: Any,
    ) -> GeneratedRecipe:
        """Generate and validate one recipe."""
        return parse_generated_recipe(
            self.generate_text(ingredients, tools, time, **options)
        )

