"""LLM-assisted conversion of raw recipes into structured recipe records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from pydantic import ValidationError

from recipeprep.config import get_config
from recipeprep.generation.prompts import RECIPE_PROCESS_PROMPT
from recipeprep.schemas import ProcessedRecipe, RawRecipe, RecipeProcessingOutput


def get_API_response(
    client: Any,
    in_prompt: str,
    user_input: str,
    temp: float,
    topp: float,
    *,
    model: str | None = None,
) -> str:
    """Send a system prompt and user input to the configured chat model."""
    config = get_config()
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": in_prompt},
            {"role": "user", "content": user_input},
        ],
        model=model or config.openai.chat_model,
        temperature=temp,
        top_p=topp,
    )
    response = chat_completion.choices[0].message.content
    if response is None:
        raise ValueError("The chat-completions API returned no message content.")
    return str(response)


def process_API_res_get_processed_recipe(
    API_resonse: str,
    recipe_id: str,
    eachRecipe: Mapping[str, Any],
) -> dict[str, Any]:
    """Turn the LLM JSON response into the processed recipe dictionary."""
    try:
        processed_res = RecipeProcessingOutput.model_validate_json(API_resonse)
        raw_recipe = RawRecipe.model_validate(eachRecipe)
    except (ValidationError, ValueError, TypeError) as error:
        print(f"Error: {error}")
        print(API_resonse)
        return {}

    processed_recipe = ProcessedRecipe(
        recipe_id=recipe_id,
        recipe_title=raw_recipe.title,
        original_instructions=raw_recipe.instructions,
        ingredients=raw_recipe.ingredients,
        **processed_res.model_dump(),
    )
    return processed_recipe.model_dump(exclude_none=True)


def _save_recipe_batch(
    recipes: list[dict[str, Any]],
    *,
    output_dir: Path,
    total_size: int,
    batch_counter: int,
) -> Path:
    """Save one processed recipe batch and return its file path."""

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (
        f"processed_recipes_init_{total_size}_batch_{batch_counter}.json"
    )
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(recipes, file, indent=4)
    print(f"Intially Processed Recipe dataset has been saved in {output_path}")
    return output_path


def get_processed_recipe_dataset(
    client: Any,
    temp: float,
    topp: float,
    recipe_dataset: Mapping[str, Mapping[str, Any]],
    batch_size: int = 50,
    *,
    prompt_template: str = RECIPE_PROCESS_PROMPT,
    output_dir: str | Path | None = None,
    model: str | None = None,
) -> int:
    """Process a raw recipe dictionary and save valid results in JSON batches."""
    
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero.")

    config = get_config()
    destination = (
        config.processed_recipes_dir
        if output_dir is None
        else config.resolve_path(output_dir)
    )

    out_list: list[dict[str, Any]] = []
    batch_counter = 0
    total_size = len(recipe_dataset)

    # Process each source recipe with the same prompt and output format.
    for recipe_id, eachRecipe in recipe_dataset.items():
        raw_recipe = RawRecipe.model_validate(eachRecipe)
        ingredients_str = ". ".join(raw_recipe.ingredients)
        prompt_recipe_process = prompt_template.format(
            raw_recipe.title,
            ingredients_str,
            raw_recipe.instructions,
        )
        response = get_API_response(
            client,
            in_prompt=prompt_recipe_process,
            user_input="",
            temp=temp,
            topp=topp,
            model=model,
        )

        processed_recipe = process_API_res_get_processed_recipe(
            response,
            recipe_id,
            eachRecipe,
        )
        if not processed_recipe:
            print(
                f"Empty JSON detected. {recipe_id}: "
                f"{raw_recipe.title} is not a regular dish."
            )
        else:
            out_list.append(processed_recipe)

        # Save a full batch so a long run does not keep everything in memory.
        if len(out_list) >= batch_size:
            batch_counter += 1
            _save_recipe_batch(
                out_list,
                output_dir=destination,
                total_size=total_size,
                batch_counter=batch_counter,
            )
            out_list = []

    # Save the last partial batch, if there is one.
    if out_list:
        batch_counter += 1
        _save_recipe_batch(
            out_list,
            output_dir=destination,
            total_size=total_size,
            batch_counter=batch_counter,
        )

    return batch_counter
