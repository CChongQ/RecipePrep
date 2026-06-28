"""Embedding, indexing, and retrieval."""

from recipeprep.retrieval.embeddings import (
    batch_generate_embeddings,
    generate_embeddings,
)
from recipeprep.retrieval.index import (
    create_FAISS_Index,
    get_food_code_dataset,
    get_normalized_foodCode_dataset,
    get_regular_foodCode_dataset,
    load_FAISS_Index,
)
from recipeprep.retrieval.ingredient_matcher import (
    IngredientMatcher,
    find_closest_food_code,
    get_food_code_for_ingredients,
)
from recipeprep.retrieval.preprocessing import preprocess_text
from recipeprep.retrieval.vector_store import (
    RetrievalBundle,
    build_nutrient_retriever,
    build_recipe_retriever,
    build_retrievers,
    get_recipe_by_id,
    load_and_process_json,
    load_file_content,
    retrieve_food_and_nutrients,
    retrieve_similar_recipe_id,
)

__all__ = [
    "IngredientMatcher",
    "RetrievalBundle",
    "batch_generate_embeddings",
    "build_nutrient_retriever",
    "build_recipe_retriever",
    "build_retrievers",
    "create_FAISS_Index",
    "find_closest_food_code",
    "generate_embeddings",
    "get_food_code_dataset",
    "get_food_code_for_ingredients",
    "get_normalized_foodCode_dataset",
    "get_recipe_by_id",
    "get_regular_foodCode_dataset",
    "load_and_process_json",
    "load_file_content",
    "load_FAISS_Index",
    "preprocess_text",
    "retrieve_food_and_nutrients",
    "retrieve_similar_recipe_id",
]
