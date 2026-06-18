"""
Provide functions to evaluate the healthiness of recipes using RAG
"""
import json
import re

from langchain_community.document_loaders import JSONLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from recipeprep.config import get_config


CONFIG = get_config()

"""
load data from the file "ingredient_nutrient_map.json"
"""


def metadata_fuc(record: dict, metadata: dict) -> dict:
    metadata["ingredient_name"] = record.get("ingredient_name")
    # change the attribute "nutrients" from list to string for the following embedding and vector storage
    metadata["nutrients"] = ''.join(map(str, record.get("nutrients")))
    return metadata


def map_loader(file_path):
    loader = JSONLoader(
        file_path=file_path,
        jq_schema=".[]",
        content_key="ingredient_name",
        metadata_func=metadata_fuc
    )
    data = loader.load()
    return data


"""
split the document into chunks for embedding and vector storage,
then turn the VectorStore into a Retriever
"""


def get_retriever(data, search_k):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CONFIG.retrieval.chunk_size,
        chunk_overlap=CONFIG.retrieval.chunk_overlap,
        add_start_index=True,
    )
    all_splits = text_splitter.split_documents(data)
    vectorstore = Chroma.from_documents(
        documents=all_splits,
        embedding=OpenAIEmbeddings(model=CONFIG.openai.embedding_model),
    )
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": search_k})
    return retriever


"""
Retrieve the most similar ingredient and its nutrients
"""


# retrieve the most similar food description and its nutrients
def retrieve_food_and_nutrients(retriever, query):
    results = retriever.get_relevant_documents(query)
    if not results:
        return None, None
    best_match = results[0]
    ingredient_name = best_match.metadata.get("ingredient_name")
    nutrients = best_match.metadata.get("nutrients")

    return ingredient_name, nutrients


"""
Generate
"""


# change value with different units to gram
# the format of ingredient_dict: e.g.{'value': '3', 'unit': 'tablespoon', 'name': 'rice vinegar'}
# 3 tablespoons rice vinegar
def convert_to_grams(ingredient_dict):
    convert_table = {
        'tablespoon': 17.07,
        'teaspoon': 5.69,
        'ounce': 28.35,
        'cup': 150.00,
        'lb': 453.59,
        'pound': 453.59,
        'tbsp': 17.07,
        'tsp': 5.69,
        'oz': 28.35,
        'kg': 1000.00,
        'kilogram': 1000.00,
        'gram': 1.00,
        'g': 1.00,
        'mg': 0.001
    }
    unit = ingredient_dict['unit']
    value = ingredient_dict['value']
    convert_factor = convert_table.get(unit, None)
    try:
        numeric_value = eval(value)
        convert_value = numeric_value * convert_factor if convert_factor else 100
    except:
        convert_value = 100
    ingredient_dict['value'] = convert_value
    ingredient_dict['unit'] = 'gram'
    return ingredient_dict


def get_health_score_with_rag(retriever, recipe):
    ingredients = recipe.get("processed_ingredients")
    pure_ingredients = recipe.get("pure_ingredients")
    nutrient_map = {
        "Protein": 0,
        "Carbohydrate": 0,
        "Sugars, total": 0,
        "Sodium, Na": 0,
        "Total Fat": 0,
        "Fatty acids, saturated, total": 0,
        "Fibre, total dietary": 0,
        "Energy (kJ)": 0,
    }

    for i, ingredient in enumerate(ingredients):
        match = re.match(r"([\d./]+)\s*([a-zA-Z]+)?\s*(.*)", ingredient)
        if match:
            value = match.group(1).strip()
            unit = match.group(2) if match.group(2) else ""
            if len(pure_ingredients) == len(ingredients):
                name = pure_ingredients[i]
            else:
                name = match.group(3).strip()

            if unit.endswith("s"):  # Handle plural forms
                unit = unit[:-1]
            parsed_ingredient = {"value": value, "unit": unit, "name": name}
            ingredient_dict = convert_to_grams(parsed_ingredient)
            matched_ingredient, nutrients = retrieve_food_and_nutrients(retriever, ingredient_dict["name"])
            nutrient_pattern = r"'value': ([\d.]+), 'nutrient_name': '([^']+)'"
            matches = re.findall(nutrient_pattern, nutrients)
            for value, name in matches:
                if name in nutrient_map:
                    nutrient_map[name] += float(value) * ingredient_dict["value"] / 100

    health_score = 0
    score_summary = {
        "Proteins": 0,
        "Carbohydrates": 0,
        "Sugars": 0,
        "Sodium": 0,
        "Fats": 0,
        "Saturated Fats": 0,
        "Fibers": 0
    }
    # print(nutrient_map)
    protein_energy = nutrient_map['Protein'] * 17
    carbo_energy = nutrient_map['Carbohydrate'] * 17
    fat_energy = nutrient_map['Total Fat'] * 37
    sugar_energy = nutrient_map['Sugars, total'] * 17
    sat_fat_energy = nutrient_map['Fatty acids, saturated, total'] * 37
    fiber_energy = nutrient_map['Fibre, total dietary'] * 8
    sodium_energy = nutrient_map['Sodium, Na'] * 0
    total_energy = nutrient_map['Energy (kJ)']

    if protein_energy >= total_energy * 0.1 and protein_energy <= total_energy * 0.35:
        health_score += 1
        score_summary["Proteins"] = 1
    if carbo_energy >= total_energy * 0.45 and carbo_energy <= total_energy * 0.75:
        health_score += 1
        score_summary["Carbohydrates"] = 1
    if sugar_energy <= total_energy * 0.1:
        health_score += 1
        score_summary["Sugars"] = 1
    if nutrient_map['Sodium, Na'] <= 500000:
        health_score += 1
        score_summary["Sodium"] = 1
    if fat_energy >= total_energy * 0.15 and fat_energy <= total_energy * 0.3:
        health_score += 1
        score_summary["Fats"] = 1
    if sat_fat_energy <= total_energy * 0.10:
        health_score += 1
        score_summary["Saturated Fats"] = 1
    if nutrient_map['Fibre, total dietary'] >= 6:
        health_score += 1
        score_summary["Fibers"] = 1
    return health_score, score_summary


"""
An example to calculate a recipe's health score
"""
if __name__ == "__main__":
    map_path = CONFIG.nutrient_map_path
    data = map_loader(map_path)
    retriever = get_retriever(data, CONFIG.retrieval.top_k)
    file_path = CONFIG.processed_recipes_dir / "processed_recipes_init_200_batch_1.json"
    with open(file_path, "r") as file:
        recipes = json.load(file)
    recipe = recipes[1]
    print(get_health_score_with_rag(retriever, recipe))

"""
An example to add `total_health_score` attribution in recipe JSON file
"""
if __name__ == "__main__":
    map_path = CONFIG.nutrient_map_path
    data = map_loader(map_path)
    retriever = get_retriever(data, CONFIG.retrieval.top_k)
    file_path = CONFIG.processed_recipes_dir / "processed_recipes_init_200_batch_1.json"
    with open(file_path, "r") as file:
        recipes = json.load(file)
    for i, recipe in enumerate(recipes):
        print(f"Recipe {i}")
        health_score, score_summary = get_health_score_with_rag(retriever, recipe)
        recipe["total_health_score"] = health_score
        recipe["summary_of_points"] = score_summary

    output_file_path = CONFIG.datasets_dir / "scored_recipes_init_200_batch_1.json"
    with open(output_file_path, "w") as file:
        json.dump(recipes, file, indent=4)
        print(f"health score in recipes has been saved")
