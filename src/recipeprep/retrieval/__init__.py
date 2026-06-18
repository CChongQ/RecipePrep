"""Embedding, indexing, and retrieval."""

from recipeprep.retrieval.embeddings import (
    batch_generate_embeddings,
    generate_embeddings,
)
from recipeprep.retrieval.ingredient_matcher import (
    IngredientMatcher,
    find_closest_food_code,
    get_food_code_for_ingredients,
)
from recipeprep.retrieval.preprocessing import preprocess_text

__all__ = [
    "IngredientMatcher",
    "batch_generate_embeddings",
    "find_closest_food_code",
    "generate_embeddings",
    "get_food_code_for_ingredients",
    "preprocess_text",
]
