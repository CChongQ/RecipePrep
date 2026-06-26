"""Build recipe prompts and call the model to generate a recipe."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from recipeprep.config import AppConfig, get_config
from recipeprep.generation.prompts import RECIPE_GENERATION_SYSTEM_PROMPT
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
    model_name = model or config.openai.chat_model
    LOGGER.info("Using model for recipe generation: %s", model_name)

    # System prompt carries retrieved context; user prompt carries constraints.
    completion = client.chat.completions.create(
        model=model_name,
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
        f"Cooking Time: {recipe.get('cooking_time', '')}\n"
        f"Required Tools: {', '.join(recipe.get('required_tools', []))}\n"
        f"Summary of Points:\n{formatted_points}\n"
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
    """Build the balanced-recipe system prompt."""
    
    # Normalize and sort ingredients so retrieval queries are stable.
    normalized_ingredients = sorted(ingredient.lower() for ingredient in ingredients)

    sample_recipes_text = ""
    if provide_example:
        all_recipes = load_file_content(recipes_file_path)
        recipe_examples: list[str] = []

        # Few-shot context: retrieve similar filtered recipes by ingredient list.
        similar_recipe_ids = retrieve_similar_recipe_id(
            retriever_recipe,
            normalized_ingredients,
        )
        for recipe_id in similar_recipe_ids:
            # Map retrieved recipe IDs back to full saved recipe records.
            recipe = get_recipe_by_id(all_recipes, recipe_id)
            if recipe is not None:
                recipe_examples.append(_format_recipe_example(dict(recipe)))
        sample_recipes_text = "\n\n".join(recipe_examples)

    # Nutrient context: retrieve saved nutrient metadata for each user ingredient.
    nutrient_map = [
        retrieve_food_and_nutrients(retriever_ingre, ingredient)[1]
        for ingredient in normalized_ingredients
    ]

    sample_recipes_section = (
        f"sample recipes: {sample_recipes_text}" if provide_example else ""
    )
    nutrient_map_section = "" if single_prompt else f"nutrient map: {nutrient_map}"

    return RECIPE_GENERATION_SYSTEM_PROMPT.format(
        sample_recipes_section=sample_recipes_section,
        nutrient_map_section=nutrient_map_section,
    )

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
    
    # Build the RAG system prompt with optional few-shot recipes and nutrient context.
    system_prompt = get_generate_sys_prompt(
        file_path,
        ingredients,
        retriever_nutrient,
        retriever_recipe,
        provide_example,
        single_prompt,
    )
    
    # Add the user provided ingredients, tools, and time as the user prompt.
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

