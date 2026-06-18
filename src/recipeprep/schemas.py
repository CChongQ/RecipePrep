"""Typed data contracts used across the RecipePrep pipeline."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RecipePrepModel(BaseModel):
    """Base model that accepts legacy records while validating known fields."""

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)


class Ingredient(RecipePrepModel):
    """One ingredient after its amount and unit have been parsed."""

    name: str
    quantity: float | None = None
    unit: str | None = None
    original_text: str | None = None


class Nutrient(RecipePrepModel):
    """One nutrient value, such as 2.0 grams of protein."""

    value: float
    nutrient_name: str
    unit: str


class IngredientNutrientRecord(RecipePrepModel):
    """All saved nutrient values for one ingredient."""

    ingredient_name: str
    nutrients: list[Nutrient]


class FoodCodeMatch(RecipePrepModel):
    """The CNF food-code match found for an ingredient."""

    food_code: int | str | None = None
    description: str | None = None
    similarity: float = 0.0


class RawRecipe(RecipePrepModel):
    """A recipe in the original source-data format."""

    title: str
    ingredients: list[str]
    instructions: str
    picture_link: str | None = None


class RecipeProcessingOutput(RecipePrepModel):
    """The JSON fields returned by the recipe-processing LLM call."""

    step_by_step_instructions: list[str]
    processed_ingredients: list[str]
    pure_ingredients: list[str]
    cooking_time: str
    required_tools: list[str]


class ProcessedRecipe(RecipeProcessingOutput):
    """A structured recipe plus its original source fields and optional score."""

    recipe_id: str
    recipe_title: str
    original_instructions: str
    ingredients: list[str]
    total_health_score: int | None = Field(default=None, ge=0, le=7)
    summary_of_points: dict[str, int] | None = None


class GeneratedRecipe(RecipePrepModel):
    """A new recipe returned by the recipe-generation workflow."""

    title: str
    processed_ingredients: list[str]
    pure_ingredients: list[str]
    instructions: list[str]
    required_tools: list[str]
    cooking_time: int | str
    suggestions: list[str] | str | None = None


class UserPreferences(RecipePrepModel):
    """Ingredients, tools, time, and other limits supplied by the user."""

    available_ingredients: list[str]
    available_tools: list[str] = Field(default_factory=list)
    max_cooking_time_minutes: int | None = Field(default=None, gt=0)
    cooking_requirements: list[str] = Field(default_factory=list)


class HealthScoreResult(RecipePrepModel):
    """The total health score and the point given for each nutrient."""

    total_health_score: int = Field(ge=0, le=7)
    summary_of_points: dict[str, int]


class RelevanceResult(RecipePrepModel):
    """Checks for tool, time, and ingredient fit."""

    cooking_tools: bool
    cooking_time: int = Field(ge=0)
    ingredient_overlap_rate: float = Field(ge=0, le=100)


class EvaluationResult(RecipePrepModel):
    """Groups all available evaluation results for one recipe."""

    health: HealthScoreResult | None = None
    relevance: RelevanceResult | None = None
    consistency: dict[str, Any] | None = None
