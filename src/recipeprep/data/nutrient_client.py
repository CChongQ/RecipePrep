"""Download, build, load, and save Canadian Nutrient File data."""

from __future__ import annotations

import json
import logging
import random
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import requests

from recipeprep.config import AppConfig, get_config

LOGGER = logging.getLogger(__name__)

EVAL_NUTRIENTS = {
    "Protein",
    "Carbohydrate",
    "Sugars, total",
    "Sodium, Na",
    "Total Fat",
    "Fatty acids, saturated, total",
    "Fiber",
    "Fibre",
    "Calories",
    "Energy",
}


def _request_json(url: str, *, timeout: float) -> Any | None:
    """Request JSON data and return None when the CNF API call fails."""
    
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        LOGGER.error("CNF API request failed for %s: %s", url, error)
        return None


def get_nutrientamount_foodcode(
    food_code: int | str | None,
    *,
    config: AppConfig | None = None,
) -> list[dict[str, Any]] | None:
    """Get all nutrient amounts for one CNF food code."""
    
    settings = config or get_config()
    
    url = (
        f"{settings.cnf.base_url}{settings.cnf.nutrient_amount_endpoint}"
        f"?REQ_LANG={settings.cnf.language}&id={food_code}"
    )
    
    data = _request_json(url, timeout=settings.cnf.request_timeout_seconds)
    
    return data if isinstance(data, list) else None


def get_nutrientname_foodcode(
    nutrient_name_id: int | str,
    *,
    config: AppConfig | None = None,
) -> dict[str, Any] | None:
    """Get the name and unit for one CNF nutrient ID."""
    
    settings = config or get_config()
    
    url = (
        f"{settings.cnf.base_url}{settings.cnf.nutrient_name_endpoint}"
        f"?REQ_LANG={settings.cnf.language}&id={nutrient_name_id}"
    )
    data = _request_json(url, timeout=settings.cnf.request_timeout_seconds)
    return data if isinstance(data, dict) else None


def get_nut_map(
    in_foodCode: int | str | None,
    ingre_name: str,
    nutri_id_map: dict[str, Any],
    *,
    config: AppConfig | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Create the saved nutrient record for one matched ingredient."""
    
    settings = config or get_config()

    # fetch all nutrient amounts for the matched food code.
    map_data = get_nutrientamount_foodcode(in_foodCode, config=settings)
    if not map_data:
        return None, None

    nutrients: list[dict[str, Any]] = []
    current_unit_map = nutri_id_map
    for nutrient in map_data:
        nutrient_name = str(nutrient.get("nutrient_web_name", ""))

        # Keep only nutrients used by the health-scoring pipeline.
        if not any(name.lower() in nutrient_name.lower() for name in EVAL_NUTRIENTS):
            continue

        nutrient_id = str(nutrient["nutrient_name_id"])

        # Get unit
        if nutrient_id in current_unit_map:
            #Reuse cached units
            nutrient_unit = current_unit_map[nutrient_id]
        else:
            #call CNF once to look up the nutrient unit
            nutrient_data = get_nutrientname_foodcode(nutrient_id, config=settings)
            nutrient_unit = "g" if nutrient_data is None else nutrient_data["unit"]
            current_unit_map[nutrient_id] = nutrient_unit

        # Store a compact nutrient record for this ingredient.
        nutrients.append(
            {
                "value": nutrient["nutrient_value"],
                "nutrient_name": nutrient_name,
                "unit": nutrient_unit,
            }
        )

    return {
        "ingredient_name": ingre_name,
        "nutrients": nutrients,
    }, current_unit_map


def load_nut_id_map(unit_map_name: str | Path) -> dict[str, Any]:
    """Load the saved nutrient-unit lookup, or return an empty map."""
    unit_map_path = Path(unit_map_name)
    if not unit_map_path.exists():
        return {}
    with unit_map_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, dict) else {}


def save_nut_id_map(nut_id_map: dict[str, Any], unit_map_name: str | Path) -> None:
    """Save the nutrient-unit lookup as JSON."""
    unit_map_path = Path(unit_map_name)
    unit_map_path.parent.mkdir(parents=True, exist_ok=True)
    with unit_map_path.open("w", encoding="utf-8") as file:
        json.dump(nut_id_map, file, indent=4)
    LOGGER.info("Unit map saved to %s", unit_map_path)


def get_unitMap_name(*, config: AppConfig | None = None) -> Path:
    """Return the configured nutrient-unit map path."""
    return (config or get_config()).nutrient_unit_map_path


def save_nut_map(
    nuntri_unit_map: dict[str, Any],
    all_mapping: Sequence[dict[str, Any]],
    *,
    config: AppConfig | None = None,
) -> None:
    """Save both the nutrient-unit map and ingredient nutrient map."""
    settings = config or get_config()
    save_nut_id_map(nuntri_unit_map, settings.nutrient_unit_map_path)
    settings.nutrient_map_path.parent.mkdir(parents=True, exist_ok=True)
    with settings.nutrient_map_path.open("w", encoding="utf-8") as file:
        json.dump(list(all_mapping), file, indent=4)
    LOGGER.info("Ingredient nutrient map saved to %s", settings.nutrient_map_path)


def count_items_in_dataset(file_path: str | Path) -> int:
    """Return the number of top-level items in a JSON dataset."""
    with Path(file_path).open("r", encoding="utf-8") as file:
        dataset = json.load(file)
    return len(dataset)


def save_N_random_items(
    in_filename: str | Path,
    out_filename: str | Path,
    N: int,
) -> None:
    """Save up to N random items from a JSON list."""
    with Path(in_filename).open("r", encoding="utf-8") as file:
        data = json.load(file)

    if N > len(data):
        LOGGER.warning(
            "Requested %s items, but the dataset contains %s; selecting all items.",
            N,
            len(data),
        )
        N = len(data)

    output_path = Path(out_filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(random.sample(data, N), file, indent=4)
    LOGGER.info("Saved %s random items to %s", N, output_path)


def get_smaller_map(*, config: AppConfig | None = None, size: int = 1000) -> Path:
    """Save a small CNF file for local testing and return its path."""
    settings = config or get_config()
    output_path = settings.datasets_dir / "CNF_API_food_code_test.json"
    save_N_random_items(settings.cnf_food_code_path, output_path, size)
    return output_path
