import psycopg2
import requests
import os
import json
import time

from connect import DATABASE, USER, PASSWORD, HOST, PORT

ingredient_cache = {}

def preload_ingredient_cache(cursor):
    """Load all existing ingredients into memory cache"""
    cursor.execute("SELECT id, name FROM ingredient_list;")
    for ingredient_id, name in cursor.fetchall():
        ingredient_cache[name.strip().lower()] = ingredient_id

def create_tables(cursor):
    """Create normalized tables for recipes and ingredients"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            meal_id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT,
            area TEXT,
            instructions TEXT
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingredient_list (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            recipe_id INTEGER REFERENCES recipes(meal_id),
            ingredient_id INTEGER REFERENCES ingredient_list(id),
            PRIMARY KEY (recipe_id, ingredient_id)
        );
    """)

def insert_ingredient(cursor, ingredient_name):
   """Insert ingredient using in-memory cache for speed"""
   normalized = ingredient_name.strip().lower()

  # Check in cache
   if normalized in ingredient_cache:
        return ingredient_cache[normalized]

  # Insert into DB if not in cache
   cursor.execute("""
        INSERT INTO ingredient_list (name)
        VALUES (%s)
        ON CONFLICT (name) DO NOTHING;
    """, (normalized,))

  # Getting ID
   cursor.execute("SELECT id FROM ingredient_list WHERE name = %s;", (normalized,))
   ingredient_id = cursor.fetchone()[0]

  # Cache update
   ingredient_cache[normalized] = ingredient_id
   return ingredient_id


def insert_recipe_with_ingredients(cursor, meal):
    """Insert recipe and its ingredients into normalized tables"""
    cursor.execute("""
        INSERT INTO recipes (meal_id, name, category, area, instructions)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (meal_id) DO NOTHING
        RETURNING meal_id;
    """, (
        int(meal["idMeal"]),
        meal["strMeal"],
        meal["strCategory"],
        meal["strArea"],
        meal["strInstructions"]
    ))

    result = cursor.fetchone()
    if result:
        recipe_id = result[0]
        for i in range(1, 21):
            ingredient = meal.get(f"strIngredient{i}")
            if ingredient and ingredient.strip():
                ingredient_id = insert_ingredient(cursor, ingredient)
                cursor.execute("""
                    INSERT INTO recipe_ingredients (recipe_id, ingredient_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                """, (recipe_id, ingredient_id))

def get_all_categories():
    """Fetch all recipe categories from API or cache"""
    cache_file = "categories_cache.json"
    if os.path.exists(cache_file):
        last_modified = os.path.getmtime(cache_file)
        if time.time() - last_modified < 86400:  # 24 hours
            try:
                with open(cache_file, "r") as f:
                    print("Using category cache")
                    return json.load(f)
            except Exception as e:
                print(f"Cache read error: {e}")

    # If the cache didn't work, we load it from the API
    url = "https://www.themealdb.com/api/json/v1/1/list.php?c=list"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        categories = [item['strCategory'] for item in data.get('meals', [])]

        with open(cache_file, "w") as f:
            json.dump(categories, f)

        print("Categories are loaded from API and saved to cache")
        return categories
    except requests.RequestException as e:
        print(f"Error loading categories from API: {e}")
        return []


def load_recipes_by_category(cursor, connection):
    cache_file = "recipes_cache.json"
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            all_meals = json.load(f)
    else:
        all_meals = []
        categories = get_all_categories()
        for category in categories:
            url = f"https://www.themealdb.com/api/json/v1/1/filter.php?c={category}"
            response = requests.get(url)
            data = response.json()
            meals = data.get("meals", [])
            for meal in meals:
                meal_id = meal["idMeal"]
                detail_url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}"
                detail_response = requests.get(detail_url)
                detail_data = detail_response.json()
                detailed_meal = detail_data.get("meals", [])[0]
                all_meals.append(detailed_meal)

        with open(cache_file, "w") as f:
            json.dump(all_meals, f)

    for meal in all_meals:
        insert_recipe_with_ingredients(cursor, meal)

    connection.commit()


