# RecipePrep

RecipePrep is a GPT-4o-powered personalized recipe generator that **helps users turn available ingredients into practical, balanced meals**. Users provide ingredients, cooking tools, and time constraints, and the app generates a tailored recipe with clear step-by-step instructions.

To make nutrient calculation and recipe guidance more reliable, the system grounds ingredient nutrition data in the Canadian Nutrient File (CNF), scores recipes with deterministic nutrition rules, and uses few-shot retrieval to provide the model with similar filtered recipes as examples.

RecipePrep includes the full pipeline for recipe processing, nutrient matching, health scoring, retrieval, evaluation, and interactive generation through a Gradio app.


This guide explains how to run the current project and how each part works.

## Table of Contents

- [1. Project flow](#1-project-flow)
- [2. Important directories](#2-important-directories)
- [3. Data sources](#3-data-sources)
- [4. Installation](#4-installation)
- [5. API key setup](#5-api-key-setup)
- [6. Configuration](#6-configuration)
- [7. Quick start using existing project data](#7-quick-start-using-existing-project-data)
- [8. Full pipeline rebuild](#8-full-pipeline-rebuild)
- [9. Recipe evaluation](#9-recipe-evaluation)
- [10. Tests and quality checks](#10-tests-and-quality-checks)

## 1. Project flow

The project has two main phases: setup and generation. 

During setup, the project builds the processed recipe data, nutrient map, health scores, and retrieval indexes. 

During generation, the app uses those prepared artifacts to create and evaluate personalized recipes.

```text
Raw recipe data + CNF nutrition data
    |
    v
Process recipes and match ingredients to CNF food codes
    |
    v
Build ingredient nutrient map and health scores
    |
    v
Filter balanced recipes and build retrieval indexes
    |
    v
Generate a personalized recipe from user ingredients, tools, and time
    |
    v
Evaluate health, relevance, and consistency
```

## 2. Important directories

```text
app/                    Gradio web app for interactive recipe generation
configs/                Project settings, model choices, paths, and thresholds
scripts/                Command-line entry points for setup, generation, and evaluation
src/recipeprep/         Main Python package with data, retrieval, nutrition, generation, and evaluation logic

datasets/               Recipe datasets created or used by the pipeline
recipes_raw/            Original raw recipe files
ingre_nutrition_map/    Ingredient-to-nutrient maps built from CNF data
artifacts/              Generated embeddings, vector stores, indexes, and outputs
tests/                  Automated tests
```

## 3. Data sources

This project uses two external data sources:

### RecipeBox recipe data

Source: [RecipeBox](https://eightportions.com/datasets/Recipes/)

It is used as the raw recipe source for sampling, recipe processing, health scoring, filtering, and few-shot recipe examples.


### Canadian Nutrient File nutrition data

Source: [Canadian Nutrient File (CNF)](https://produits-sante.canada.ca/api/documentation/cnf-documentation-en.html#a6)

It is the reference source used to ground ingredient nutrition data. This project uses CNF food codes, food descriptions, nutrient amounts, and nutrient units to build the ingredient nutrient map used for health scoring and generation context.

To download a fresh local copy of the CNF food-code dataset used later for ingredient matching:

```python
from recipeprep.retrieval import get_food_code_dataset

food_codes = get_food_code_dataset()
print(len(food_codes))
```

## 4. Installation

Python 3.11 or 3.12 is recommended.

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Or activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

Then upgrade pip:

```powershell
python -m pip install --upgrade pip
```

Install the full project for app, notebook, and development use:

```powershell
python -m pip install -e ".[app,notebooks,dev]"
python -m nltk.downloader wordnet omw-1.4
```

For package and pipeline use only, install the minimal package:

```powershell
python -m pip install -e .
python -m nltk.downloader wordnet omw-1.4
```

The editable install (`-e`) lets scripts, notebooks, tests, and the app import `recipeprep` from the local source code.

## 5. API key setup

RecipePrep currently uses *OpenAI models* by default for recipe processing, embeddings, vector-store creation, and recipe generation. Other model providers would require adapting the chat and embedding clients.


Set your OpenAI API key before running scripts or the app.

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="your-key"
```

macOS/Linux:

```bash
export OPENAI_API_KEY="your-key"
```

## 6. Configuration

The default settings are in `configs/default.yaml`.

Important settings include:

- `openai.chat_model`: model used to process and generate recipes;
- `openai.embedding_model`: model used for retrieval embeddings;
- `retrieval.top_k`: nutrient matches returned per query;
- `retrieval.recipe_top_k`: similar recipes returned per query;
- `nutrition.*`: health-score thresholds;
- `paths.*`: datasets, indexes, reports, and nutrient-map directories.

Paths are resolved from the project root.

To use another configuration:

```powershell
$env:RECIPEPREP_CONFIG="configs/evaluation.yaml"
```

Other supported overrides:

```text
RECIPEPREP_ROOT
RECIPEPREP_CONFIG
RECIPEPREP_CHAT_MODEL
RECIPEPREP_EMBEDDING_MODEL
RECIPEPREP_LOG_LEVEL
OPENAI_API_KEY
```

## 7. Quick start using existing project data

Follow below steps when the prepared project artifacts already exist (Or you already completed Section 8 Step 1-9) and you want to generate recipes without rebuilding the full pipeline.

Expected files:

- `datasets/filtered_recipes_merged.json`;
- `ingre_nutrition_map/ingredient_nutrient_map.json`;
- `ingre_nutrition_map/nutrient_unit_map.json`.

### 7.1 Run the Gradio UI

Start the app:

```powershell
python app/gradio_app.py
```

Open the local URL printed in the terminal, by default:

```text
http://127.0.0.1:7860
```

In the UI, the user can provide available ingredients, cooking tools, cooking time, and whether retrieved example recipes should be included in the prompt.

On the first recipe request, the app creates the OpenAI client, loads or builds the nutrient and recipe Chroma stores, then generates the recipe. Later requests reuse the loaded services and saved stores.

To force both Chroma stores to be rebuilt:

```powershell
python app/gradio_app.py --rebuild-indexes
```

Other app options:

```powershell
python app/gradio_app.py --host 0.0.0.0 --port 7860
python app/gradio_app.py --share
python app/gradio_app.py --debug
```

### 7.2 Quick command-line generation

Use this as a smoke test if you want to check generation without opening the UI:

```powershell
python scripts/generate_recipe.py `
  --recipes datasets/filtered_recipes_merged.json `
  --ingredients tomato egg rice `
  --tools pan stove `
  --time 30
```

## 8. Full pipeline rebuild

The following sections describe how to rebuild the project from raw data. Steps 1-9 are setup and data-preparation steps. They usually only need to be **run once** when rebuilding the project from raw data or refreshing generated artifacts.

**Important Note!**: Please remember to choose model settings based on your requirement and budget. The scripts below use OpenAI models by default.

The easiest way to rebuild or resume the setup pipeline is to use the pipeline runner. It prints and runs the same scripts shown in the manual steps below.

**Preview the full rebuild without running anything**:

```powershell
python scripts/run_pipeline.py --from-step 1 --to-step 9 --dry-run
```

**Run the full rebuild**:

```powershell
python scripts/run_pipeline.py --from-step 1 --to-step 9 --allow-costly
```

Resume from a later step after fixing an input or reviewing an output:

```powershell
python scripts/run_pipeline.py --from-step 7 --to-step 9 --allow-costly
```

Useful options:

- `--dry-run`: print selected commands without running them.
- `--from-step` and `--to-step`: run only part of the setup pipeline.
- `--allow-costly`: required for steps that call OpenAI models, embeddings, or external APIs.
- `--download-food-codes`: download the CNF food-code file before building the CNF index.
- `--rebuild-indexes`: rebuild saved vector stores where supported.
- `--sample-size`, `--process-batch-size`, `--embedding-batch-size`, and `--min-score`: adjust common pipeline settings.

### 8.1 Recipe dataset preparation

#### Step 1: Sample raw recipes

The original RecipeBox file is large, so we choose to create a smaller **balanced sample dataset** for this project. 

In this example, the input recipe file from RecipeBox is `recipes_raw/recipes_raw_processed.json` and the output sample has 200 recipes.

```powershell
python scripts/sample_recipes.py `
  --input recipes_raw/recipes_raw_processed.json `
  --output datasets/recipe_dataset_init_200.json `
  --sample-size 200 `
  --long-recipe-percent 0.2
```

The sampler keeps only valid recipes. Recipes already in `datasets/Processed_Recipes/` are skipped to reduce repetitive processing. 

A "long" recipe is defined by `long_recipe_min_characters` in config file, and `--long-recipe-percent` controls the long/short split for balanced output.

#### Step 2: Convert raw recipes to structured recipes

This step uses an LLM to convert paragraph-style recipe instructions into **structured recipe** fields. 

Choose the right model in the config based on your budget and quality needs before running it.

```powershell
python scripts/process_recipes.py `
  --input datasets/recipe_dataset_init_200.json `
  --batch-size 50 `
  --temperature 0.2 `
  --top-p 1.0
```

Processed batches are saved under the configured `processed_recipes` directory. By default, this is `datasets/Processed_Recipes/`.

### 8.2 Nutrient data preparation

#### Step 3: Build the CNF embedding and FAISS index

This stage creates embeddings for every CNF food description, which will be used for ingredient-nutrient search.  

```powershell
python scripts/build_cnf_index.py --batch-size 400
```

If the local CNF food-code file has not been created yet, add `--download-food-codes`.


#### Step 4: Collect unique processed ingredients

Collect unique ingredient names from processed recipe batches

```powershell
python scripts/collect_ingredients.py `
  --pattern processed_recipes_init*.json `
  --output datasets/ingredient_list.json
```

#### Step 5: Match ingredients to CNF food codes

This step maps each unique processed ingredient to the closest Canadian Nutrient File (CNF) food code.

The matcher works in four stages:

1. Normalize the ingredient name and try an **exact match** against normalized CNF food descriptions.
2. Check CNF comma-separated description parts, so names like `almond` can match `Nuts, almonds, dried...`.
3. Use conservative word matching for multi-word ingredients
4. If no text match is found, compare the ingredient embedding with saved CNF description embeddings and use the **closest candidate**.

```powershell
python scripts/match_ingredients.py `
  --input datasets/ingredient_list.json `
  --output datasets/ingredient_food_code_matches.json
```

*Optional check*: Food names can have many variations or nicknames, so matches may not be 100% correct. Review the output file and manually correct matches if needed before making Step 6 nutrient API calls.


#### Step 6: Build the ingredient nutrient map

This step uses the **matched CNF food codes** to call the CNF nutrient API and build
an ingredient-to-nutrients map.

Only nutrients used by the evaluation pipeline are kept: **protein, carbohydrate, sugar, sodium, fat, saturated fat, fiber, and energy**.

```powershell
python scripts/build_nutrient_map.py `
  --input datasets/ingredient_food_code_matches.json
```

Each saved ingredient record contains nutrient names, values, and units.

### 8.3 Scoring and retrieval setup

#### Step 7: Score processed recipes

This step uses the ingredient nutrient map to calculate a **health score** for each processed recipe. The score is later used to filter recipes before building the recipe retriever.


```powershell
python scripts/score_recipes.py `
  --input-dir datasets/Processed_Recipes `
  --pattern "processed_recipes_*.json" `
  --output-dir datasets/scored_recipes
```

Use `--rebuild-retriever` when the ingredient nutrient map or nutrient retriever metadata has changed.

**Scoring rules**:

| Metric | Rule |
|---|---|
| Protein | 10-35% of total energy |
| Carbohydrates | 45-65% of total energy |
| Sugars | At most 10% of total energy |
| Sodium | At most 2,500 mg |
| Fat | 15-30% of total energy |
| Saturated fat | At most 10% of total energy |
| Fiber | At least 12.5 g |

`total_health_score` is the sum of all nutrition metric points. Each metric gets 1 if it meets the rule and 0 if it does not. For example, if 3 out of 7 metrics meet the rules, the total health score is 3.

Example output:

```json
{
  "total_health_score": 3,
  "summary_of_points": {
    "Proteins": 0,
    "Carbohydrates": 0,
    "Sugars": 1,
    "Sodium": 0,
    "Fats": 0,
    "Saturated Fats": 1,
    "Fibers": 1
  }
}
```


#### Step 8: Filter and merge scored recipes

Filter scored recipes before building the recipe retriever. By default, filtering uses `total_health_score`, so the recipe retriever is built from the healthy recipe set.

```powershell
python scripts/filter_recipes.py `
  --input-dir datasets/scored_recipes `
  --pattern "scored_recipes_*.json" `
  --output datasets/filtered_recipes_merged.json `
  --min-score 3
```

Useful args:

- `--strict`: fail instead of skipping recipes with missing or invalid scores.
- `--score-field`: filter using another score field.

#### Step 9: Build persistent Chroma retrievers

This step builds the saved Chroma vector stores used by recipe generation. 

The **nutrient retriever** searches ingredient names, and the **recipe retriever** searches pure ingredient lists from filtered recipes.

```powershell
python scripts/build_retrievers.py `
  --recipes datasets/filtered_recipes_merged.json `
  --rebuild
```

Use `--rebuild` after changing filtered recipes, nutrient maps, or vector-store metadata.

### 8.4 Test recipe generation from the command line

Use this command as a quick smoke test after the setup artifacts are built. The
user provides **available ingredients, cooking tools, and a target cooking time**;
the generator combines those inputs with retrieved recipe examples and nutrient
context.

```powershell
python scripts/generate_recipe.py `
  --recipes datasets/filtered_recipes_merged.json `
  --ingredients tomato egg rice `
  --tools pan stove `
  --time 30
```

Optional args:

- `--no-example`: disable retrieved example recipes in the prompt.
- `--validated-json`: parse the model output into the `GeneratedRecipe` schema.

## 9. Recipe evaluation

Generated recipes are evaluated on whether it's healthy, relevant to the user request, and structurally consistent. These checks are deterministic; they do not
judge flavor or cooking quality.

The full evaluator returns three groups of results:

- **Health**: calculates nutrient totals and health score using the nutrient retriever.
- **Relevance**: checks required tools, cooking-time limit, and ingredient overlap with the user request.
- **Consistency**: checks that instructions, ingredient measurements, and step sequence are structurally valid.

Run the evaluator on one generated recipe JSON file:

```powershell
python scripts/evaluate_recipe.py `
  --recipe artifacts/generated_recipe.json `
  --ingredients tomato egg rice `
  --tools pan stove `
  --time 30 `
  --output artifacts/evaluation_result.json
```

Use `--focused-tools` when only a subset of tools must appear in the generated
recipe. If it is omitted, the evaluator uses all tools passed through `--tools`.

Time parsing supports numeric minutes and strings such as `"30 minutes"`,
`"20-30 minutes"`, `"1.5 hours"`, and `"1 hour 30 minutes"`.



## 10. Tests and quality checks

Run all tests:

```powershell
python -m pytest -q
```

Run strict type checking:

```powershell
python -m mypy src\recipeprep
python -m mypy app\gradio_app.py
```

Run linting after installing development dependencies:

```powershell
python -m ruff check src tests app scripts
```

The tests cover:

- configuration and schemas;
- dataset sampling and filtering;
- CNF nutrient handling;
- quantity parsing and unit conversion;
- ingredient and recipe retrieval helpers;
- health-score boundaries;
- relevance and consistency checks;
- recipe generation with mocked clients;
- Gradio input handling;
- filtering scripts.

Tests do not make real OpenAI calls.


