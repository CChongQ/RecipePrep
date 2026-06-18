import json
import re

import faiss
import requests
from nltk.stem import WordNetLemmatizer

from recipeprep.config import get_config


CONFIG = get_config()
FOOD_CODE_URL = (
    f"{CONFIG.cnf.base_url}{CONFIG.cnf.food_endpoint}"
    f"?lang={CONFIG.cnf.language}&type=json"
)
FOOD_CODE_PATH = CONFIG.cnf_food_code_path
FOOD_DES_FAISS_INDEX_PATH = CONFIG.faiss_index_path


lemmatizer = WordNetLemmatizer()


#Load Ingredient food_code dataset
def get_food_code_dataset():
    res = requests.get(FOOD_CODE_URL, timeout=CONFIG.cnf.request_timeout_seconds)
    res.raise_for_status()
    food_code_data = res.json()
    FOOD_CODE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FOOD_CODE_PATH.open("w", encoding="utf-8") as f:
        json.dump(food_code_data, f, indent=4)
    
    return food_code_data

def preprocess_text(text):
    # Lowercase and remove punctuation
    text = text.strip().lower()
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation

    text = " ".join([lemmatizer.lemmatize(word) for word in text.split()])
    
    return text

def get_normalized_foodCode_dataset():
    with FOOD_CODE_PATH.open("r", encoding="utf-8") as file:
        food_code_dataset = json.load(file)

    #Clean the description
    food_descriptions = [
        f"{preprocess_text(item['food_description'])}" 
        for item in food_code_dataset
    ]
    food_codes = [item["food_code"] for item in food_code_dataset]
    
    return food_descriptions,food_codes

def get_regular_foodCode_dataset():
    with FOOD_CODE_PATH.open("r", encoding="utf-8") as file:
        food_code_dataset = json.load(file)

    #Clean the description
    food_descriptions = [
        f"{item['food_description']}" 
        for item in food_code_dataset
    ]
    food_codes = [item["food_code"] for item in food_code_dataset]
    return food_descriptions,food_codes
    

def create_FAISS_Index(food_embeddings):
    # Create a FAISS index
    dimension = food_embeddings.shape[1]  # Embedding dimension
    index = faiss.IndexFlatL2(dimension)
    index.add(food_embeddings)  # Add embeddings to the index

    # Save the FAISS index for future use
    FOOD_DES_FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(FOOD_DES_FAISS_INDEX_PATH))
    print(f"FAISS index saved in {FOOD_DES_FAISS_INDEX_PATH}")
    
    return index
