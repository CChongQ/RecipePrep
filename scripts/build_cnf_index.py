"""Build CNF description embeddings and the FAISS index."""

from __future__ import annotations

import argparse
import logging
from typing import Sequence

import numpy as np
from openai import OpenAI

from recipeprep.config import get_config
from recipeprep.retrieval import (
    batch_generate_embeddings,
    create_FAISS_Index,
    get_food_code_dataset,
    get_normalized_foodCode_dataset,
)


def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description="Create embeddings for CNF food descriptions and save a FAISS index."
    )
    parser.add_argument(
        "--download-food-codes",
        action="store_true",
        help="Download the CNF food-code file before building embeddings.",
    )
    parser.add_argument("--batch-size", type=int, default=400, help="Embedding batch size.")
    parser.add_argument("--model", default=None, help="Optional embedding model override.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run CNF embedding and index creation."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    config = get_config()
    config.ensure_output_directories()
    if args.download_food_codes:
        get_food_code_dataset(config=config)
        

    model_name = args.model or config.openai.embedding_model
    print(f"Using embedding model: {model_name}")

    #descriptions are normalized lowercased, stripped of punctuation, and lemmatized
    food_descriptions, _ = get_normalized_foodCode_dataset(config=config)
    
    #generates one embedding vector per description
    embeddings = batch_generate_embeddings(
        OpenAI(),
        food_descriptions,
        batch_size=args.batch_size,
        model=model_name,
    )
    embedding_array = np.asarray(embeddings, dtype="float32")
    embedding_path = (
        config.embeddings_dir / config.retrieval.description_embeddings_filename
    )
    np.save(embedding_path, embedding_array)
    
    #FAISS stores the vectors in a flat L2 index
    create_FAISS_Index(embedding_array, config=config)
    
    print(f"Saved embeddings to {embedding_path}")
    print(f"Saved FAISS index to {config.faiss_index_path}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

