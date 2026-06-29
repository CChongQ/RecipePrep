from pathlib import Path
from types import SimpleNamespace

import pytest

from recipeprep.config import load_config
from scripts.run_pipeline import build_steps, run_pipeline, selected_steps


def pipeline_args(**overrides):
    values = {
        "sample_size": 200,
        "long_recipe_percent": 0.2,
        "process_batch_size": 50,
        "embedding_batch_size": 400,
        "min_score": 3,
        "download_food_codes": False,
        "rebuild_indexes": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_selected_steps_respects_range(tmp_path: Path) -> None:
    config = load_config(project_root=tmp_path)
    steps = build_steps(pipeline_args(), config)

    selected = selected_steps(steps, 4, 6)

    assert [step.number for step in selected] == [4, 5, 6]


def test_dry_run_does_not_require_inputs_or_allow_costly(tmp_path: Path) -> None:
    config = load_config(project_root=tmp_path)
    steps = build_steps(pipeline_args(), config)
    calls: list[list[str]] = []

    result = run_pipeline(
        selected_steps(steps, 1, 3),
        dry_run=True,
        allow_costly=False,
        runner=lambda command: calls.append(list(command)) or 0,
    )

    assert result == 0
    assert calls == []


def test_costly_steps_require_explicit_opt_in(tmp_path: Path) -> None:
    config = load_config(project_root=tmp_path)
    steps = build_steps(pipeline_args(), config)

    with pytest.raises(PermissionError, match="allow-costly"):
        run_pipeline(selected_steps(steps, 2, 2), dry_run=False, allow_costly=False)


def test_pipeline_stops_when_required_input_is_missing(tmp_path: Path) -> None:
    config = load_config(project_root=tmp_path)
    steps = build_steps(pipeline_args(), config)

    with pytest.raises(FileNotFoundError, match="requires missing input"):
        run_pipeline(selected_steps(steps, 1, 1), dry_run=False, allow_costly=True)


def test_pipeline_runs_commands_in_order_when_inputs_exist(tmp_path: Path) -> None:
    config = load_config(project_root=tmp_path)
    raw_path = config.raw_recipes_dir / "recipes_raw_processed.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("{}", encoding="utf-8")
    calls: list[list[str]] = []

    result = run_pipeline(
        selected_steps(build_steps(pipeline_args(), config), 1, 1),
        dry_run=False,
        allow_costly=True,
        runner=lambda command: calls.append(list(command)) or 0,
    )

    assert result == 0
    assert len(calls) == 1
    assert calls[0][1].endswith(str(Path("scripts") / "sample_recipes.py"))
