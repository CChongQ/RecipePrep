"""LLM-assisted conversion of raw recipes into structured recipe records."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from recipeprep.config import get_config
from recipeprep.generation.prompts import RECIPE_PROCESS_PROMPT
from recipeprep.schemas import ProcessedRecipe, RawRecipe, RecipeProcessingOutput

LOGGER = logging.getLogger(__name__)


def get_API_response(
    client: Any,
    in_prompt: str,
    user_input: str,
    temp: float,
    topp: float,
    *,
    model: str | None = None,
) -> str:
    """Send a system prompt and user input to the configured model."""
    
    config = get_config()
    model_name = model or config.openai.chat_model
    LOGGER.info("Using model for recipe processing: %s", model_name)

    # Send the recipe-specific prompt to the chat model.
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": in_prompt},
            {"role": "user", "content": user_input},
        ],
        model=model_name,
        temperature=temp,
        top_p=topp,
    )
    response = chat_completion.choices[0].message.content
    if response is None:
        raise ValueError("The chat-completions API returned no message content.")

    # Return plain text for JSON parsing.
    return str(response)


def process_API_res_get_processed_recipe(
    API_resonse: str,
    recipe_id: str,
    eachRecipe: Mapping[str, Any],
) -> dict[str, Any]:
    """Turn the LLM JSON response into the processed recipe dictionary."""
    
    try:
        # Validate the LLM output schema.
        processed_res = RecipeProcessingOutput.model_validate_json(API_resonse)

        # Validate the source recipe metadata.
        raw_recipe = RawRecipe.model_validate(eachRecipe)
        
    except (ValidationError, ValueError, TypeError) as error:
        # Skip responses that cannot become a processed recipe.
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

    # Save each batch as a separate checkpoint file.
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (
        f"processed_recipes_{total_size}_batch_{batch_counter}.json"
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
    """Process a raw recipe dictionary and save valid results in JSON batches.
    """
    
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero.")

    config = get_config()

    # Use the default output folder unless one is provided.
    destination = (
        config.processed_recipes_dir
        if output_dir is None
        else config.resolve_path(output_dir)
    )

    out_list: list[dict[str, Any]] = []
    batch_counter = 0
    total_size = len(recipe_dataset)

    # Process each raw recipe with the same prompt template.
    for recipe_id, eachRecipe in recipe_dataset.items():
        
        # Validate required raw recipe fields.
        raw_recipe = RawRecipe.model_validate(eachRecipe)

        # Convert ingredient list into prompt text.
        ingredients_str = ". ".join(raw_recipe.ingredients)
        prompt_recipe_process = prompt_template.format(
            raw_recipe.title,
            ingredients_str,
            raw_recipe.instructions,
        )

        # Ask the model for structured recipe JSON.
        response = get_API_response(
            client,
            in_prompt=prompt_recipe_process,
            user_input="",
            temp=temp,
            topp=topp,
            model=model,
        )

        # Parse the response and attach source metadata.
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

        # Save a batch
        if len(out_list) >= batch_size:
            batch_counter += 1
            _save_recipe_batch(
                out_list,
                output_dir=destination,
                total_size=total_size,
                batch_counter=batch_counter,
            )
            out_list = []

    # Save any remaining recipes that did not fill a full batch.
    if out_list:
        batch_counter += 1
        _save_recipe_batch(
            out_list,
            output_dir=destination,
            total_size=total_size,
            batch_counter=batch_counter,
        )

    return batch_counter
