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
from recipeprep.retrieval.index import (
    create_FAISS_Index,
    get_food_code_dataset,
    get_normalized_foodCode_dataset,
    get_regular_foodCode_dataset,
    load_FAISS_Index,
)
from recipeprep.retrieval.preprocessing import preprocess_text

__all__ = [
    "IngredientMatcher",
    "batch_generate_embeddings",
    "create_FAISS_Index",
    "find_closest_food_code",
    "generate_embeddings",
    "get_food_code_dataset",
    "get_food_code_for_ingredients",
    "get_normalized_foodCode_dataset",
    "get_regular_foodCode_dataset",
    "load_FAISS_Index",
    "preprocess_text",
]
