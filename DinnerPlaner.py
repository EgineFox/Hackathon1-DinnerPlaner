import psycopg2
import requests
from connect import DATABASE, USER, PASSWORD, HOST, PORT

# Create tables in the database
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

# Load recipes from TheMealDB API
def load_recipes_from_api(cursor, connection, api_url):
    response = requests.get(api_url)
    data = response.json()

    meals = data.get("meals", [])
    for meal in meals:
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
            for i in range(1, 21):
                ingredient = meal.get(f"strIngredient{i}")
                measure = meal.get(f"strMeasure{i}")
                if ingredient and ingredient.strip():
                    cursor.execute("""
                        INSERT INTO ingredients (recipe_id, ingredient, measure)
                        VALUES (%s, %s, %s);
                    """, (recipe_id, ingredient.strip(), measure.strip() if measure else None))

    connection.commit()

# Find recipes that match all given ingredients
def find_recipes_by_ingredients(cursor, ingredients):
    placeholders = ','.join(['%s'] * len(ingredients))
    cursor.execute(f"""
        SELECT r.name
        FROM recipes r
        JOIN ingredients i ON r.id_recipe = i.recipe_id
        WHERE LOWER(i.ingredient) IN ({placeholders})
        GROUP BY r.id_recipe, r.name
        HAVING COUNT(DISTINCT LOWER(i.ingredient)) = %s;
    """, ingredients + [len(ingredients)])

    return cursor.fetchall()

# Main function
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
                load_recipes_from_api(cursor, connection, "https://www.themealdb.com/api/json/v1/1/search.php?s=")

                user_input = input("Enter ingredients separated by commas: ")
                ingredients = [i.strip().lower() for i in user_input.split(",") if i.strip()]
                matched = find_recipes_by_ingredients(cursor, ingredients)

                print("\nMatching recipes:")
                for recipe in matched:
                    print("-", recipe[0])

    except psycopg2.Error as e:
        print(f"Database connection error: {e}")

if __name__ == "__main__":
    main()
