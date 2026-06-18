"""
Provide functions to evaluate the relevance of recipes using RAG
"""

import json

from langchain_community.document_loaders import JSONLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from recipeprep.config import get_config


CONFIG = get_config()
"""
Check the hard constraints
Input arguments:
- input_tools: tools from users
- recipe: generated recipe, containing the attribute "required_tools"
- focused_tools: the list of tools we want to pay attention to
Output:
- True: satisfy the hard constraint
- False: user don't have tools that are needed for the recipe and on the focused tools list. unsatisfy the hard constraint
"""
def check_cooking_tools(input_tools,recipe,focused_tools):
  recipe_tools=recipe.get("required_tools",[])
  for tool in focused_tools:
    if tool in recipe_tools and tool not in input_tools:
      return False
  return True

"""
Check the soft constraint: cooking time
Input arguments:
- input_time: available time from users
- recipe: generated recipe, containing the attribute "cooking_time"
Output:
- 0: recipe's cooking time is within the user's available time
- value>0: exceeded time value
"""
def check_cooking_time(input_time,recipe):
  cooking_time_str=recipe.get("cooking_time")
  cooking_time = int(''.join(filter(str.isdigit, cooking_time_str)))
  if cooking_time <= input_time:
    return 0
  return cooking_time - input_time

"""
functions for RAG
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

def retrieve_food_and_nutrients(retriever,query):
    results=retriever.get_relevant_documents(query)
    if not results:
      return None,None
    best_match=results[0]
    ingredient_name=best_match.metadata.get("ingredient_name")
    nutrients=best_match.metadata.get("nutrients")

    return ingredient_name, nutrients

"""
functions for similarity
"""

def get_matched_list(ingredient_list,retriever):
    matched_ingredient_list=[]
    for ingredient in ingredient_list:
      matched_ingredient,nutrients=retrieve_food_and_nutrients(retriever,ingredient)
      matched_ingredient_list.append(matched_ingredient)
    return matched_ingredient_list

def compare_ingredient_list(user_root_list,recipe_root_list):
  user_set={ing for ing in user_root_list}
  recipe_set={ing for ing in recipe_root_list}
  is_covered=recipe_set.issubset(user_set)
  common_ingredients=user_set&recipe_set
  overlap_rate=(len(common_ingredients)/len(recipe_set))*100
  return is_covered,overlap_rate

def get_similarity(input_ingredients,recipe,retriever):
  recipe_ingredients=recipe["pure_ingredients"]
  matched_ingredient_list_1=get_matched_list(input_ingredients,retriever)
  matched_ingredient_list_2=get_matched_list(recipe_ingredients,retriever)
  is_covered,overlap_rate=compare_ingredient_list(matched_ingredient_list_1,matched_ingredient_list_2)
  return is_covered,overlap_rate

"""
master function
Input arguments:
- focused_tools: the list of tools we want to pay attention to
- input_tools: tools from users
- input_time: available time from users
- input_ingredients: ingredients from users
- recipe: a generated recipe
- nutrient_map_path: the file path of nutrient map
Output:
The Output format is like:
{'cooking_tools': True, 'cooking_time': 0, 'ingredient_overlap_rate': 66.66666666666666}
meaning:
- cooking_tools: True -> satisfy the hard constraint; Otherwise False.
- cooking_time: 0 -> recipe's cooking time is within the user's available time; 
                value -> value of exceeded time (unit: minute)
- ingredient_overlap_rate: the overlap rate of user inputs and recipe ingredients. 
                           Rate = 100% means all ingredients needed for the recipe can be found in user's inputs.

Note that when you call the function, it will ask you to provide your api key.
"""
def relevance_evaluation(focused_tools,input_tools,input_time,input_ingredients,recipe,nutrient_map_path):
  data=map_loader(nutrient_map_path)
  search_k=CONFIG.retrieval.top_k
  retriever=get_retriever(data,search_k)

  hard_constraint=check_cooking_tools(input_tools,recipe,focused_tools)
  cooking_time_constraint=check_cooking_time(input_time,recipe)
  is_covered, overlap_rate=get_similarity(input_ingredients,recipe,retriever)

  relevance_eval={
      'cooking_tools': hard_constraint,
      'cooking_time': cooking_time_constraint,
      'ingredient_overlap_rate': overlap_rate
  }
  return relevance_eval

"""
Test Example
"""
if __name__ =='__main__':
    input_file_path = CONFIG.datasets_dir / "filtered_recipes_419.json"
    nutrient_map_path = CONFIG.nutrient_map_path
    with open(input_file_path, "r") as file:
        recipes = json.load(file)
    recipe = recipes[0]
    input_time = 10
    input_tools = ["pan", "stove"]
    input_ingredients = [
        "peach",
        "sugar",
        "wine",
        # "raspberries",
        # "blueberries",
        "lemon"
    ]
    focused_tools = ["stove", "oven"]

    print(relevance_evaluation(focused_tools, input_tools, input_time, input_ingredients, recipe, nutrient_map_path))
