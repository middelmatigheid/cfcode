import sqlite3 as sq

db = sq.connect('cfcode.db')
cursor = db.cursor()


# Удаление базы данных
async def delete_tables():
    # Удаление таблицы пользователей
    # cursor.execute("DROP TABLE IF EXISTS users")

    # Удаление таблицы cf code'ов
    # cursor.execute("DROP TABLE IF EXISTS cfcodes")
    db.commit()


# Создание базы данных
async def create_tables():
    # Создание таблицы пользователей
    cursor.execute("CREATE TABLE IF NOT EXISTS users("
                   "user_id INTEGER PRIMARY_KEY, "  # Telegram id пользователя
                   "step TEXT, "  # Шаг, на котором находится пользователь
                   "page INTEGER, "  # Страница cf code'ов, которую пользователь просматривает
                   "text TEXT, "  # Текст, который будет сохранён в cf code
                   "cfcode_id TEXT, "  # Id cf code'а, с которым взаимодействует пользователь
                   "cfcode_num INTEGER)")  # Количество cf code'ов, созданных пользователем

    # Создание таблицы cf code'ов
    cursor.execute("CREATE TABLE IF NOT EXISTS cfcodes("
                   "cfcode_id TEXT PRIMARY KEY, "  # Id cfcode'а
                   "owner_id INTEGER, "  # Telegram id пользователя, создавшего cf code
                   "text TEXT, "  # Текст cf code'а
                   "date TEXT, "  # Дата и время создание cf code'а
                   "views INTEGER)")  # Количество использований cf code'а
    db.commit()


# Добавление нового пользователя в базу данных
async def add_new_user(user_id):
    cursor.execute(f"INSERT INTO users (user_id, step, page, text, cfcode_id, cfcode_num) VALUES ({user_id}, '', 1, '', '', 0)")
    db.commit()


# Поиск пользователя в базе данных по его telegram id
async def get_user_by_id(user_id):
    user = cursor.execute(f"SELECT * FROM users WHERE user_id == {user_id}").fetchone()
    if user is None:
        return False
    res = {'user_id': None, 'step': None, 'page': None, 'text': None, 'cfcode_id': None, 'cfcode_num': None}
    res_keys = list(res.keys())
    for i in range(len(user)):
        res[res_keys[i]] = user[i]
    return res


# Изменение шага, на котором находится пользователь
async def update_user_step(user_id, step):
    cursor.execute(f"UPDATE users SET step = '{step}' WHERE user_id == {user_id}")
    db.commit()


# Изменение страницы cf code'ов пользователя
async def update_user_page(user_id, page):
    cursor.execute(f"UPDATE users SET page = {page} WHERE user_id == {user_id}")
    db.commit()


# Изменение текста, который будет сохранен в cf code
async def update_user_text(user_id, text):
    cursor.execute(f"UPDATE users SET text = '{text}' WHERE user_id == {user_id}")
    db.commit()


# Изменение id cf code'а, с которым взаимодействует пользователь
async def update_user_cfcode_id(user_id, cfcode_id):
    cursor.execute(f"UPDATE users SET cfcode_id = '{cfcode_id}' WHERE user_id == {user_id}")
    db.commit()


# Поиск всех cf code'ов пользователя в базе данных по его telegram id
async def get_users_cfcodes(user_id):
    cfcodes = cursor.execute(f"SELECT * FROM cfcodes WHERE owner_id == {user_id}").fetchall()
    if cfcodes == []:
        return None
    res = []
    for cfcode in cfcodes:
        res.append({'cfcode_id': cfcode[0], 'owner_id': cfcode[1], 'text': cfcode[2], 'date': cfcode[3], 'views': cfcode[4]})
    return res


# Добавление нового cf code'а в базу данных
async def add_new_cfcode(owner_id, cfcode_id, text, date):
    cursor.execute(f"INSERT INTO cfcodes (cfcode_id, owner_id, text, date, views) VALUES ('{cfcode_id}', {owner_id}, '{text}', '{date}', 0)")
    cfcode_num = cursor.execute(f"SELECT cfcode_num FROM users WHERE user_id == {owner_id}").fetchone()
    cursor.execute(f"UPDATE users SET cfcode_num = {cfcode_num[0] + 1} WHERE user_id == {owner_id}")
    db.commit()


# Поиск cf code'а по его id
async def get_cfcode_by_id(cfcode_id):
    cfcode = cursor.execute(f"SELECT * FROM cfcodes WHERE cfcode_id == '{cfcode_id}'").fetchone()
    #print(cfcode)
    if cfcode is None:
        return None
    res = {'cfcode_id': None, 'owner_id': None, 'text': None, 'date': None, 'views': None}
    res_keys = ['cfcode_id', 'owner_id', 'text', 'date', 'views']
    for i in range(len(cfcode)):
        res[res_keys[i]] = cfcode[i]
    cursor.execute(f"UPDATE cfcodes SET views = {res['views'] + 1} WHERE cfcode_id == '{cfcode_id}'")
    db.commit()
    return res


# Изменение текста cf code'а
async def update_cfcode_text(cfcode_id, text):
    cursor.execute(f"UPDATE cfcodes SET text = '{text}' WHERE cfcode_id == '{cfcode_id}'")
    db.commit()


# Удаление cf code'а из базы данных
async def delete_cfcode(user_id, cfcode_id):
    cursor.execute(f"DELETE FROM cfcodes WHERE cfcode_id == '{cfcode_id}'")
    user = await get_user_by_id(user_id)
    cursor.execute(f'UPDATE users SET cfcode_num == {user["cfcode_num"] - 1}')
    db.commit()
