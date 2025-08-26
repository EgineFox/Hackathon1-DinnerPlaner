import psycopg2
import requests
from connect import DATABASE, USER, PASSWORD,HOST, PORT

connection = psycopg2.connect(database = DATABASE,
    user = USER,
    password = PASSWORD,
    host = HOST,
    port = PORT)

cursor = connection.cursor()