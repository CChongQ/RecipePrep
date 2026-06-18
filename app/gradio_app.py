"""Standalone Gradio interface for RecipePrep."""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Sequence

from recipeprep.config import AppConfig, get_config
from recipeprep.generation import RecipeGenerator
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


def create_services(
    *,
    config: AppConfig | None = None,
    rebuild_indexes: bool = False,
) -> AppServices:
    """Create the model client, persistent retrievers, and recipe generator."""
    settings = config or get_config()
    recipes_path = settings.datasets_dir / "filtered_recipes_419.json"
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
    *,
    services: AppServices | None = None,
) -> str:
    """Validate UI inputs and return generated recipe JSON text."""
    try:
        ingredient_list = parse_comma_separated(ingredients)
        if not ingredient_list:
            raise ValueError("Please enter at least one ingredient.")

        tool_list = parse_comma_separated(tools)
        time_minutes = parse_time_minutes(time)
        app_services = services or get_services()

        return app_services.generator.generate_text(
            ingredient_list,
            tool_list,
            time_minutes,
            temperature=0.8,
            top_p=1.0,
            provide_example=bool(provide_example),
            single_prompt=bool(single_prompt),
        )
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


def build_app(handler: Any = generate_recipe) -> Any:
    """Create and return the Gradio interface without launching it."""
    gr = _load_gradio()
    return gr.Interface(
        fn=handler,
        inputs=[
            gr.Textbox(
                label="Enter your ingredients",
                placeholder="tomato, egg, rice",
            ),
            gr.Textbox(
                label="Enter your available cooking tools",
                placeholder="pan, stove",
            ),
            gr.Number(
                label="Preferred cooking time (minutes)",
                value=30,
                minimum=1,
            ),
            gr.Checkbox(label="Provide example recipes", value=True),
            gr.Checkbox(label="Use single-prompt format", value=False),
        ],
        outputs=gr.Code(label="Generated recipe", language="json"),
        title="RecipePrep",
        description=(
            "Generate a personalized recipe from your ingredients, available "
            "tools, and preferred cooking time."
        ),
    )


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
        ) -> str:
            return generate_recipe(
                ingredients,
                tools,
                time,
                provide_example,
                single_prompt,
                services=get_services(True),
            )

        app = build_app(generate_with_rebuild)
    else:
        app = build_app()

    app.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        debug=args.debug,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
