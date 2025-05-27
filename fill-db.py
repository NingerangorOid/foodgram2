import json
import sqlite3

# Подключение к базе данных SQLite
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Чтение данных из JSON-файла
with open('ingredients.json', 'r', encoding='utf-8') as file:
    ingredients = json.load(file)

# Вставка данных в таблицу api_ingredient
for ingredient in ingredients:
    cursor.execute(
        '''
        INSERT INTO api_ingredient (name, measurement_unit)
        VALUES (?, ?)
        ''',
        (ingredient['name'], ingredient['measurement_unit'])
    )

# Сохранение изменений и закрытие соединения
conn.commit()
conn.close()

print("Данные успешно импортированы в таблицу api_ingredient.")