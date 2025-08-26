import psycopg2
import requests
from connect import DATABASE, USER, PASSWORD,HOST, PORT

connection = psycopg2.connect(database = DATABASE,
    user = USER,
    password = PASSWORD,
    host = HOST,
    port = PORT)

cursor = connection.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS recipes (
               id_recipe INTEGER PRIMARY KEY,
               meal_id TEXT UNIQUE,
               name TEXT,
               category TEXT,
               area TEXT,
               instructions TEXT
               )

''')
connection.commit()
