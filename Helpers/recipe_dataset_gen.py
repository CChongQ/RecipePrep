import json
import random
import re
from collections import Counter
from pathlib import Path

import pandas as pd
from nltk.stem import WordNetLemmatizer

from recipeprep.config import get_config


lemmatizer = WordNetLemmatizer()
CONFIG = get_config()

MIN_LONG_RECIPE_LEN = CONFIG.pipeline.long_recipe_min_characters


def _processed_recipe_files() -> list[Path]:
    if not CONFIG.processed_recipes_dir.is_dir():
        return []
    return sorted(CONFIG.processed_recipes_dir.glob("*.json"))


#Get recipe dataset
#long_percnt !=0: Return a long reicpe dataset with samp_size*long_percnt number of recipes, and a short recipe dataset with {1-long_percnt}*samp_size of recipes
#long_percnt ==0: Return a testing dataset with recipes randomly selected between long and short recipes 

def get_testing_dataset(in_filename,samp_size,long_percnt=0):

    existing_ids = set()
    
    # Extract recipe IDs from existing files
    for file in _processed_recipe_files():
        with file.open("r", encoding="utf-8") as f:
            data = json.load(f)
            existing_ids.update(recipe["recipe_id"] for recipe in data)
            
    with open(in_filename, "r") as f:
        recipe_data = json.load(f)
    
    #Basic filter: instruction!=None
    recipe_data = {recipe_ID: recipe_value for recipe_ID, recipe_value in recipe_data.items() 
                    if (recipe_ID not in existing_ids) and recipe_value.get("instructions") and isinstance(recipe_value["instructions"], str) and recipe_value["instructions"].strip()}
 
    if long_percnt!=0:   
        long_recipes={}
        short_recipes={}
        for recipe_ID, recipe_value in recipe_data.items():
            if  len(recipe_value["instructions"]) >= MIN_LONG_RECIPE_LEN:
                long_recipes[recipe_ID] = recipe_value
            else:
                short_recipes[recipe_ID] = recipe_value
        
        num_sample_long = int(samp_size * long_percnt)
        num_sample_short = samp_size - num_sample_long
        
        #corner case check
        if num_sample_long==0:
            raise ValueError("Error: The dataset don't have enough long recipes or the sample size is too small.")
        else:
            print(f"The dataset will contains {num_sample_long} long recipes and {num_sample_short} short recipes.")
              
        sampled_long_items = random.sample(list(long_recipes.items()), min(num_sample_long, len(long_recipes)))
        sampled_short_items = random.sample(list(short_recipes.items()), min(num_sample_short, len(short_recipes)))

        return sampled_short_items,sampled_long_items
    else:
        sampled_items = random.sample(list(recipe_data.items()), samp_size)
        return sampled_items,None

def filter_recipe_ingre_frequency(recipes_list, min_freq=3):
 
    # Get frequency for each ingredient
    ingredient_counts = Counter()
    for eachRecipe in recipes_list:
        ingredients = eachRecipe.get("pure_ingredients", [])
        ingredient_counts.update(ingredients)
    
    # filter out low frequency recipes
    valid_ingredients = set()
    for eachIngre,count in ingredient_counts.items():
        if count >= min_freq:
            valid_ingredients.add(eachIngre)
        else:
            print(f"[{eachIngre}] Filtered out")
    
    #Filter recipes
    filtered_recipes = []
    for recipe in recipes_list:
        ingredients = recipe.get("pure_ingredients", [])
        if all(ingredient in valid_ingredients for ingredient in ingredients):
            filtered_recipes.append(recipe)
    
    return filtered_recipes


