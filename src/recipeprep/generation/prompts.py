"""Prompt templates used by RecipePrep generation and processing workflows."""

from __future__ import annotations

from importlib import resources

PROMPT_PACKAGE = "recipeprep.generation.prompt_text"


def load_prompt(filename: str) -> str:
    """Load a packaged Markdown prompt template."""
    prompt_file = resources.files(PROMPT_PACKAGE).joinpath(filename)
    return prompt_file.read_text(encoding="utf-8")


# Format with: recipe title, ingredient text, and instructions.
RECIPE_PROCESS_PROMPT = load_prompt("recipe_processing_system.md")

# Format with: sample_recipes_section and nutrient_map_section.
RECIPE_GENERATION_SYSTEM_PROMPT = load_prompt("recipe_generation_system.md")
