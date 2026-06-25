"""Build, load, and query the nutrient and recipe vector stores."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from recipeprep.config import AppConfig, get_config

LOGGER = logging.getLogger(__name__)


def _langchain_types() -> tuple[Any, Any, Any]:
    """Load LangChain classes only when vector-store work is requested."""
    try:
        from langchain_chroma import Chroma  # type: ignore[import-not-found]
        from langchain_core.documents import Document  # type: ignore[import-not-found]
        from langchain_openai import OpenAIEmbeddings  # type: ignore[import-not-found]
    except ImportError as error:
        raise ImportError(
            "LangChain and Chroma dependencies are required for vector-store work."
        ) from error
    return Chroma, Document, OpenAIEmbeddings


def _retrieve_documents(retriever: Any, query: str) -> list[Any]:
    """Run a query with either the current or older LangChain retriever API."""
    if hasattr(retriever, "invoke"):
        results = retriever.invoke(query)
    else:
        results = retriever.get_relevant_documents(query)
    return list(results or [])


def nutrient_metadata(record: Mapping[str, Any]) -> dict[str, Any]:
    """Create searchable metadata for one ingredient nutrient record."""
    return {
        "ingredient_name": record.get("ingredient_name", ""),
        "nutrients": "".join(map(str, record.get("nutrients", []))),
    }


def recipe_metadata(record: Mapping[str, Any]) -> dict[str, Any]:
    """Create searchable metadata for one processed recipe."""
    pure_ingredients = record.get("pure_ingredients", [])
    ingredient_text = (
        ", ".join(pure_ingredients) if isinstance(pure_ingredients, list) else ""
    )
    return {
        "recipe_title": record.get("recipe_title", ""),
        "recipe_id": record.get("recipe_id", ""),
        "pure_ingredients": ingredient_text,
    }


def load_file_content(file_path: str | Path) -> list[dict[str, Any]]:
    """Load a JSON list"""
    path = Path(file_path)
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
        
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list: {path}")
    
    return data


def load_and_process_json(file_path: str | Path) -> list[dict[str, Any]]:
    """Convert recipe JSON records into page-content and metadata dictionaries."""
    
    processed_data: list[dict[str, Any]] = []

    # Chroma searches page_content; metadata keeps recipe IDs/titles for lookup.
    for recipe in load_file_content(file_path):
        metadata = recipe_metadata(recipe)
        processed_data.append(
            {
                "page_content": metadata["pure_ingredients"],
                "metadata": metadata,
            }
        )
    return processed_data


def _nutrient_documents(file_path: str | Path) -> list[Any]:
    """Create LangChain documents from the saved ingredient nutrient map."""
    
    _, Document, _ = _langchain_types()

    # Search by ingredient name, then return nutrient data from metadata.
    return [
        Document(
            page_content=str(record.get("ingredient_name", "")),
            metadata=nutrient_metadata(record),
        )
        for record in load_file_content(file_path)
    ]


def _recipe_documents(file_path: str | Path) -> list[Any]:
    """Create LangChain documents from processed recipe data."""
    
    _, Document, _ = _langchain_types()

    # Search by pure ingredient text, then return matching recipe metadata.
    return [
        Document(page_content=item["page_content"], metadata=item["metadata"])
        for item in load_and_process_json(file_path)
    ]


def _build_or_load_retriever(
    documents: Sequence[Any],
    *,
    persist_directory: Path,
    collection_name: str,
    top_k: int,
    config: AppConfig,
    rebuild: bool,
) -> Any:
    """Load an existing Chroma store or build it once from source documents."""
    
    Chroma, _, OpenAIEmbeddings = _langchain_types()

    # Use the configured OpenAI embedding model for both Chroma collections.
    embeddings = OpenAIEmbeddings(model=config.openai.embedding_model)
    has_saved_store = persist_directory.is_dir() and any(persist_directory.iterdir())

    # Reuse persisted Chroma data unless the caller explicitly rebuilds it.
    if has_saved_store and not rebuild:
        vectorstore = Chroma(
            collection_name=collection_name,
            persist_directory=str(persist_directory),
            embedding_function=embeddings,
        )
        LOGGER.info("Loaded vector store from %s", persist_directory)
    else:
        persist_directory.mkdir(parents=True, exist_ok=True)
        vectorstore = Chroma.from_documents(
            documents=list(documents),
            embedding=embeddings,
            collection_name=collection_name,
            persist_directory=str(persist_directory),
        )
        LOGGER.info("Built vector store at %s", persist_directory)

    # Expose the vector store through LangChain's retriever interface.
    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": top_k},
    )


def build_nutrient_retriever(
    nutrient_map_path: str | Path | None = None,
    *,
    persist_directory: str | Path | None = None,
    top_k: int | None = None,
    rebuild: bool = False,
    config: AppConfig | None = None,
) -> Any:
    """Build or load the retriever used for ingredient nutrient lookups."""
    
    settings = config or get_config()
    source_path = (
        settings.nutrient_map_path
        if nutrient_map_path is None
        else Path(nutrient_map_path)
    )
    store_path = (
        settings.nutrient_vectorstore_dir
        if persist_directory is None
        else Path(persist_directory)
    )
    
    # Convert the nutrient map JSON into searchable Chroma documents.
    documents = _nutrient_documents(source_path)
    
    return _build_or_load_retriever(
        documents,
        persist_directory=store_path,
        collection_name="recipeprep_nutrients",
        top_k=top_k or settings.retrieval.top_k,
        config=settings,
        rebuild=rebuild,
    )


def build_recipe_retriever(
    recipes_path: str | Path,
    *,
    persist_directory: str | Path | None = None,
    top_k: int | None = None,
    rebuild: bool = False,
    config: AppConfig | None = None,
) -> Any:
    """Build or load the retriever used to find similar recipes."""
    
    settings = config or get_config()
    store_path = (
        settings.recipe_vectorstore_dir
        if persist_directory is None
        else Path(persist_directory)
    )
    
    # Convert filtered recipes into searchable Chroma documents.
    documents = _recipe_documents(recipes_path)
    return _build_or_load_retriever(
        documents,
        persist_directory=store_path,
        collection_name="recipeprep_recipes",
        top_k=top_k or settings.retrieval.recipe_top_k,
        config=settings,
        rebuild=rebuild,
    )


def retrieve_food_and_nutrients(
    retriever: Any,
    query: str,
) -> tuple[str | None, Any | None]:
    """Return the closest ingredient name and its saved nutrient metadata."""
    
    # Use the top retrieved ingredient document as the nutrient match.
    results = _retrieve_documents(retriever, query)
    if not results:
        return None, None
    metadata = results[0].metadata
    
    return metadata.get("ingredient_name"), metadata.get("nutrients")


def retrieve_similar_recipe_id(
    retriever_recipe: Any,
    input_ingredients: Sequence[str],
) -> set[str]:
    """Return recipe IDs found for the sorted ingredient query."""
    
    # Sort ingredients so equivalent user input orders produce the same query.
    query = ",".join(sorted(input_ingredients))
    
    results = _retrieve_documents(retriever_recipe, query)
    recipe_ids = {
        str(document.metadata["recipe_id"])
        for document in results
        if document and document.metadata.get("recipe_id")
    }
    if not recipe_ids:
        LOGGER.info("No similar recipe found for: %s", query)
        
    return recipe_ids


def get_recipe_by_id(
    recipes: Sequence[Mapping[str, Any]],
    recipe_id: str,
) -> Mapping[str, Any] | None:
    """Find one recipe record by its recipe ID."""
    return next(
        (recipe for recipe in recipes if recipe.get("recipe_id") == recipe_id),
        None,
    )


@dataclass(frozen=True)
class RetrievalBundle:
    """The two retrievers needed by recipe generation."""

    nutrient: Any
    recipes: Any


def build_retrievers(
    recipes_path: str | Path,
    nutrient_map_path: str | Path | None = None,
    *,
    rebuild: bool = False,
    config: AppConfig | None = None,
) -> RetrievalBundle:
    """Build or load both project retrievers."""
    settings = config or get_config()

    # Build/load both stores used by recipe generation.
    return RetrievalBundle(
        nutrient=build_nutrient_retriever(
            nutrient_map_path,
            rebuild=rebuild,
            config=settings,
        ),
        recipes=build_recipe_retriever(
            recipes_path,
            rebuild=rebuild,
            config=settings,
        ),
    )
