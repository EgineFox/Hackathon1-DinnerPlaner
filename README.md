# 📌 Project  "Dinner Planer" 
Ingredient-based recipe search using TheMealDB API and Neon cloud database

# 📍 Introduction

What is this project?

An interactive Python application that allows users to:

•	Enter a list of ingredients

•	Retrieve recipes that include all specified items

•	View detailed instructions for the selected dish



Data storage:

All recipes and ingredients are stored in a PostgreSQL cloud database hosted on Neon, offering:

•	High availability

•	Strong security

•	Easy scalability


# 🧪 Technologies

Project stack:

1	Language: Python

2	Database: PostgreSQL (Neon cloud)

3	API: TheMealDB

4	Libraries: psycopg2, requests

5	DB Hosting: Neon.tech


# 🧩 Architecture

How it works:

•	On launch, tables recipes and ingredients are created

•	Data is fetched from the API and stored in Neon

•	User inputs ingredients → SQL query finds matches

•	Matching recipes are displayed → user can view full instructions


# 🔍 Usage Example

User scenario:
1.	Input: chicken stock, honey
2.	Output:
o	Katsu Chicken curry | Category: Chicken | Area: Japanese
o	General Tsos Chicken | Category: Chicken | Area: Chinese
o	Honey Balsamic Chicken with Crispy Broccoli & Potatoes | Category: Chicken | Area: American
4.	Recipe selection → ingredients and step-by-step instructions are shown
   
# 💡 Improvement Idea

Feature expansion: “Personal Culinary Assistant”

•🔐 User authentication
•📝 Save favorite recipes
•⭐ Ratings and comments
•📦 API response caching
•📱 Web interface or Telegram bot
•🌍 Multilingual support
