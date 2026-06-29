"""Run the RecipePrep data-preparation pipeline end to end."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from recipeprep.config import AppConfig, get_config


@dataclass(frozen=True)
class PipelineStep:
    number: int
    name: str
    command: tuple[str, ...]
    required_inputs: tuple[Path, ...] = ()
    costly: bool = False


Runner = Callable[[Sequence[str]], int]


def _script_command(script_name: str, *args: str | Path | int | float) -> tuple[str, ...]:
    return (
        sys.executable,
        str(Path("scripts") / script_name),
        *(str(arg) for arg in args),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the RecipePrep setup pipeline using the existing scripts."
    )
    parser.add_argument("--from-step", type=int, default=1, help="First step to run. Default: 1.")
    parser.add_argument("--to-step", type=int, default=9, help="Last step to run. Default: 9.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the selected commands without running them or checking inputs.",
    )
    parser.add_argument(
        "--allow-costly",
        action="store_true",
        help="Allow steps that call OpenAI models, embeddings, or external APIs.",
    )
    parser.add_argument(
        "--download-food-codes",
        action="store_true",
        help="Download the CNF food-code file before building the CNF index.",
    )
    parser.add_argument(
        "--rebuild-indexes",
        action="store_true",
        help="Rebuild saved vector stores where supported.",
    )
    parser.add_argument("--sample-size", type=int, default=200, help="Recipe sample size.")
    parser.add_argument(
        "--long-recipe-percent",
        type=float,
        default=0.2,
        help="Fraction of sampled recipes that should be long recipes.",
    )
    parser.add_argument("--process-batch-size", type=int, default=50)
    parser.add_argument("--embedding-batch-size", type=int, default=400)
    parser.add_argument("--min-score", type=float, default=3)
    return parser


def build_steps(args: argparse.Namespace, config: AppConfig) -> list[PipelineStep]:
    raw_recipes = config.raw_recipes_dir / "recipes_raw_processed.json"
    sampled_recipes = config.datasets_dir / f"recipe_dataset_init_{args.sample_size}.json"
    ingredient_list = config.datasets_dir / "ingredient_list.json"
    food_code_matches = config.datasets_dir / "ingredient_food_code_matches.json"
    scored_recipes_dir = config.datasets_dir / "scored_recipes"
    filtered_recipes = config.datasets_dir / "filtered_recipes_merged.json"

    cnf_args: list[str | Path | int | float] = ["--batch-size", args.embedding_batch_size]
    if args.download_food_codes:
        cnf_args.append("--download-food-codes")

    retriever_args: list[str | Path | int | float] = ["--recipes", filtered_recipes]
    if args.rebuild_indexes:
        retriever_args.append("--rebuild")

    score_args: list[str | Path | int | float] = [
        "--input-dir",
        config.processed_recipes_dir,
        "--pattern",
        "processed_recipes_*.json",
        "--output-dir",
        scored_recipes_dir,
    ]
    if args.rebuild_indexes:
        score_args.append("--rebuild-retriever")

    return [
        PipelineStep(
            1,
            "Sample raw recipes",
            _script_command(
                "sample_recipes.py",
                "--input",
                raw_recipes,
                "--output",
                sampled_recipes,
                "--sample-size",
                args.sample_size,
                "--long-recipe-percent",
                args.long_recipe_percent,
            ),
            required_inputs=(raw_recipes,),
        ),
        PipelineStep(
            2,
            "Process sampled recipes",
            _script_command(
                "process_recipes.py",
                "--input",
                sampled_recipes,
                "--batch-size",
                args.process_batch_size,
            ),
            required_inputs=(sampled_recipes,),
            costly=True,
        ),
        PipelineStep(
            3,
            "Build CNF FAISS index",
            _script_command("build_cnf_index.py", *cnf_args),
            required_inputs=() if args.download_food_codes else (config.cnf_food_code_path,),
            costly=True,
        ),
        PipelineStep(
            4,
            "Collect processed ingredients",
            _script_command(
                "collect_ingredients.py",
                "--pattern",
                "processed_recipes_*.json",
                "--output",
                ingredient_list,
            ),
            required_inputs=(config.processed_recipes_dir,),
        ),
        PipelineStep(
            5,
            "Match ingredients to CNF food codes",
            _script_command(
                "match_ingredients.py",
                "--input",
                ingredient_list,
                "--output",
                food_code_matches,
            ),
            required_inputs=(ingredient_list, config.faiss_index_path),
            costly=True,
        ),
        PipelineStep(
            6,
            "Build ingredient nutrient map",
            _script_command("build_nutrient_map.py", "--input", food_code_matches),
            required_inputs=(food_code_matches,),
            costly=True,
        ),
        PipelineStep(
            7,
            "Score processed recipes",
            _script_command("score_recipes.py", *score_args),
            required_inputs=(config.processed_recipes_dir, config.nutrient_map_path),
            costly=True,
        ),
        PipelineStep(
            8,
            "Filter scored recipes",
            _script_command(
                "filter_recipes.py",
                "--input-dir",
                scored_recipes_dir,
                "--pattern",
                "scored_recipes_*.json",
                "--output",
                filtered_recipes,
                "--min-score",
                args.min_score,
            ),
            required_inputs=(scored_recipes_dir,),
        ),
        PipelineStep(
            9,
            "Build Chroma retrievers",
            _script_command("build_retrievers.py", *retriever_args),
            required_inputs=(filtered_recipes, config.nutrient_map_path),
            costly=True,
        ),
    ]


def selected_steps(
    steps: Sequence[PipelineStep],
    from_step: int,
    to_step: int,
) -> list[PipelineStep]:
    if from_step < 1 or to_step > len(steps) or from_step > to_step:
        raise ValueError(f"Step range must be between 1 and {len(steps)}.")
    return [step for step in steps if from_step <= step.number <= to_step]


def validate_step(step: PipelineStep) -> None:
    missing = [path for path in step.required_inputs if not path.exists()]
    if missing:
        missing_text = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Step {step.number} requires missing input(s): {missing_text}")


def print_step(step: PipelineStep) -> None:
    marker = " [costly]" if step.costly else ""
    print(f"[{step.number}] {step.name}{marker}")
    print("    " + " ".join(step.command))


def run_command(command: Sequence[str]) -> int:
    return subprocess.run(command, check=False).returncode


def run_pipeline(
    steps: Sequence[PipelineStep],
    *,
    dry_run: bool,
    allow_costly: bool,
    runner: Runner = run_command,
) -> int:
    for step in steps:
        print_step(step)
        if step.costly and not allow_costly and not dry_run:
            raise PermissionError(
                f"Step {step.number} may call paid model/API services. "
                "Rerun with --allow-costly to execute it."
            )
        if dry_run:
            continue
        validate_step(step)
        result = runner(step.command)
        if result != 0:
            return result
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = get_config()
    config.ensure_output_directories()
    steps = selected_steps(build_steps(args, config), args.from_step, args.to_step)
    return run_pipeline(steps, dry_run=args.dry_run, allow_costly=args.allow_costly)


if __name__ == "__main__":
    raise SystemExit(main())
