import json
import sqlite3

# Подключение к базе данных SQLite
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Чтение данных из JSON-файла
with open('data/ingredients.json', 'r', encoding='utf-8') as file:
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

# conn = sqlite3.connect('db.sqlite3')
# cursor = conn.cursor()
# recipe = list(cursor.execute(
#         '''
#         SELECT name, image, text, cooking_time, pub_date, author_id FROM api_recipe WHERE id == 1
#         '''))
# for i in range(100):
#     for i in recipe:
#         print(i[1])
#         cursor.execute(
#             '''
#             INSERT INTO api_recipe (name, image, text, cooking_time, pub_date, author_id)
#             VALUES (?, ?, ?, ?, ?, ?);''', (i[0], i[1], i[2], i[3],
#             i[4], i[5]))
# conn.commit()
# conn.close()
# print('sas')
