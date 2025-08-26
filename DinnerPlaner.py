import psycopg2
import requests
from connect import DATABASE, USER, PASSWORD, HOST, PORT

# Function to create the necessary tables in the database
def create_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id_recipe SERIAL PRIMARY KEY,
            meal_id TEXT UNIQUE,
            name TEXT,
            category TEXT,
            area TEXT,
            instructions TEXT
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingredients (
            id SERIAL PRIMARY KEY,
            recipe_id INTEGER REFERENCES recipes(id_recipe),
            ingredient TEXT,
            measure TEXT
        );
    """)

# Fetches a list of meals by category from TheMealDB API
def get_meals_by_category(category="Seafood"):
    url = f"https://www.themealdb.com/api/json/v1/1/filter.php?c={category}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get("meals", [])
    except requests.RequestException as e:
        print(f"Error fetching meals list: {e}")
        return []

# Fetches detailed information about a specific meal by its ID
def get_meal_details(meal_id):
    url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        meals = response.json().get("meals", [])
        return meals[0] if meals else None
    except requests.RequestException as e:
        print(f"Error fetching meal details for ID {meal_id}: {e}")
        return None
    
# Fetches a list of meals by ingridients
def get_meals_by_ingridient(ingridient)

# Saves a meal and its ingredients to the database
def save_meal_to_db(cursor, meal):
    cursor.execute("""
        INSERT INTO recipes (meal_id, name, category, area, instructions)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (meal_id) DO NOTHING
        RETURNING id_recipe;
    """, (
        meal["idMeal"],
        meal["strMeal"],
        meal["strCategory"],
        meal["strArea"],
        meal["strInstructions"]
    ))

    result = cursor.fetchone()
    if result:
        recipe_id = result[0]
        # Loop through up to 20 possible ingredients
        for i in range(1, 21):
            ingredient = meal.get(f"strIngredient{i}")
            measure = meal.get(f"strMeasure{i}")
            if ingredient and ingredient.strip():
                cursor.execute("""
                    INSERT INTO ingredients (recipe_id, ingredient, measure)
                    VALUES (%s, %s, %s);
                """, (recipe_id, ingredient.strip(), measure.strip() if measure else None))
        print(f"Recipe added: {meal['strMeal']}")
    else:
        print(f"Recipe already exists: {meal['strMeal']}")

# Main function to run the script
def main():
    try:
        with psycopg2.connect(
            database=DATABASE,
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT
        ) as connection:
            with connection.cursor() as cursor:
                create_tables(cursor)
                meals = get_meals_by_category("Seafood")
                for meal in meals:
                    details = get_meal_details(meal["idMeal"])
                    if details:
                        save_meal_to_db(cursor, details)
                connection.commit()
    except psycopg2.Error as db_error:
        print(f"Database connection error: {db_error}")

# Entry point of the script
if __name__ == "__main__":
    main()