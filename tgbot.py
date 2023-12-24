from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup
import requests
import io
from PIL import Image
import random
import datetime
import cfcode as cf
import database as db

bot = Bot('BOT_TOKEN')
uri = f'https://api.telegram.org/botBOT_TOKEN/getFile?file_id='
uri_img = f'https://api.telegram.org/file/BOT_TOKEN/'
dp = Dispatcher(bot)


# Создание ReplyKeyboardMarkup
def make_keyboard(arr):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for elem in arr:
        keyboard.add(elem)
    return keyboard


# Начало работы
async def on_startup(_):
    await db.delete_tables()
    await db.create_tables()


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer(f'Привет, это бот, с помощью которого ты сможешь считывать и генерировать cf code\nДанный проект является лишь небольшим прототипом, основной концепции, в соответствии с чем далек от идеала и имеет возможность претерпевать различные изменения\nПри использовании, помни, что я всего на всего бедный школьник с незаурядными знаниями в программировании, будь вежлив и милосерден\nВыбери действие, чтобы продолжить', reply_markup=make_keyboard(['Считать код', 'Мои кода']))


# Обработка получаемых изображений
@dp.message_handler(content_types=['photo'])
async def cmd_photo(message: types.Message):
    user = await db.get_user_by_id(message.chat.id)
    if user is not False and user['step'] == 'read image':
        res = requests.get(uri + message.photo[-1].file_id)
        img_path = res.json()['result']['file_path']
        img = requests.get(uri_img + img_path)
        img = Image.open(io.BytesIO(img.content))
        res = await cf.detect_code_try(img)
        if res is None:
            await message.answer('Не удалось считать код, попробуй сделать другую фотографию')
        else:
            result = await db.get_cfcode_by_id(f'{res[1]} {res[2]} {res[0]}')
            if result is not None:
                await message.answer(result['text'])
                return
            await message.answer('Не удалось найти код в базе данных')
    elif user is not False and user['step'] == 'send image':
        res = requests.get(uri + message.photo[-1].file_id)
        img_path = res.json()['result']['file_path']
        img = requests.get(uri_img + img_path)
        img = Image.open(io.BytesIO(img.content))
        res = await cf.detect_code_try(img)
        if res is None:
            await message.answer('Не удалось считать код, попробуй отправить другую фотографию')
        elif await db.get_cfcode_by_id(f'{res[1]} {res[2]} {res[0]}') is None:
            offset = datetime.timezone(datetime.timedelta(hours=3))
            date = datetime.datetime.now(offset)
            await cf.generate_code(res[0], res[1], res[2], False)
            await db.add_new_cfcode(message.chat.id, f'{res[1]} {res[2]} {res[0]}', user['text'], str(date)[:19])
            await db.update_user_step(message.chat.id, '')
            await db.update_user_text(message.chat.id, '')
            photo = open(f'images//{res[1]} {res[2]} {res[0]}.png', 'rb')
            await bot.send_photo(message.chat.id, photo=photo, caption='Код добавлен, убедитесь в правильности считывания', reply_markup=make_keyboard(['Считать код', 'Мои кода']))
            photo.close()
        else:
            await message.answer('Данный код уже использован, попробуй другой')
    else:
        await message.answer('Неизвестная команда')


async def pages(message):
    cfcodes = await db.get_users_cfcodes(message.chat.id)
    user = await db.get_user_by_id(message.chat.id)
    if cfcodes is None:
        await message.answer('У тебя еще нет кодов, но ты можешь их сгенерировать', reply_markup=make_keyboard(
            ['Сгенерировать случайный', 'Загрузить изображение', 'Нарисовать код', 'Меню']))
    else:
        for i in range(len(cfcodes[(user['page'] - 1) * 5: user['page'] * 5])):
            photo = open(f'images//{cfcodes[(user["page"] - 1) * 5 + i]["cfcode_id"]}.png', 'rb')
            await bot.send_photo(message.chat.id, photo=photo, caption=f'{(user["page"] - 1) * 5 + i + 1}. Текст: {cfcodes[(user["page"] - 1) * 5 + i]["text"]}\nИспользований: {cfcodes[(user["page"] - 1) * 5 + i]["views"]}\nДата создания: {cfcodes[(user["page"] - 1) * 5 + i]["date"]}')

        if len(cfcodes) > user['page'] * 5 and user['page'] != 1:
            await message.answer(f'Страница {user["page"]} из {(len(cfcodes) + 4) // 5}', reply_markup=make_keyboard(['Следующая страница', 'Предыдущая страница', 'Редактировать код', 'Создать новый', 'Меню']))
        elif user['page'] != 1:
            await message.answer(f'Страница {user["page"]} из {(len(cfcodes) + 4) // 5}', reply_markup=make_keyboard(['Предыдущая страница', 'Редактировать код', 'Создать новый', 'Меню']))
        elif len(cfcodes) > user['page'] * 5:
            await message.answer(f'Страница {user["page"]} из {(len(cfcodes) + 4) // 5}', reply_markup=make_keyboard(['Следующая страница', 'Редактировать код', 'Создать новый', 'Меню']))
        else:
            await message.answer(f'Страница {user["page"]} из {(len(cfcodes) + 4) // 5}', reply_markup=make_keyboard(['Редактировать код', 'Создать новый', 'Меню']))


