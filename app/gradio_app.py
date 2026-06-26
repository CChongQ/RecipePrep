"""Standalone Gradio interface for RecipePrep."""

from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Sequence

from recipeprep.config import AppConfig, get_config
from recipeprep.generation import RecipeGenerator
from recipeprep.schemas import GeneratedRecipe
from recipeprep.retrieval import build_retrievers

LOGGER = logging.getLogger(__name__)


def parse_comma_separated(value: object) -> list[str]:
    """Split comma-separated UI text and remove empty items."""
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def parse_time_minutes(value: object) -> int:
    """Read the UI cooking-time value as a positive whole number."""
    if value is None or str(value).strip() == "":
        raise ValueError("Please enter a cooking time.")
    raw_value = str(value).strip()
    try:
        minutes = int(round(float(raw_value)))
    except (TypeError, ValueError) as error:
        raise ValueError("Cooking time must be a number.") from error
    if minutes <= 0:
        raise ValueError("Cooking time must be greater than zero.")
    return minutes


def _openai_client() -> Any:
    """Create the OpenAI client only when generation is requested."""
    try:
        from openai import OpenAI  # type: ignore[import-not-found]
    except ImportError as error:
        raise ImportError(
            "The OpenAI SDK is required. Install the project dependencies first."
        ) from error
    return OpenAI()


@dataclass(frozen=True)
class AppServices:
    """Services shared by every request handled by the app."""

    generator: RecipeGenerator


def _format_list(items: Sequence[object]) -> str:
    """Render a short Markdown bullet list."""

    values = [str(item).strip() for item in items if str(item).strip()]
    return "\n".join(f"- {item}" for item in values) or "None"


def _format_suggestions(suggestions: list[str] | str | None) -> str:
    """Normalize optional recipe suggestions for display."""

    if suggestions is None:
        return "None"
    if isinstance(suggestions, str):
        suggestions = [suggestions]
    return _format_list(suggestions)


def _strip_step_number(step: object) -> str:
    """Remove model-provided step numbers before Markdown adds its own."""

    return re.sub(r"^\s*\d+[\.)]\s*", "", str(step).strip())


def format_recipe_markdown(recipe: GeneratedRecipe) -> str:
    """Render a generated recipe as a user-friendly Markdown page."""

    cleaned_steps = [
        step for step in (_strip_step_number(item) for item in recipe.instructions) if step
    ]
    instructions = "\n".join(
        f"{index}. {step}" for index, step in enumerate(cleaned_steps, start=1)
    )
    return f"""# {recipe.title}

## Ingredients
{_format_list(recipe.processed_ingredients)}

## Tools
{_format_list(recipe.required_tools)}

## Cooking Time
{recipe.cooking_time} minutes

## Instructions
{instructions or "No instructions returned."}

## Suggestions
{_format_suggestions(recipe.suggestions)}
"""


def create_services(
    *,
    config: AppConfig | None = None,
    rebuild_indexes: bool = False,
) -> AppServices:
    """Create the model client, persistent retrievers, and recipe generator."""
    settings = config or get_config()
    recipes_path = settings.datasets_dir / "filtered_recipes_merged.json"
    if not recipes_path.is_file():
        raise FileNotFoundError(f"Recipe dataset not found: {recipes_path}")
    if not settings.nutrient_map_path.is_file():
        raise FileNotFoundError(
            f"Ingredient nutrient map not found: {settings.nutrient_map_path}"
        )

    retrievers = build_retrievers(
        recipes_path,
        settings.nutrient_map_path,
        rebuild=rebuild_indexes,
        config=settings,
    )
    return AppServices(
        generator=RecipeGenerator(
            client=_openai_client(),
            nutrient_retriever=retrievers.nutrient,
            recipe_retriever=retrievers.recipes,
            recipes_path=recipes_path,
            config=settings,
        )
    )


@lru_cache(maxsize=2)
def get_services(rebuild_indexes: bool = False) -> AppServices:
    """Create app services once and reuse them for later requests."""
    return create_services(rebuild_indexes=rebuild_indexes)


def generate_recipe(
    ingredients: object,
    tools: object,
    time: object,
    provide_example: bool,
    single_prompt: bool,
    progress: Any = None,
    *,
    services: AppServices | None = None,
) -> str:
    """Validate UI inputs and return generated recipe JSON text."""
    try:
        if progress is not None:
            progress(0.1, desc="Reading inputs")
        ingredient_list = parse_comma_separated(ingredients)
        if not ingredient_list:
            raise ValueError("Please enter at least one ingredient.")

        tool_list = parse_comma_separated(tools)
        time_minutes = parse_time_minutes(time)
        if progress is not None:
            progress(0.25, desc="Loading retrievers")
        app_services = services or get_services()

        if progress is not None:
            progress(0.55, desc="Generating recipe")
        recipe = app_services.generator.generate(
            ingredient_list,
            tool_list,
            time_minutes,
            temperature=0.8,
            top_p=1.0,
            provide_example=bool(provide_example),
            single_prompt=bool(single_prompt),
        )
        if progress is not None:
            progress(0.9, desc="Formatting recipe")
        return format_recipe_markdown(recipe)
    except Exception as error:
        LOGGER.exception("Recipe generation failed.")
        return f"Error: {error}"


