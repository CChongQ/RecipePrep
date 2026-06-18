import pandas as pd
import random
from itertools import combinations
import math


import random
import math

import csv

from recipeprep.config import get_config


CONFIG = get_config()

def generate_mix_examples(categorized_data,num_examples, ingredient_range):
    examples = []
    mixed_examples = categorized_data.get("Mixed", [])  # Retrieve mixed examples if they exist
    # Ensure at least half of examples are from the "Mixed" category
    for _ in range(num_examples // 5):
        if mixed_examples:
            sampled_ingredients = random.choice(mixed_examples)[:random.randint(*ingredient_range)]
            examples.append({"category": "Mixed", "ingredients": sampled_ingredients})

    # Fill the rest with examples from single categories
    for _ in range(num_examples - len(examples)):
        category = random.choice([cat for cat in categorized_data.keys() if cat != "Mixed"])
        ingredients = categorized_data[category]
        if len(ingredients) >= ingredient_range[0]:  # Ensure enough items
            sampled_ingredients = random.sample(ingredients, random.randint(*ingredient_range))
            examples.append({"category": category, "ingredients": sampled_ingredients})
    return examples


def create_examples(categorized_data, mid_percnt, total_size):
    # Calculate the number of intermediate and other examples
    mid_num = round(total_size * mid_percnt)  # Use round instead of floor
    short_num = (total_size - mid_num) // 2   # Divide remaining evenly between short and long
    long_num = total_size - (mid_num + short_num)  # Calculate leftover
    print(f"Mid length examples: {mid_num}, Short length examples: {short_num}, Long length examples: {long_num}")

    # Initialize lists to store examples
    short = []
    intermediate = []
    long = []
    
    short = generate_mix_examples(categorized_data,short_num, (1,3))
    intermediate = generate_mix_examples(categorized_data,mid_num, (4,7))
    long = generate_mix_examples(categorized_data,long_num, (8,12))

    # Combine all examples
    return short, intermediate, long

def split_with_mixed(samples, tune_num):
    """
    Splits the samples into tuning and testing datasets with at least 50% from the Mixed category.
    """
    # Separate Mixed and Non-Mixed samples
    mixed_samples = [s for s in samples if s["category"] == "Mixed"]
    non_mixed_samples = [s for s in samples if s["category"] != "Mixed"]

    # Ensure at least 50% Mixed in the tuning dataset
    num_mixed_tune = min(len(mixed_samples), tune_num // 2)
    num_non_mixed_tune = tune_num - num_mixed_tune

    # Tuning dataset
    tuning = mixed_samples[:num_mixed_tune] + non_mixed_samples[:num_non_mixed_tune]
    # Testing dataset
    testing = mixed_samples[num_mixed_tune:] + non_mixed_samples[num_non_mixed_tune:]

    return tuning, testing

def generate_datasets(file_path,mid_percnt,total_size,tune_size):
    # Load CSV file
    data = pd.read_csv(file_path)
    
    # Dynamically detect all categories from the file
    all_categories = data['Category'].unique().tolist()
    
    # Placeholder for categorized data
    categorized_data = {category: [] for category in all_categories}
    categorized_data['Mixed'] = []  # To hold mixed category combinations

    # Populate categorized_data with items from each category
    for index, row in data.iterrows():
        ingredient = row['Food']
        category = row['Category']
        if category in categorized_data:
            categorized_data[category].append(ingredient)

    # Generate mixed combinations of ingredients (any N number of categories)
    max_categories = len(all_categories)
    for num_categories in range(2, max_categories + 1):
        for category_combination in combinations(all_categories, num_categories):
            combined_ingredients = []
            for cat in category_combination:
                if categorized_data[cat]:
                    combined_ingredients.append(random.choice(categorized_data[cat]))
            if combined_ingredients:
                categorized_data['Mixed'].append(combined_ingredients)
                
    #create dataset
    tuning_dataset = []
    testing_dataset = []

    short_samples, intern_samples, long_samples = create_examples(categorized_data, mid_percnt, total_size)
    
    tune_short_num = math.floor(len(short_samples) * tune_size)
    tune_intern_num = math.floor(len(intern_samples) * tune_size)
    tune_long_num = math.floor(len(long_samples) * tune_size)
    # Split short, intermediate, and long samples into tuning and testing datasets
    tuning_short, testing_short = split_with_mixed(short_samples, tune_short_num)
    tuning_intern, testing_intern = split_with_mixed(intern_samples, tune_intern_num)
    tuning_long, testing_long = split_with_mixed(long_samples, tune_long_num)

    # Combine all datasets
    tuning_dataset = tuning_short + tuning_intern + tuning_long
    testing_dataset = testing_short + testing_intern + testing_long

    # Sort the datasets by length
    tuning_dataset_sorted = sorted(tuning_dataset, key=lambda x: len(x["ingredients"]))
    testing_dataset_sorted = sorted(testing_dataset, key=lambda x: len(x["ingredients"]))
    
    # Print the sorted datasets
    print("Sorted Tuning Dataset:")
    for example in tuning_dataset_sorted:
        print(example)

    print("\nSorted Testing Dataset:")
    for example in testing_dataset_sorted:
        print(example)
        
    return tuning_dataset_sorted,testing_dataset_sorted
    
def save_to_csv(data, file_path):

    csv_data = {"Category": [], "Ingredients": []}

    # Populate the dictionary
    for entry in data:
        if isinstance(entry, dict):  # Ensure each entry is a dictionary
            csv_data["Category"].append(entry.get("category", "Unknown"))
            csv_data["Ingredients"].append(", ".join(entry.get("ingredients", [])))
        else:
            print(f"Skipping invalid entry: {entry}")  # Debugging invalid entries

    # Save the dictionary as a CSV file
    with open(file_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        # Write header
        writer.writerow(csv_data.keys())
        # Write rows
        writer.writerows(zip(*csv_data.values()))

def test_generate_datasets():
    file_path = CONFIG.test_data_dir / "testing_ingredient_List.csv"
    mid_percnt=0.5
    total_size = 400
    tune_size=0.2
    tuning_dataset_sorted,testing_dataset_sorted = generate_datasets(file_path,mid_percnt,total_size,tune_size)
    tuning_dataset_filename = CONFIG.test_data_dir / "tuning_ingre_list.csv"
    testing_dataset_filename = CONFIG.test_data_dir / "testing_ingre_list.csv"
    save_to_csv(tuning_dataset_sorted, tuning_dataset_filename)
    save_to_csv(testing_dataset_sorted, testing_dataset_filename)
    
    
if __name__ == "__main__":
    test_generate_datasets()