@dp.message_handler()
async def cmd_text(message: types.Message):
    user = await db.get_user_by_id(message.chat.id)

    if user is False:
        await db.add_new_user(message.chat.id)

    if message.text == 'Меню':
        await message.answer('Выбери действие, чтобы продолжить', reply_markup=make_keyboard(['Считать код', 'Мои кода']))

    elif message.text == 'Считать код':
        await db.update_user_step(message.chat.id, 'read image')
        await message.answer('Отправь изображение с кодом, обрежь изображение ровно по коду, чтобы больше не было ничего лишнего и расположи код так, чтобы стрелка, указывающая вправо, находилась под кодом')

    elif message.text == 'Мои кода':
        await db.update_user_page(message.chat.id, 1)
        await db.update_user_step(message.chat.id, 'page')
        await pages(message)

    elif user['step'] == 'page' and message.text == 'Следующая страница' and user['cfcode_num'] <= (user['page'] + 1) * 5:
        await db.update_user_page(message.chat.id, user['page'] + 1)
        await pages(message)

    elif user['step'] == 'page' and message.text == 'Предыдущая страница' and user['page'] - 1 != 0:
        await db.update_user_page(message.chat.id, user['page'] - 1)
        await pages(message)

    elif message.text == 'Редактировать код':
        await db.update_user_step(message.chat.id, 'edit')
        await message.answer('Укажите номер кода для редактирования (номер кода указан под фотографией)')

    elif user['step'] == 'edit':
        if not (message.text.isnumeric()) or int(message.text) < 1 or int(message.text) > user['cfcode_num']:
            await message.answer('Некорректный номер кода, попробуйте снова')
        else:
            cfcode = await db.get_users_cfcodes(message.chat.id)
            cfcode = cfcode[int(message.text) - 1]
            await db.update_user_cfcode_id(message.chat.id, cfcode['cfcode_id'])
            await db.update_user_step(message.chat.id, 'editing')
            photo = open(f'images//{cfcode["cfcode_id"]}.png', 'rb')
            await bot.send_photo(message.chat.id, photo=photo, caption='Выберите действие, чтобы продолжить', reply_markup=make_keyboard(['Изменить текст', 'Удалить код', 'Меню']))
            photo.close()

    elif user['step'] == 'editing' and message.text == 'Изменить текст':
        await db.update_user_step(message.chat.id, 'editing text')
        await message.answer('Отправь новый текст, который будет отображаться при сканировании кода')

    elif user['step'] == 'editing text':
        await db.update_cfcode_text(user['cfcode_id'], message.text)
        await db.update_user_step(message.chat.id, '')
        await message.answer('Текст успешно изменен', reply_markup=make_keyboard(['Считать код', 'Мои кода']))

    elif user['step'] == 'editing' and message.text == 'Удалить код':
        await db.update_user_step(message.chat.id, 'delete')
        await message.answer('Ты уверен, что хочешь удалить код?', reply_markup=make_keyboard(['Да', 'Нет', 'Меню']))

    elif user['step'] == 'delete' and message.text == 'Да':
        await db.delete_cfcode(message.chat.id, user['cfcode_id'])
        await db.update_user_step(message.chat.id, '')
        await message.answer('Код удален', reply_markup=make_keyboard(['Считать код', 'Мои кода']))

    elif user['step'] == 'delete' and message.text == 'Нет':
        await db.update_user_step(message.chat.id, '')
        await message.answer('Выберите действие, чтобы продолжить', reply_markup=make_keyboard(['Считать код', 'Мои кода']))

    elif message.text == 'Создать новый':
        await message.answer('Выбери действие, чтобы продолжить', reply_markup=make_keyboard(['Сгенерировать случайный', 'Загрузить изображение', 'Создать код', 'Меню']))

    elif message.text == 'Сгенерировать случайный':
        await db.update_user_step(message.chat.id, 'generate random')
        await message.answer('Отправь текст, который будет отображаться при сканировании кода')

    elif user['step'] == 'generate random':
        w = random.randint(3, 10)
        h = random.randint(2, w - 1)
        n = "".join(random.choices('0123456', k=h * w))
        while await db.get_cfcode_by_id(n) is not None:
            n = "".join(random.choices('0123456', k=h * w))
        image = await cf.generate_code(n, h, w, False, None, False)
        photo = open(f'images//{image}.png', 'rb')
        offset = datetime.timezone(datetime.timedelta(hours=3))
        date = datetime.datetime.now(offset)
        await db.add_new_cfcode(message.chat.id, image, message.text, str(date)[:19])
        await db.update_user_step(message.chat.id, '')
        await bot.send_photo(message.chat.id, photo=photo, caption='Ваш сгенерированный код', reply_markup=make_keyboard(['Считать код', 'Мои кода']))
        photo.close()

    elif message.text == 'Загрузить изображение':
        await db.update_user_step(message.chat.id, 'generate by image text')
        await message.answer('С помощью этой функции ты сможешь загрузить изображение, содержащее готовый код с твоей уникальной расцветкой, но для начала отправь текст, который будет отображаться при сканировании кода', reply_markup=make_keyboard(['Считать код', 'Мои кода']))

    elif user['step'] == 'generate by image text':
        await db.update_user_step(message.chat.id, 'send image')
        await db.update_user_text(message.chat.id, message.text)
        await message.answer('Отправь изображение')

    elif message.text == 'Создать код':
        await db.update_user_step(message.chat.id, 'text')
        await message.answer('С помощью этой функции ты сможешь создать небольшой код, учти, что процесс этот кропотливый и в случае нетерпеливости ты можешь воспользоваться функцией \'Загрузить изображение\', чтобы продолжить отправь текст, который будет отображаться при сканировании кода')

    elif user['step'] == 'text':
        await db.update_user_step(message.chat.id, 'draw code columns')
        await db.update_user_text(message.chat.id, message.text)
        await message.answer('Введи количество столбцов кода от 2 до 5')

    elif user['step'] == 'draw code columns':
        if not (message.text.isnumeric()) or int(message.text) < 2 or int(message.text) > 5:
            await message.answer('Некорректное количество столбцов, попробуй снова')
        else:
            await db.update_user_step(message.chat.id, 'draw code lines')
            await db.update_user_cfcode_id(message.chat.id, message.text)
            await message.answer(f'Введи количество строк от 1 до 5')

    elif user['step'] == 'draw code lines':
        if not (message.text.isnumeric()) or int(message.text) < 1 or int(message.text) > 5:
            await message.answer('Некорректное количество строк, попробуй снова')
        else:
            await db.update_user_step(message.chat.id, 'draw code')
            await db.update_user_cfcode_id(message.chat.id, f"{user['cfcode_id']} {message.text} {'7' * int(user['cfcode_id']) * int(message.text)}")
            await cf.generate_code('7' * int(user['cfcode_id']) * int(message.text), int(message.text), int(user['cfcode_id']), True, message.chat.id)
            photo = open(f'images//{message.chat.id}.png', 'rb')
            await bot.send_photo(message.chat.id, photo=photo, caption='Выбери цвет квадрата', reply_markup=make_keyboard(['Черный', 'Красный', 'Желтый', 'Зеленый', 'Голубой', 'Синий', 'Розовый', 'Меню']))
            photo.close()

    elif user['step'] == 'draw code':
        if message.text not in ['Черный', 'Красный', 'Желтый', 'Зеленый', 'Голубой', 'Синий', 'Розовый']:
            await message.answer('Некорректный цвет, попробуй снова')
        else:
            colors = {'Черный': 0, 'Красный': 1, 'Желтый': 2, 'Зеленый': 3, 'Голубой': 4, 'Синий': 5, 'Розовый': 6}
            n = str(user['cfcode_id']).split()[2]
            i = n.find('7')
            n = n[:i] + str(colors[message.text]) + n[i + 1:]
            await db.update_user_cfcode_id(message.chat.id, f"{str(user['cfcode_id']).split()[0]} {str(user['cfcode_id']).split()[1]} {n}")
            if n.count('7') == 0:
                image = await cf.generate_code(n, int(str(user['cfcode_id']).split()[1]), int(str(user['cfcode_id']).split()[0]), False, message.chat.id, False)
                if await db.get_cfcode_by_id(image) is None:
                    offset = datetime.timezone(datetime.timedelta(hours=3))
                    date = datetime.datetime.now(offset)
                    await db.add_new_cfcode(message.chat.id, image, user['text'], str(date)[:19])
                    photo = open(f'images//{image}.png', 'rb')
                    await bot.send_photo(message.chat.id, photo=photo, caption='Код добавлен', reply_markup=make_keyboard(['Считать код', 'Мои кода']))
                    photo.close()
                else:
                    await message.answer('Данный код уже использован, попробуй другой')
            else:
                await cf.generate_code(n, int(str(user['cfcode_id']).split()[1]), int(str(user['cfcode_id']).split()[0]), True, message.chat.id)
                photo = open(f'images//{message.chat.id}.png', 'rb')
                await bot.send_photo(message.chat.id, photo=photo, caption='Выбери цвет квадрата', reply_markup=make_keyboard(['Черный', 'Красный', 'Желтый', 'Зеленый', 'Голубой', 'Синий', 'Розовый', 'Меню']))
                photo.close()

    else:
        await message.answer(f'Неизвестная команда')

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
