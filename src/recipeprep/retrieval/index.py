"""Download CNF food data and build or load its FAISS search index."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import requests  # type: ignore[import-untyped]

from recipeprep.config import AppConfig, get_config
from recipeprep.retrieval.preprocessing import preprocess_text

LOGGER = logging.getLogger(__name__)


def _load_faiss() -> Any:
    """Import FAISS only when an index operation needs it."""
    try:
        import faiss  # type: ignore[import-not-found]
    except ImportError as error:
        raise ImportError(
            "FAISS is required for index operations. Install project dependencies first."
        ) from error
    return faiss


def get_food_code_dataset(*, config: AppConfig | None = None) -> list[dict[str, Any]]:
    """Download the CNF food-code dataset and save it locally."""
    settings = config or get_config()
    url = (
        f"{settings.cnf.base_url}{settings.cnf.food_endpoint}"
        f"?lang={settings.cnf.language}&type=json"
    )
    response = requests.get(url, timeout=settings.cnf.request_timeout_seconds)
    response.raise_for_status()
    food_code_data = response.json()
    if not isinstance(food_code_data, list):
        raise ValueError("The CNF food-code response must be a list.")

    settings.cnf_food_code_path.parent.mkdir(parents=True, exist_ok=True)
    with settings.cnf_food_code_path.open("w", encoding="utf-8") as file:
        json.dump(food_code_data, file, indent=4)
    LOGGER.info("CNF food-code dataset saved to %s", settings.cnf_food_code_path)
    return food_code_data


def _load_food_code_dataset(path: Path) -> list[dict[str, Any]]:
    """Load and check the local CNF food-code dataset."""
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"Food-code dataset must be a list: {path}")
    return data


def get_normalized_foodCode_dataset(
    *,
    config: AppConfig | None = None,
) -> tuple[list[str], list[int | str]]:
    """Return normalized food descriptions and their matching food codes."""
    settings = config or get_config()
    food_code_dataset = _load_food_code_dataset(settings.cnf_food_code_path)
    descriptions = [
        preprocess_text(str(item["food_description"])) for item in food_code_dataset
    ]
    food_codes = [item["food_code"] for item in food_code_dataset]
    return descriptions, food_codes


def get_regular_foodCode_dataset(
    *,
    config: AppConfig | None = None,
) -> tuple[list[str], list[int | str]]:
    """Return original food descriptions and their matching food codes."""
    settings = config or get_config()
    food_code_dataset = _load_food_code_dataset(settings.cnf_food_code_path)
    descriptions = [str(item["food_description"]) for item in food_code_dataset]
    food_codes = [item["food_code"] for item in food_code_dataset]
    return descriptions, food_codes


def create_FAISS_Index(
    food_embeddings: np.ndarray[Any, np.dtype[np.floating[Any]]],
    *,
    output_path: str | Path | None = None,
    config: AppConfig | None = None,
) -> Any:
    """Build a flat L2 FAISS index, save it, and return it."""
    faiss = _load_faiss()
    if food_embeddings.ndim != 2:
        raise ValueError("food_embeddings must be a two-dimensional array.")

    settings = config or get_config()
    index_path = (
        settings.faiss_index_path if output_path is None else Path(output_path)
    )
    index = faiss.IndexFlatL2(food_embeddings.shape[1])
    index.add(food_embeddings)

    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
    LOGGER.info("FAISS index saved to %s", index_path)
    return index


def load_FAISS_Index(
    path: str | Path | None = None,
    *,
    config: AppConfig | None = None,
) -> Any:
    """Load a saved FAISS index from disk."""
    faiss = _load_faiss()
    settings = config or get_config()
    index_path = settings.faiss_index_path if path is None else Path(path)
    return faiss.read_index(str(index_path))