def find_recipes_by_ingredients(cursor, ingredients):
    """Find recipes that match all given ingredients"""
    normalized = [i.strip().lower() for i in ingredients]
    placeholders = ','.join(['%s'] * len(normalized))

    cursor.execute(f"""
        SELECT r.name, r.category, r.area
        FROM recipes r
        JOIN recipe_ingredients ri ON r.meal_id = ri.recipe_id
        JOIN ingredient_list il ON ri.ingredient_id = il.id
        WHERE il.name IN ({placeholders})
        GROUP BY r.meal_id, r.name, r.category, r.area
        HAVING COUNT(DISTINCT il.name) = %s;
    """, normalized + [len(normalized)])

    return cursor.fetchall()

def get_ingredients_from_api(meal_name):
    """Fetch full recipe data from TheMealDB API"""
    url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={meal_name}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        meals = data.get("meals")
        if not meals:
            return None

        meal = meals[0]

        # Extract ingredients and measures
        ingredients = []
        for i in range(1, 21):
            ingredient = meal.get(f"strIngredient{i}")
            measure = meal.get(f"strMeasure{i}")
            if ingredient and ingredient.strip():
                normalized = ingredient.strip().lower()
                ingredients.append((normalized, measure.strip() if measure else ""))

        return {
            "ingredients": ingredients,
            "region": meal.get("strArea", "Unknown"),
            "category": meal.get("strCategory", "Unknown"),
            "instructions": meal.get("strInstructions", "No instructions found.")
        }

    except requests.RequestException as e:
        print(f"API error: {e}")
        return None


def main():
    """Main application loop"""
    try:
        with psycopg2.connect(
            database=DATABASE,
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            # sslmode='require'
        ) as connection:
            with connection.cursor() as cursor:
                create_tables(cursor)
                preload_ingredient_cache(cursor)
                load_recipes_by_category(cursor, connection)

            while True:
                user_input = input("Enter ingredients separated by commas: ").strip()
                if not user_input:
                    print("You must enter at least one ingredient.")
                    continue

                ingredients = [i.strip().lower() for i in user_input.split(",") if i.strip()]
                if not ingredients:
                    print("No valid ingredients detected. Please try again.")
                    continue

                with connection.cursor() as cursor:
                    matched = find_recipes_by_ingredients(cursor, ingredients)

                if not matched:
                    print("\nNo matching recipes found.")
                    retry = input("Try again? (Y to retry / Q to quit): ").strip().lower()
                    if retry == 'q':
                        print("Bye!")
                        break
                    elif retry == 'y':
                        continue
                    else:
                        print("Invalid choice. Returning to input.")
                        continue

                print("\nMatching recipes:")
                for i, row in enumerate(matched, start=1):
                    name, category, area = row
                    print(f"{i}: {name} | Category: {category} | Area: {area}")

                while True:
                    print("\nWould you like to see full recipe? Enter number or 'Q' to quit")
                    choice = input("Your choice: ").strip().lower()

                    if choice == 'q':
                        print("Bye!")
                        return
                    elif choice.isdigit():
                        index = int(choice) - 1
                        if 0 <= index < len(matched):
                            selected_meal_name = matched[index][0]
                            recipe_data = get_ingredients_from_api(selected_meal_name)
                            if recipe_data:
                                print(f"\nFull recipe for: {selected_meal_name}")
                                print(f"Region: {recipe_data['region']} | Category: {recipe_data['category']}")
                                print("\nIngredients:")
                                for ingredient, measure in recipe_data["ingredients"]:
                                    print(f"- {ingredient}: {measure}")
                                print("\nInstructions:")
                                print(recipe_data["instructions"])
                                print("Bon appetit!")
                                return
                            else:
                                print("Recipe not found in API.")
                        else:
                            print("Invalid number. Please choose from the list.")
                    else:
                        print("Invalid input. Please enter a number or 'Q'.")
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")


if __name__ == "__main__":
     main()
