# RecipePrep
A GPT-4o-powered personalized recipe generator designed to make balanced cooking more accessible for users who may find healthy recipes complex or time-consuming to search for online. By taking user-provided ingredients and cooking requirements as input, it generates tailored recipes with clear step-by-step instructions, helping users create practical, balanced meals from what they already have.

## API key setup

Create an OpenAI API key and expose it through the `OPENAI_API_KEY` environment variable before running the notebooks. For PowerShell:

```powershell
$env:OPENAI_API_KEY="your-key"
```

The repository includes `.env.example` as a configuration template, while populated `.env` files are ignored by Git.

Never place an API key directly in source code, notebook cells, or notebook output.

## Data Processing
### Data Processing Agent + Ingredient Nutrient map
#### Data sources
1. Recipe dataset: https://eightportions.com/datasets/Recipes/#fn:1
2. Ingredient CNF API: https://produits-sante.canada.ca/api/documentation/cnf-documentation-en.html#a6

#### Code Folders
1. **DataPrcoessing_1.ipynb**: The main notebook for Recipe data cleaning + Ingredient Map + Data Processign Agent 
2. Helpers folder: All helper functions
3. recipes_raw folder: 
    - All raw recipe datasets
    - the **Good_ingredient_List.csv**: the ingredient list we extract from [Food Basic](https://www.foodbasics.ca/aisles/fruits-vegetables?sortOrder=popularity) webiste based on popularity 
    - **recipes_raw_processed.json**: Processed recipe that only contains ingredients in the Good ingredient list
4. datasets folder: 
    - **recipe_dataset_init_{}.json**: Randomly selected small testing dataset from recipes_raw_processed.json. The number means number of items.  
    - **./Processed_Recipes/processed_recipes_init_{number of corresponding recipes before process}_ batch_**: Initially **processed** recipe datasets. Batch size 50, batch files are indexed in asc order. 
    - CNF_API_food_code.json: Ingredient food code dataset from CNF
    - emb folder: the processed embedding and faiss index for descriptions in the CNF_API_food_code.json
    - **testing** folder: 
        - tuning_ingre_list.csv: 80% of the Good ingredient list
        - test_ingre_list.csv: 20% of Good ingredient list
5. **ingre_nutrition_map**: Where the map and the unit map is stored

#### Main Code Walkthrough

Please read the DataPrcoessing_1.ipynb about how to use them. Following are some helper functions if you just want to run the process end to end.

##### To have a smaller dataset for testing
See this example test function `recipe_dataset_gen.test_get_testing_dataset`, and use the functions called inside 

##### To process the paragraph style recipes into structured labels
See main notebook `get_processed_recipe_dataset()`

##### To get nutrient mapping for the processed recipes:

See main notebook **Ingredient-Nutrient Mapping** section. The major functions are:
1. get_food_code_for_ingredients()
2. get_all_ingredient_mapping()
3. food_nutrient_mapping_helpder.save_nut_map

### Dataset Filtering

#### Data source

1. **Processed recipe dataset**: `./datasets/Processed_Recipes`
2. **Ingredient-nutrient map**: `./ingre_nutrition_map`

#### Filtering criteria

- **Health Score**: Quantifies the nutrient balance of each recipe, (detailed in the **Evaluation** Section). Recipes with a health score below 3 are filtered out.

#### Code

1. **`RAG_health_score_ver5.ipynb`**: The notebook for calculating the health score and adding it as an attribution in the recipe JSON file.
2. **`RAG_health_score.py`**: The Python functions inplementing the health score algorithm.
3. **`recipe_filter.ipynb`**: The notebook for filtering recipes and merging balanced recipes in a JSON file.

#### Main Code Walkthrough

##### To calculate recipes' health score

Use the major function `get_health_score_with_rag()` in `RAG_health_score.py`.

Examples Usages in the same file:

- For a single recipes
- For multiple recipes stored in a JSON file.

For a detailed algorithm flow and output examples, refer to `RAG_health_score_ver5.ipynb`.

##### To filter recipes

Use `filter()` in the `recipe_filter.ipynb` notebook.

#### Filtered Dataset

- **Filtered Recipes**: `./datasets/filtered_recipes_419.json`  
  Contains 419 balanced recipes with a health score of 3 or higher.

---

## Evaluation

### Criteria

1. **Health Score**: Measures the nutrient balance of a recipe based on the WHO Nutrient Intake Goals. Seven macronutrients are considered:  
   - **Proteins**  
   - **Carbohydrates**  
   - **Sugars**  
   - **Sodium**  
   - **Fats**  
   - **Saturated Fats**  
   - **Fibres**  

   Each macronutrient that falls within the recommended range scores 1 point. The total score (out of 7) is the recipe’s health score.
2. **Relevance**: Evaluates how well the recipe meets user requirements, including:  
   - **Cooking Tools**  
   - **Cooking Time**  
   - **Ingredient Similarity**  
3. **Consistency**: Assesses the quality of the generated recipe based on:  
   - **Instructional Clarity**  
   - **Measurement Consistency**  
   - **Logical Step Sequencing**

### Code

1. **`RAG_health_score.py`**: The Python function for health score calculation algorithm.
2. **`recipe_relevance_ver3.py`**: The Python function for relevance evaluation algorithm.

### Main Code Walkthrough

#### To calculate recipes' health score

Use the major function `get_health_score_with_rag()` in `RAG_health_score.py`.

#### To evaluate recipes' relevance

Use the major function `relevance_evaluation()` in `recipe_relevance_ver3.py`.
Refer to the example in the file for guidance on function usage.

### Evaluation Function Output

1. **`get_health_score_with_rag()`**:
Returns the health score and a summary of points for the input recipe.

    **Example Output**:

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

2. **`relevance_evaluation()`**:
Returns the relevance evaluation results for the input recipe.

    **Example Output**:

    ```json
    {
        "cooking_tools": "True", 
        "cooking_time": 0, 
        "ingredient_overlap_rate": 66.66666666666666
    }
    ```

    **Explanation**:

    - `cooking_tools`:
        - `True` if the recipe meets the tool requirement; otherwise, `False`.
    - `cooking_time`:
        - `0` if the cooking time is within the user's limit.
        - Positive value indicating the exceeded time (in minutes).
    - `ingredient_overlap_rate`:
        - The overlap rate of user inputs and recipe ingredients.
        - 100% means all ingredients needed for the recipe can be found in user's inputs.



