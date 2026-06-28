"""Ingredient-to-CNF food-code matching extracted from the notebook."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from recipeprep.retrieval.embeddings import generate_embeddings
from recipeprep.retrieval.preprocessing import preprocess_text
from recipeprep.schemas import FoodCodeMatch


def _normalized_description_segments(description: str) -> list[str]:
    """Split a CNF description into normalized comma-separated parts."""

    return [
        segment
        for segment in (preprocess_text(part) for part in description.split(","))
        if segment
    ]


def _contains_all_words(ingredient: str, description: str) -> bool:
    """Return whether every ingredient word appears in the CNF description."""

    ingredient_words = ingredient.split()
    if len(ingredient_words) < 2:
        return False
    description_words = set(description.split())
    return all(word in description_words for word in ingredient_words)


def _is_product_variant_for_single_word(ingredient: str, description: str) -> bool:
    """Avoid matching plain foods to oils or extracts too early."""

    ingredient_words = set(ingredient.split())
    if len(ingredient_words) != 1:
        return False
    product_words = {"oil", "extract"}
    description_words = set(preprocess_text(description).split())
    return bool(product_words & description_words) and not bool(
        product_words & ingredient_words
    )


def find_closest_food_code(
    client: Any,
    index: Any,
    ingredient: str,
    top_k: int = 30,
    *,
    food_descriptions: Sequence[str],
    food_codes: Sequence[int | str],
    food_descriptions_ori: Sequence[str],
    embedding_model: str | None = None,
) -> tuple[int | str | None, str | None, float]:
    """Return the best food code, description, and similarity for an ingredient."""

    normalized_ingredient = preprocess_text(ingredient)

    # Case 1: exact match against the full normalized CNF description.
    for idx, description in enumerate(food_descriptions):
        if normalized_ingredient == description:
            return food_codes[idx], food_descriptions_ori[idx], 1.0

    # Case 2: exact match against comma-separated CNF description segments.
    # Example: "almond" matches "Nuts, almonds, dried, unblanched, unroasted".
    segment_match: tuple[int, int | str, str] | None = None
    for idx, description_ori in enumerate(food_descriptions_ori):
        if _is_product_variant_for_single_word(normalized_ingredient, description_ori):
            continue
        segments = _normalized_description_segments(description_ori)
        if normalized_ingredient not in segments:
            continue
        segment_position = segments.index(normalized_ingredient)
        if segment_match is None or segment_position < segment_match[0]:
            segment_match = (segment_position, food_codes[idx], description_ori)
    if segment_match is not None:
        _, food_code, description_ori = segment_match
        return food_code, description_ori, 0.95

    # Case 3: conservative multi-word containment match.
    # Example: "all purpose flour" matches a longer CNF flour description.
    for idx, description in enumerate(food_descriptions):
        if _contains_all_words(normalized_ingredient, description):
            return food_codes[idx], food_descriptions_ori[idx], 0.9

    # Case 4: embed the ingredient and search the saved FAISS index.
    ingredient_embedding = generate_embeddings(
        client,
        [normalized_ingredient],
        model=embedding_model,
    )[0]
    search_k = min(top_k, len(food_descriptions))
    distances, indices = index.search(
        np.array([ingredient_embedding], dtype="float32"),
        k=search_k,
    ) # L2 distances

    priority_match: tuple[int | str, str, float] | None = None
    best_match: tuple[int | str, str, float] | None = None
    best_similarity = 0.0
    best_prio_similarity = 0.0
    first_part_empty = True


    """
    Core Logic:
        CNF descriptions often use comma-separated parts. 
        Prefer exact matches against the main description, then the second segment, before fallback.
    """
    for idx, distance in zip(indices[0], distances[0], strict=False):
        
        if idx < 0 or idx >= len(food_descriptions_ori):
            continue

        description_ori = food_descriptions_ori[idx].strip()

        # Smaller L2 distance = closer vectors
        similarity = 1 - float(distance) #simple match score
        if similarity < 0.5:
            continue

        second_part = None
        second_part_words: list[str] = []

        if "," in description_ori:
            parts = description_ori.lower().split(",")
            first_part = parts[0].strip() if parts else ""
            second_part = parts[1].strip() if len(parts) > 1 else ""
            second_part_words = preprocess_text(second_part).split()
        else:
            first_part = description_ori.lower()

        ingredient_words = normalized_ingredient.split()
        first_part_words = preprocess_text(first_part).split()

        if ingredient_words == first_part_words:
            if similarity > best_prio_similarity or (
                first_part_empty and best_prio_similarity - similarity < 0.1
            ):
                priority_match = (food_codes[idx], description_ori, similarity)
                best_prio_similarity = similarity
                first_part_empty = False
        elif second_part and ingredient_words == second_part_words:
            if similarity > best_prio_similarity:
                priority_match = (food_codes[idx], description_ori, similarity)
                best_prio_similarity = similarity

        if similarity > best_similarity:
            best_match = (food_codes[idx], description_ori, similarity)
            best_similarity = similarity

    # Check the best text-priority match first
    # otherwise use the closest remaining vector candidate above the score threshold.
    if priority_match:
        return priority_match
    if best_match:
        return best_match
    
    return None, None, 0.0


@dataclass
class IngredientMatcher:
    """Stores the client, index, and food data needed for repeated matching."""

    client: Any
    index: Any
    food_descriptions: Sequence[str]
    food_codes: Sequence[int | str]
    food_descriptions_ori: Sequence[str]
    top_k: int = 30
    embedding_model: str | None = None

    def find_closest_food_code(
        self,
        ingredient: str,
    ) -> tuple[int | str | None, str | None, float]:
        """Find the closest CNF food-code match for one ingredient."""

        return find_closest_food_code(
            self.client,
            self.index,
            ingredient,
            self.top_k,
            food_descriptions=self.food_descriptions,
            food_codes=self.food_codes,
            food_descriptions_ori=self.food_descriptions_ori,
            embedding_model=self.embedding_model,
        )


def get_food_code_for_ingredients(
    ingredients_list: Sequence[str],
    matcher: IngredientMatcher,
) -> dict[str, dict[str, int | str | float | None]]:
    """Match a list of ingredients and return results keyed by original name."""

    results_dict: dict[str, dict[str, int | str | float | None]] = {}
    for ingredient in ingredients_list:
        ingredient_cleaned = preprocess_text(ingredient)
        matched_food_code, matched_description, similarity = (
            matcher.find_closest_food_code(ingredient_cleaned)
        )
        match = FoodCodeMatch(
            food_code=matched_food_code,
            description=matched_description,
            similarity=similarity,
        )
        results_dict[ingredient] = match.model_dump()
        
    return results_dict
