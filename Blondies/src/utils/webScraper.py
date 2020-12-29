import requests
from bs4 import BeautifulSoup
import json
import re
import pandas as pd
import string
import os

import scraper_params as sp


def soupify_url(url):
    page = requests.get(url)
    return BeautifulSoup(page.content, 'html.parser')


def search_all_recipes(search_term):
    # enter search term, return a list of links to recipes
    url = "https://www.allrecipes.com/search/results/?wt=" + search_term
    soup = soupify_url(url)
    grid_cards = soup.findAll("div", {"class": "grid-card-image-container"})
    links_list = [card.find('a')['href'] for card in grid_cards]
    return links_list


def get_recipe_dict(soup):
    app_json = soup.find("script", {"type": "application/ld+json"}).contents
    recipe_dict = json.loads("".join(app_json))[1]
    return recipe_dict


def get_ingredients_dict(item_ingredients):
    item_ingredients_cleaned = []

    # TO-DO: more elegant solution for fractions in string
    for ingr in item_ingredients:
        ingr = ingr.replace("½", ".5") \
            .replace("¼", ".25") \
            .replace("¾", ".75") \
            .replace("⅔", ".6666") \
            .replace("⅓", ".3333") \
            .replace("\u2009", "")
        item_ingredients_cleaned.append(ingr)

    item_ingredients = {}

    for i in item_ingredients_cleaned:
        qty = re.findall(r"[-+]?\d*\.*\d+", i)  # find decimal values
        unit = [s for s in i.split() if s in sp.unit_names]  # find measuring unit

        qty = qty[0] if len(qty) > 0 else ""
        unit = unit[0] if len(unit) > 0 else ""

        i = i.replace(qty, "")
        i = i.replace(unit, "")

        ingredient_item_dict = {'quantity': qty, 'measuring_unit': unit}
        item_ingredients[i.lstrip()] = ingredient_item_dict

    return item_ingredients


def convert_to_ml(quantity, measuring_unit):
    if "cup" in measuring_unit:
        return 236.586 * float(quantity)
    elif "tablespoon" in measuring_unit or "tbsp" in measuring_unit:
        return 14.787 * float(quantity)
    elif "teaspoon" in measuring_unit or "tsp" in measuring_unit:
        return 4.929 * float(quantity)
    else:
        return None


def clean_ingredients(item_name):
    item_name = "".join(c for c in item_name if c not in ('!', '.', ':', ','))

    if "sugar" in item_name:
        if "brown" in item_name:
            return "brown sugar"
        else:
            return "white sugar"
    for ingredient in sp.common_ingredients:
        if ingredient in item_name:
            return ingredient


search_term = "brownies"
brownie_recipe_links = search_all_recipes("brownies")

brownie_recipe_links = brownie_recipe_links[0:2] # limit to 4 links for testing
df = pd.DataFrame(columns=('recipe_name', 'recipe_categories', 'ingredient_name', 'quantity', 'measuring_unit', 'total_milliliters'))

for link in brownie_recipe_links:
    recipe_soup = soupify_url(link)
    recipe_dict = get_recipe_dict(recipe_soup)

    item_name = recipe_dict["name"]
    item_ingredients = recipe_dict["recipeIngredient"]
    item_category = recipe_dict["recipeCategory"]

    ingredients_dict = get_ingredients_dict(item_ingredients)

    for k, v in ingredients_dict.items():
        # temp fix for fractions in strings
        try:
            row_list = [item_name,
                        item_category,
                        clean_ingredients(k),
                        v["quantity"],
                        v["measuring_unit"],
                        convert_to_ml(v["quantity"], v["measuring_unit"])
                        ]
        except Exception as e:
            print("error: ", e, "item_name: ", item_name, "key: ", k, "value:  ", v)
            exit(1)

        row_list_series = pd.Series(row_list, index=df.columns)
        df = df.append(row_list_series, ignore_index=True)


# TO DO:
# pivot or unstack df to have ingredients as columns
# ex: recipe_name, recipe_categories, flour_qty, sugar_qty, prediction(cookie, brownie, both, neither)

# output_path = '' # ADD OUTPUT PATH
# file_name = search_term + ".csv"
# df_pivoted.to_csv(os.path.join(output_path, file_name), index=False)
