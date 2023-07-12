import logging
import sqlite3
import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram import executor

# Настройки бота
API_TOKEN = 'YourToken'

# Настройки базы данных
DB_FILE = 'database.sql'

# Id канала
CHANNEL_ID = 'YourId'

# Инициализация бота и хранилища состояний
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Настройка логгирования
logging.basicConfig(level=logging.INFO)

# Подключение к базе данных
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT,
                    last_name TEXT,
                    department TEXT,
                    position TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS issues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    description TEXT,
                    category TEXT,
                    urgency TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id))''')
conn.commit()

# Команда для старта бота
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.reply("Привет! Для регистрации отправь /register")

# Команда для регистрации пользователя
@dp.message_handler(commands=['register'])
async def cmd_register(message: types.Message):
    await message.reply("Введите свое имя:")
    await RegisterStates.first_name.set()

# Состояния для регистрации
class RegisterStates(StatesGroup):
    first_name = State()
    last_name = State()
    department = State()
    position = State()

# Обработка имени пользователя
@dp.message_handler(state=RegisterStates.first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['first_name'] = message.text
    await message.reply("Введите свою фамилию:")
    await RegisterStates.last_name.set()

# Обработка фамилии пользователя
@dp.message_handler(state=RegisterStates.last_name)
async def process_last_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['last_name'] = message.text
    await message.reply("Выберите отдел:",
                        reply_markup=types.ReplyKeyboardMarkup(
                            keyboard=[
                                [types.KeyboardButton(text='Маркетинговый отдел')],
                                [types.KeyboardButton(text='IT отдел')],
                                [types.KeyboardButton(text='Финансовый отдел')],
                                [types.KeyboardButton(text='Отдел кадров')],
                            ],
                            one_time_keyboard=True,
                            resize_keyboard=True
                        ))
    await RegisterStates.department.set()

# Обработка отдела пользователя
@dp.message_handler(state=RegisterStates.department)
async def process_department(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['department'] = message.text
    await message.reply("Введите свою должность:")
    await RegisterStates.position.set()

# Обработка должности пользователя
@dp.message_handler(state=RegisterStates.position)
async def process_position(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['position'] = message.text
    await message.reply("Регистрация успешно завершена!! Теперь можете сформировать заявку /create_issue")
    await state.finish()

    # Сохранение информации о пользователе в базу данных
    cursor.execute("INSERT INTO users (first_name, last_name, department, position) VALUES (?, ?, ?, ?)",
                   (data['first_name'], data['last_name'], data['department'], data['position']))
    conn.commit()

# Команда для создания заявки
@dp.message_handler(commands=['create_issue'])
async def cmd_create_issue(message: types.Message):
    await message.reply("Введите описание проблемы:")
    await CreateIssueStates.description.set()

# Состояния для создания заявки
class CreateIssueStates(StatesGroup):
    description = State()
    category = State()
    urgency = State()

# Обработка описания проблемы
@dp.message_handler(state=CreateIssueStates.description)
async def process_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['description'] = message.text
    await message.reply("Выберите категорию проблемы:",
                        reply_markup=types.ReplyKeyboardMarkup(
                            keyboard=[
                                [types.KeyboardButton(text='Интернет')],
                                [types.KeyboardButton(text='Принтер')],
                                [types.KeyboardButton(text='Сервер')],
                                [types.KeyboardButton(text='Другое')],
                            ],
                            one_time_keyboard=True,
                            resize_keyboard=True
                        ))
    await CreateIssueStates.category.set()

# Обработка категории проблемы
@dp.message_handler(state=CreateIssueStates.category)
async def process_category(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['category'] = message.text
    if data['category'] == 'Другое':
        await message.reply("Опишите проблему:")
        await CreateIssueStates.description.set()
    else:
        await message.reply("Выберите срочность проблемы:",
                            reply_markup=types.ReplyKeyboardMarkup(
                                keyboard=[
                                    [types.KeyboardButton(text='Срочно')],
                                    [types.KeyboardButton(text='Не срочно')],
                                    [types.KeyboardButton(text='Не важно')],
                                ],
                                one_time_keyboard=True,
                                resize_keyboard=True
                            ))
        await CreateIssueStates.urgency.set()

# Обработка срочности проблемы
@dp.message_handler(state=CreateIssueStates.urgency)
async def process_urgency(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['urgency'] = message.text
    await state.finish()

    # Сохранение заявки в базу данных
    cursor.execute("INSERT INTO issues (user_id, description, category, urgency) VALUES (?, ?, ?, ?)",
                   (message.from_user.id, data['description'], data['category'], data['urgency']))
    conn.commit()

    await message.reply("Заявка успешно создана!")

    # Отправка заявки на канал администратору (замените YOUR_CHANNEL на реальный канал)
    await bot.send_message(CHANNEL_ID, text=f"Новая заявка:\n"
                                                         f"Пользователь: {message.from_user.first_name} {message.from_user.last_name}\n"
                                                         f"Описание: {data['description']}\n"
                                                         f"Категория: {data['category']}\n"
                                                         f"Срочность: {data['urgency']}")

# Запуск бота
if __name__ == '__main__':

    executor.start_polling(dp, skip_updates=True)