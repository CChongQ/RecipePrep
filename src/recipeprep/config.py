"""Typed, side-effect-free configuration for RecipePrep."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml

DEFAULT_CONFIG_ENV = "RECIPEPREP_CONFIG"
PROJECT_ROOT_ENV = "RECIPEPREP_ROOT"


@dataclass(frozen=True)
class PathsConfig:
    raw_recipes: Path = Path("recipes_raw")
    datasets: Path = Path("datasets")
    processed_recipes: Path = Path("datasets/Processed_Recipes")
    test_data: Path = Path("datasets/testing")
    nutrient_maps: Path = Path("ingre_nutrition_map")
    artifacts: Path = Path("artifacts")
    embeddings: Path = Path("artifacts/embeddings")
    indexes: Path = Path("artifacts/indexes")
    reports: Path = Path("reports")


@dataclass(frozen=True)
class OpenAIConfig:
    chat_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    temperature: float = 0.0
    timeout_seconds: float = 60.0
    max_retries: int = 3


@dataclass(frozen=True)
class RetrievalConfig:
    top_k: int = 1
    chunk_size: int = 1000
    chunk_overlap: int = 200
    faiss_index_filename: str = "food_index.faiss"
    food_embeddings_filename: str = "food_embeddings.npy"
    description_embeddings_filename: str = "food_descriptions_embeddings.npy"


@dataclass(frozen=True)
class CnfConfig:
    base_url: str = "https://food-nutrition.canada.ca"
    language: str = "en"
    food_endpoint: str = "/api/canadian-nutrient-file/food/"
    nutrient_amount_endpoint: str = "/api/canadian-nutrient-file/nutrientamount/"
    nutrient_name_endpoint: str = "/api/canadian-nutrient-file/nutrientname/"
    request_timeout_seconds: float = 30.0
    food_code_filename: str = "CNF_API_food_code.json"
    nutrient_map_filename: str = "ingredient_nutrient_map.json"
    nutrient_unit_map_filename: str = "nutrient_unit_map.json"


@dataclass(frozen=True)
class PipelineConfig:
    random_seed: int = 42
    long_recipe_min_characters: int = 900


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"


@dataclass(frozen=True)
class AppConfig:
    project_root: Path
    paths: PathsConfig = field(default_factory=PathsConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    cnf: CnfConfig = field(default_factory=CnfConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def resolve_path(self, path: str | Path) -> Path:
        """Resolve a configured path relative to the project root."""
        candidate = Path(path).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()
        return (self.project_root / candidate).resolve()

    @property
    def raw_recipes_dir(self) -> Path:
        return self.resolve_path(self.paths.raw_recipes)

    @property
    def datasets_dir(self) -> Path:
        return self.resolve_path(self.paths.datasets)

    @property
    def processed_recipes_dir(self) -> Path:
        return self.resolve_path(self.paths.processed_recipes)

    @property
    def test_data_dir(self) -> Path:
        return self.resolve_path(self.paths.test_data)

    @property
    def nutrient_maps_dir(self) -> Path:
        return self.resolve_path(self.paths.nutrient_maps)

    @property
    def artifacts_dir(self) -> Path:
        return self.resolve_path(self.paths.artifacts)

    @property
    def embeddings_dir(self) -> Path:
        return self.resolve_path(self.paths.embeddings)

    @property
    def indexes_dir(self) -> Path:
        return self.resolve_path(self.paths.indexes)

    @property
    def reports_dir(self) -> Path:
        return self.resolve_path(self.paths.reports)

    @property
    def cnf_food_code_path(self) -> Path:
        return self.datasets_dir / self.cnf.food_code_filename

    @property
    def nutrient_map_path(self) -> Path:
        return self.nutrient_maps_dir / self.cnf.nutrient_map_filename

    @property
    def nutrient_unit_map_path(self) -> Path:
        return self.nutrient_maps_dir / self.cnf.nutrient_unit_map_filename

    @property
    def faiss_index_path(self) -> Path:
        return self.indexes_dir / self.retrieval.faiss_index_filename

    def ensure_output_directories(self) -> None:
        """Create writable output directories when a command explicitly requests them."""
        for directory in (
            self.datasets_dir,
            self.processed_recipes_dir,
            self.test_data_dir,
            self.nutrient_maps_dir,
            self.artifacts_dir,
            self.embeddings_dir,
            self.indexes_dir,
            self.reports_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def _discover_project_root() -> Path:
    configured_root = os.getenv(PROJECT_ROOT_ENV)
    if configured_root:
        return Path(configured_root).expanduser().resolve()

    candidates = [Path.cwd(), *Path.cwd().parents, Path(__file__).resolve().parents[2]]
    for candidate in candidates:
        if (candidate / "pyproject.toml").is_file():
            return candidate.resolve()
    return Path.cwd().resolve()


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with path.open("r", encoding="utf-8") as config_file:
        data = yaml.safe_load(config_file) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Configuration root must be a mapping: {path}")
    return data


def _section(data: Mapping[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"Configuration section '{name}' must be a mapping.")
    return value


def _deep_merge(base: dict[str, Any], overrides: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, Mapping):
            merged[key] = _deep_merge(current, value)
        else:
            merged[key] = value
    return merged


def _path_values(values: Mapping[str, Any]) -> dict[str, Any]:
    return {key: Path(value) for key, value in values.items()}


def load_config(
    config_path: str | Path | None = None,
    *,
    project_root: str | Path | None = None,
) -> AppConfig:
    """Load configuration from YAML, with environment overrides for runtime settings."""
    root = (
        Path(project_root).expanduser().resolve()
        if project_root is not None
        else _discover_project_root()
    )

    default_path = root / "configs" / "default.yaml"
    data = _load_yaml(default_path) if default_path.is_file() else {}

    selected_path = config_path or os.getenv(DEFAULT_CONFIG_ENV)
    if selected_path is not None:
        candidate = Path(selected_path).expanduser()
        config_file = candidate if candidate.is_absolute() else root / candidate
        resolved_config_file = config_file.resolve()
        if resolved_config_file != default_path.resolve():
            data = _deep_merge(data, _load_yaml(resolved_config_file))

    openai_values = _section(data, "openai")
    retrieval_values = _section(data, "retrieval")
    cnf_values = _section(data, "cnf")
    pipeline_values = _section(data, "pipeline")
    logging_values = _section(data, "logging")

    if chat_model := os.getenv("RECIPEPREP_CHAT_MODEL"):
        openai_values["chat_model"] = chat_model
    if embedding_model := os.getenv("RECIPEPREP_EMBEDDING_MODEL"):
        openai_values["embedding_model"] = embedding_model
    if log_level := os.getenv("RECIPEPREP_LOG_LEVEL"):
        logging_values["level"] = log_level

    return AppConfig(
        project_root=root,
        paths=PathsConfig(**_path_values(_section(data, "paths"))),
        openai=OpenAIConfig(**openai_values),
        retrieval=RetrievalConfig(**retrieval_values),
        cnf=CnfConfig(**cnf_values),
        pipeline=PipelineConfig(**pipeline_values),
        logging=LoggingConfig(**logging_values),
    )


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Return the process-wide configuration instance."""
    return load_config()