def filter_raw_recipe_on_ingredient_list(raw_file_name,key_word_filename,output_filename):
    
    key_word_df = pd.read_csv(key_word_filename)
    keywords = key_word_df['Food'].dropna().tolist() 
    keywords = [normalize_word(keyword) for keyword in keywords]
    
    with open(raw_file_name, "r") as f:
        recipe_data = json.load(f)
    
    filtered_recipes = {}
    print(f"Before filter, recipe number = {len(recipe_data)}")
    
    for recipe_id, recipe in recipe_data.items():
            ingredients = recipe.get("ingredients", [])
            instruc = recipe.get("instructions")
            if len(ingredients)>0 and (instruc and len(instruc)>0):
                # Check if all ingredients in the recipe match at least one keyword
                all_ingredients_match = all(
                    any(keyword in normalize_word(ingredient) for keyword in keywords)
                    for ingredient in ingredients
                )
                
                if all_ingredients_match:
                    filtered_recipes[recipe_id] = recipe
                    
    print(f"After filter, recipe number = {len(filtered_recipes)}")
    
    save_json_file(filtered_recipes,output_filename)

#Used to generate the pure testing dataset
def get_pure_testing_ingre_list(data, category_col, frac=0.2, random_state=42):
    # Randomly sample from each category
    sampled_testing_data = data.groupby(category_col, group_keys=False).apply(
        lambda x: x.sample(frac=frac, random_state=random_state)
    )
    
    remaining_data = data.loc[~data.index.isin(sampled_testing_data.index)]
     
    return sampled_testing_data,remaining_data
    
'''
Small Helpers
'''  
#Get the average recipe length (the instruction field) in a dataset
def get_average_instruction_length(recipe_filename):
    with open(recipe_filename, "r") as f:
        recipe_data = json.load(f)
    
    instruction_lengths = [len(eachRecipe["instructions"]) for eachRecipe in recipe_data.values()]
    average_length = sum(instruction_lengths) / len(instruction_lengths) if instruction_lengths else 0

    return average_length

def save_json_file(in_data,output_file_name):
    with open(output_file_name, "w") as f:
        json.dump(in_data, f, indent=4)

def get_long_short_recipe_dataset(recipe_filename,sample_size,output_file_name,long_recipe_percnt=0.2):
        #output recipes contains a special percentage of long recipes
        short_recipes,long_recipes = get_testing_dataset(recipe_filename,sample_size,long_percnt=long_recipe_percnt)
        sampled_data = dict(short_recipes + long_recipes)
        save_json_file(sampled_data,output_file_name)
        print(f"{sample_size} records have been saved to {output_file_name}.")

def get_rand_recipe_dataset(recipe_filename,sample_size,output_file_name,long_recipe_percnt=0):
        #output recipes are randomly selected between long and short 
        all_recipes,_ = get_testing_dataset(recipe_filename,sample_size,long_percnt=long_recipe_percnt)
        sampled_data = dict(all_recipes)
        save_json_file(sampled_data,output_file_name)
        print(f"{sample_size} records have been saved to {output_file_name}.")

def get_ingre_list_from_dataset(file_path):
    with open(file_path, 'r') as f:
        processed_recipe_list = json.load(f)
    
    all_ingredients = set() #unique set

    for eachRecipe in processed_recipe_list:
        pure_ingredients = eachRecipe.get("pure_ingredients", [])
        # less_important_ingredients = eachRecipe["processed_output"].get("less_important_ingredients", [])

        all_ingredients.update(pure_ingredients)
        # all_ingredients.update(less_important_ingredients)


    all_ingredients_list = sorted(all_ingredients)
    
    all_ingredients_list = [preprocess_text(ingredient) for ingredient in all_ingredients_list]

  
    return all_ingredients_list

def preprocess_text(text):
    # Lowercase and remove punctuation
    text = text.strip().lower()
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation

    text = " ".join([lemmatizer.lemmatize(word) for word in text.split()])
    
    return text


def normalize_word(word):
    word = word.lower().strip()  # Convert to lowercase and remove extra spaces
    if word.endswith('es'):
        return word[:-2]
    elif word.endswith('s'):
        return word[:-1]
    return word


