"""Build the ingredient nutrient map from matched CNF food codes."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Sequence

from recipeprep.config import get_config
from recipeprep.data import get_all_ingredient_mapping
from recipeprep.data.nutrient_client import get_unitMap_name, load_nut_id_map, save_nut_map


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Call the CNF API and build ingredient nutrient map files."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Ingredient food-code mapping. Default: datasets/ingredient_food_code_matches.json.",
    )
    return parser


def _load_matches(path: Path) -> dict[str, dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object of ingredient matches: {path}")
    return data


def main(argv: Sequence[str] | None = None) -> int:
    """Run ingredient-nutrient map creation."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    config = get_config()
    config.ensure_output_directories()
    input_path = (
        config.datasets_dir / "ingredient_food_code_matches.json"
        if args.input is None
        else config.resolve_path(args.input)
    )

    unit_map_path = get_unitMap_name(config=config)
    unit_map = load_nut_id_map(unit_map_path)
    
    nutrient_records, unit_map = get_all_ingredient_mapping(
        _load_matches(input_path),
        unit_map,
    )
    save_nut_map(unit_map, nutrient_records, config=config)
    
    print(f"Saved nutrient map to {config.nutrient_map_path}")
    
    # caches nutrient unit map, so repeated runs do not need to look up the same nutrient unit from the CNF API every time
    print(f"Saved nutrient unit map to {config.nutrient_unit_map_path}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
