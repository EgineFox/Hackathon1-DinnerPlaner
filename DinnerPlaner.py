import psycopg2
import requests
from connect import DATABASE, USER, PASSWORD, HOST, PORT

def create_tables(cursor):
    '''Create necessary database tables'''
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            meal_id INTEGER UNIQUE,
            name TEXT,
            category TEXT,
            area TEXT,
            instructions TEXT
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingredients (
            id_ingredient SERIAL,
            recipe_id INTEGER REFERENCES recipes(meal_id),
            ingredient TEXT,
            PRIMARY KEY (recipe_id, ingredient)
        );
    """)


def load_recipes_from_api(cursor, connection, api_url):
    '''Load recipes from TheMealDB API and insert into DB'''
    response = requests.get(api_url)
    data = response.json()

    meals = data.get("meals", [])
    for meal in meals:
        # Insert recipe metadata
        cursor.execute("""
            INSERT INTO recipes (meal_id, name, category, area, instructions)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (meal_id) DO NOTHING
            RETURNING meal_id;
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
            # Insert up to 20 ingredients
            for i in range(1, 21):
                ingredient = meal.get(f"strIngredient{i}")
                if ingredient and ingredient.strip():
                    cursor.execute("""
                        INSERT INTO ingredients (recipe_id, ingredient)
                        VALUES (%s, %s)
                        ON CONFLICT (recipe_id, ingredient) DO NOTHING;
                    """, (recipe_id, ingredient.strip()))

    connection.commit()

def find_recipes_by_ingredients(cursor, ingredients):
    '''Find recipes that match all given ingredients'''
    placeholders = ','.join(['%s'] * len(ingredients))
    cursor.execute(f"""
        SELECT r.name, r.category, r.area
        FROM recipes r
        JOIN ingredients i ON r.meal_id = i.recipe_id
        WHERE LOWER(i.ingredient) IN ({placeholders})
        GROUP BY r.meal_id, r.name, r.category, r.area
        HAVING COUNT(DISTINCT LOWER(i.ingredient)) = %s;
    """, ingredients + [len(ingredients)])

    return cursor.fetchall()

def get_recipe_instructions(cursor, meal_name):
    '''Get recipe instructions from DB'''
    cursor.execute("""
        SELECT instructions
        FROM recipes
        WHERE LOWER(name) = %s;
    """, (meal_name.lower(),))
    result = cursor.fetchone()
    return result[0] if result else None

def get_ingredients_from_api(meal_name):
    '''Get full recipe data from TheMealDB API'''
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
                ingredients.append((ingredient.strip(), measure.strip() if measure else ""))

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
    '''Main application loop'''
    try:
        # Connect to PostgreSQL
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

            while True:
                user_input = input("Enter ingredients separated by commas: ")
                ingredients = [i.strip().lower() for i in user_input.split(",") if i.strip()]

                with connection.cursor() as cursor:
                    matched = find_recipes_by_ingredients(cursor, ingredients)

                if not matched:
                    print("\n  No matching recipes found.")
                    retry = input("Would you like to try again? (Y to retry / Q to quit): ").strip().lower()
                    if retry == 'q':
                        print("Bye!")
                        break
                    else:
                        continue
                else:
                    print("\nMatching recipes:")
                    for i, row in enumerate(matched, start=1):
                        name, category, area = row
                        print(f"{i}: {name} | Category: {category} | Area: {area}")

                    print("Would you like to see full recipe of one? Enter number or 'Q' to quit\n")
                    choice = input("Your choice: ").strip()
                    if choice.lower() == 'q':
                        print("Bye!")
                        break
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
                                break
                            else:
                                print("Recipe not found in API.")
                    else:
                        print("Invalid input.")
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")

if __name__ == "__main__":
    main()