def combine_two_json(file_1, file_2,out_filename):
    with open(file_1, 'r') as f1:
        data1 = json.load(f1)

    # Load the contents of the second JSON file
    with open(file_2, 'r') as f2:
        data2 = json.load(f2)

    # Merge the two JSON objects
    # Assuming both files contain dictionaries
    combined_data = {**data1, **data2}

    # Save the combined data to a new file
    with open(out_filename, 'w') as out:
        json.dump(combined_data, out, indent=4)
        print(f"Combined JSON saved to {out_filename}")

'''
Testing helpers 
'''
def test_get_average_instruction_length():
    recipe_filename = CONFIG.datasets_dir / "sample_data_1000.json"
    avg_len = get_average_instruction_length(recipe_filename)
    print(f"The average instruction length in the {recipe_filename} dataset is: {avg_len:.4f} characters.")

def test_get_testing_dataset(long_recipe_percnt):
    sample_size = 250
    recipe_filename = CONFIG.raw_recipes_dir / "recipes_raw_processed.json"
    output_file_name = CONFIG.datasets_dir / f"recipe_dataset_init_{sample_size}.json"
    
    if long_recipe_percnt>0:
        get_long_short_recipe_dataset(recipe_filename,sample_size,output_file_name,long_recipe_percnt=long_recipe_percnt)
        
    else:
        #output recipes are randomly selected between long and short 
        get_rand_recipe_dataset(recipe_filename,sample_size,output_file_name,long_recipe_percnt=0)

def test_filter_recipe_ingre_frequency():
    recipe_filename = CONFIG.datasets_dir / "processed_recipes_init_300.json"
  
    with open(recipe_filename, "r") as f:
        recipe_data = json.load(f)
    
    min_freq=2
    filtered_recipes = filter_recipe_ingre_frequency(recipe_data, min_freq=2)
    filtered_filename = (
        CONFIG.datasets_dir
        / f"processed_freq{min_freq}_recipes_init_{len(filtered_recipes)}.json"
    )
    save_json_file(filtered_recipes,filtered_filename)
    
def test_filter_raw_recipe_on_ingredient_list():
    raw_file_name = CONFIG.raw_recipes_dir / "recipes_raw_nosource_epi.json"
    key_word_filename = CONFIG.raw_recipes_dir / "Good_ingredient_List.csv"
    output_filename_1 = CONFIG.raw_recipes_dir / "recipes_raw_nosource_epi_filtered.json"
    filter_raw_recipe_on_ingredient_list(raw_file_name,key_word_filename,output_filename_1)
    
    raw_file_name = CONFIG.raw_recipes_dir / "recipes_raw_nosource_fn.json"
    key_word_filename = CONFIG.raw_recipes_dir / "Good_ingredient_List.csv"
    output_filename_2 = CONFIG.raw_recipes_dir / "recipes_raw_nosource_fn_filtered.json"
    filter_raw_recipe_on_ingredient_list(raw_file_name,key_word_filename,output_filename_2)
    
    combined_filename = CONFIG.raw_recipes_dir / "recipes_raw_processed.json"
    combine_two_json(output_filename_1, output_filename_2,combined_filename)



def test_get_pure_testing_ingre_list():
    key_word_filename = CONFIG.raw_recipes_dir / "Good_ingredient_List.csv"
    data = pd.read_csv(key_word_filename)
    
    sampled_testing_data,remaining_data = get_pure_testing_ingre_list(data,  category_col="Category", frac=0.2,random_state=123)
    out_pure_ingre_list = CONFIG.test_data_dir / "test_ingre_list.csv"
    tune_ingre_list = CONFIG.test_data_dir / "tuning_ingre_list.csv"
    sampled_testing_data.to_csv(out_pure_ingre_list, index=False)
    remaining_data.to_csv(tune_ingre_list, index=False)

#test_filter_raw_recipe_on_ingredient_list()
#test_get_testing_dataset(0.2)
#test_get_pure_testing_ingre_list()
