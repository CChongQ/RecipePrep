import json
import random
from pathlib import Path

import requests

from recipeprep.config import get_config


CONFIG = get_config()
NUTRITION_BASE_URL = CONFIG.cnf.base_url
REQ_LANG = CONFIG.cnf.language
REQ_NUT_AMOUNT = CONFIG.cnf.nutrient_amount_endpoint
REQ_NUT_NAME = CONFIG.cnf.nutrient_name_endpoint
MAP_BASE_PATH = CONFIG.nutrient_maps_dir
NUT_UNIT_MAP_NAME = CONFIG.cnf.nutrient_unit_map_filename
INGRE_NUT_MAP_NAME = CONFIG.cnf.nutrient_map_filename

EVAL_NUTRIENTS = {"Protein", "Carbohydrate", "Sugars, total", "Sodium, Na", "Total Fat", "Fatty acids, saturated, total", "Fiber","Fibre","Calories","Energy"}

def get_nutrientamount_foodcode(food_code):
    query_param = f'{REQ_NUT_AMOUNT}?REQ_LANG={REQ_LANG}&id={food_code}'

    request_url = NUTRITION_BASE_URL + query_param
    #print(request_url)
    response = requests.get(request_url, timeout=CONFIG.cnf.request_timeout_seconds)
    if response.status_code == 200:
        nutrient_data = response.json()
        return nutrient_data
    else:
        print(f"Failed to retrieve data for {food_code}: Status Code {response.status_code}")
        return None

def get_nutrientname_foodcode(nut_name_id):
    query_param = f'{REQ_NUT_NAME}?REQ_LANG={REQ_LANG}&id={nut_name_id}'
    request_url = NUTRITION_BASE_URL + query_param
    response = requests.get(request_url, timeout=CONFIG.cnf.request_timeout_seconds)
    if response.status_code == 200:
        nutrient_data = response.json()
        #print(nutrient_data)
        return nutrient_data
    else:
        print(f"Failed to retrieve data for nutrient_nameId {nut_name_id}: Status Code {response.status_code}")
        return None

#Return processed/fitlered nutrient-ingredient map for the input food code
def get_nut_map(in_foodCode, ingre_name, nutri_id_map):
    map_data = get_nutrientamount_foodcode(in_foodCode)

    if map_data:
        nutrients = []
        for eachNutri in map_data:
            # Check if the nutrient should be included
            if any(eval_nutri.lower() in eachNutri["nutrient_web_name"].lower() for eval_nutri in EVAL_NUTRIENTS):
                nut_id = str(eachNutri["nutrient_name_id"])
                if nutri_id_map and nut_id in nutri_id_map:
                    nutri_unit = nutri_id_map[nut_id]
                else:
                    if not nutri_id_map:
                        nutri_id_map={}
                    nutri_unit = get_nutrientname_foodcode(nut_id)
                    nutri_unit  = 'g' if nutri_unit==None else nutri_unit["unit"]                   
                    nutri_id_map[nut_id] =  nutri_unit
               
                nutrient_info = {
                    #"food_code": eachNutri["food_code"],
                    "value": eachNutri["nutrient_value"],
                    #"nutrient_name_id": eachNutri["nutrient_name_id"],
                    "nutrient_name": eachNutri["nutrient_web_name"],
                    "unit": nutri_unit  # Get the unit from function
                }
                nutrients.append(nutrient_info)
        aggregated_data = {
            "ingredient_name": ingre_name,
            "nutrients": nutrients
        }
      
        return aggregated_data,nutri_id_map

    return None,None


def save_nut_map(nuntri_unit_map,all_mapping):
    
    #save the unit map
    nut_unit_map_name = get_unitMap_name()
    save_nut_id_map(nuntri_unit_map,nut_unit_map_name)

    #save the ingredient-nutrient map
    output_file_name = MAP_BASE_PATH / INGRE_NUT_MAP_NAME
    output_file_name.parent.mkdir(parents=True, exist_ok=True)
    with output_file_name.open("w", encoding="utf-8") as file:
        json.dump(all_mapping, file, indent=4)

    print(f"Ingredient-Nutrient mapping has been saved to {output_file_name}")
        
'''Small Helpers'''

def load_nut_id_map(unit_map_name):
    unit_map_path = Path(unit_map_name)
    if unit_map_path.exists():
        with unit_map_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {}
    
def save_nut_id_map(nut_id_map,unit_map_name):
    unit_map_path = Path(unit_map_name)
    unit_map_path.parent.mkdir(parents=True, exist_ok=True)
    with unit_map_path.open("w", encoding="utf-8") as f:
        json.dump(nut_id_map, f, indent=4)
    
    print(f"Unit map {unit_map_name} updated!")
    
    
def count_items_in_dataset(file_path):
    with open(file_path, "r") as file:
        dataset = json.load(file)
    return len(dataset) 

def save_N_random_items(in_filename, out_filename, N):

    # Load the dataset
    with open(in_filename, "r") as f:
        data = json.load(f)
    
    # Select N random items
    if N > len(data):
        print(f"Requested {N} items, but the dataset contains only {len(data)} items. Selecting all items.")
        N = len(data)
        
    random_items = random.sample(data, N)

    # Save the selected items to a new file
    with open(out_filename, "w") as f:
        json.dump(random_items, f, indent=4)
    
    print(f"{N} random items have been saved to {out_filename}.")


'''
    For testing
'''

def get_unitMap_name():
    return MAP_BASE_PATH / NUT_UNIT_MAP_NAME
    
def test_map_create():

    unit_map_name =get_unitMap_name()
    untri_unit_map = load_nut_id_map(unit_map_name)
    
    aggregated_data,nutri_unit_map_ret= get_nut_map(4905," alfredo sauce",untri_unit_map)
   
    save_nut_id_map(nutri_unit_map_ret,unit_map_name)


def test_mapping_size():
    # Example usage
    file_path = CONFIG.cnf_food_code_path
    num_items = count_items_in_dataset(file_path)
    print(f"The dataset contains {num_items} items.")

def get_smaller_map():
    file_path = CONFIG.cnf_food_code_path
    out_file = CONFIG.datasets_dir / "CNF_API_food_code_test.json"
    N=1000
    save_N_random_items(file_path,out_file,N)


#test_map_create()

    
