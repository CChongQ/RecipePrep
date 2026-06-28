"""Embedding helpers extracted from the data-processing notebook."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from recipeprep.config import get_config

LOGGER = logging.getLogger(__name__)


def generate_embeddings(
    client: Any,
    food_descriptions: Sequence[str],
    *,
    model: str | None = None,
) -> list[list[float]]:
    """Create embeddings for one list of food descriptions."""

    config = get_config()
    model_name = model or config.openai.embedding_model
    LOGGER.debug("Using embedding model: %s", model_name)

    response = client.embeddings.create(
        model=model_name,
        input=list(food_descriptions),
    )
    return [item.embedding for item in response.data]


def batch_generate_embeddings(
    client: Any,
    food_descriptions: Sequence[str],
    batch_size: int = 400,
    *,
    model: str | None = None,
) -> list[list[float]]:
    """Create embeddings in smaller batches"""

    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero.")

    embeddings: list[list[float]] = []
    
    total_batches = (len(food_descriptions) + batch_size - 1) // batch_size
    
    for i in range(0, len(food_descriptions), batch_size):
        batch = list(food_descriptions[i : i + batch_size])
        
        print(f"Processing batch {i // batch_size + 1} of {total_batches}")
        embeddings.extend(generate_embeddings(client, batch, model=model))
        
    return embeddings