def _load_gradio() -> Any:
    """Import Gradio only when the web application is built."""
    try:
        import gradio as gr  # type: ignore[import-not-found]
    except ImportError as error:
        raise ImportError(
            'Gradio is required. Install the app extras with: pip install -e ".[app]"'
        ) from error
    return gr


def _status_html(label: str, detail: str = "", *, active: bool = False) -> str:
    """Render the right-side generation status panel."""

    progress = (
        '<progress style="width: 100%; height: 12px; margin-top: 10px;"></progress>'
        if active
        else ""
    )
    return f"""
<div style="padding: 12px 14px; border-radius: 6px; border: 1px solid #ddd; background: #fafafa;">
  <strong>{label}</strong>
  <div style="margin-top: 6px; color: #555;">{detail}</div>
  {progress}
</div>
"""


def build_app(handler: Any = generate_recipe) -> Any:
    """Create and return the Gradio interface without launching it."""
    gr = _load_gradio()

    def run_generation(
        ingredients: object,
        tools: object,
        time: object,
        provide_example: bool,
        single_prompt: bool,
        progress: Any = gr.Progress(),
    ) -> Any:
        yield (
            _status_html("Generating recipe", "Preparing inputs and retrievers...", active=True),
            "",
        )
        result = handler(
            ingredients,
            tools,
            time,
            provide_example,
            single_prompt,
            progress,
        )
        if str(result).startswith("Error:"):
            yield _status_html("Generation failed", str(result)), result
        else:
            yield _status_html("Recipe ready", "Generation complete."), result

    def clear_outputs() -> tuple[str, str]:
        return _status_html("Ready", "Submit a request to generate a recipe."), ""

    with gr.Blocks(title="RecipePrep") as app:
        gr.Markdown("# RecipePrep")
        gr.Markdown(
            "Generate a personalized recipe from your ingredients, available tools, "
            "and preferred cooking time."
        )

        with gr.Row():
            with gr.Column(scale=1):
                ingredients_input = gr.Textbox(
                    label="Enter your ingredients",
                    placeholder="tomato, egg, rice",
                )
                tools_input = gr.Textbox(
                    label="Enter your available cooking tools",
                    placeholder="pan, stove",
                )
                time_input = gr.Number(
                    label="Preferred cooking time (minutes)",
                    value=30,
                    minimum=1,
                )
                provide_example_input = gr.Checkbox(
                    label="Provide example recipes",
                    value=True,
                )
                single_prompt_input = gr.Checkbox(
                    label="Use single-prompt format",
                    value=False,
                )
                with gr.Row():
                    clear_button = gr.Button("Clear")
                    submit_button = gr.Button("Generate", variant="primary")

            with gr.Column(scale=1):
                status_output = gr.HTML(
                    value=_status_html(
                        "Ready",
                        "Submit a request to generate a recipe.",
                    ),
                    label="Status",
                )
                recipe_output = gr.Markdown(label="Generated recipe")

        inputs = [
            ingredients_input,
            tools_input,
            time_input,
            provide_example_input,
            single_prompt_input,
        ]
        submit_button.click(
            fn=run_generation,
            inputs=inputs,
            outputs=[status_output, recipe_output],
            show_progress="full",
        )
        clear_button.click(
            fn=clear_outputs,
            inputs=None,
            outputs=[status_output, recipe_output],
        )

    return app

def build_parser() -> argparse.ArgumentParser:
    """Create command-line options for launching the app."""
    parser = argparse.ArgumentParser(description="Launch the RecipePrep Gradio app.")
    parser.add_argument("--host", default="127.0.0.1", help="Server host.")
    parser.add_argument("--port", type=int, default=7860, help="Server port.")
    parser.add_argument("--share", action="store_true", help="Create a public Gradio link.")
    parser.add_argument("--debug", action="store_true", help="Enable Gradio debug output.")
    parser.add_argument(
        "--rebuild-indexes",
        action="store_true",
        help="Rebuild the nutrient and recipe vector stores on first request.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Launch the Gradio application."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.rebuild_indexes:
        # Store this choice before Gradio handles its first request.
        
        get_services.cache_clear()

        def generate_with_rebuild(
            ingredients: object,
            tools: object,
            time: object,
            provide_example: bool,
            single_prompt: bool,
            progress: Any = None,
        ) -> str:
            return generate_recipe(
                ingredients,
                tools,
                time,
                provide_example,
                single_prompt,
                progress,
                services=get_services(True),
            )

        app = build_app(generate_with_rebuild)
    else:
        app = build_app()

    app.queue().launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        debug=args.debug,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
