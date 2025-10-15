from flask import Flask, send_from_directory
from aiogram import Bot, Dispatcher, types
# from aiogram.utils import executor
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

# === Конфигурация ===
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBAPP_URL = os.getenv('WEBAPP_URL')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
app = Flask(__name__)

# === 1. Flask часть ===
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# === 2. aiogram часть ===
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    kb = [
        [types.KeyboardButton(
            text="Открыть Web App 🌐",
            web_app=types.WebAppInfo(url=WEBAPP_URL)
        )]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Привет! Открой мини-приложение 👇", reply_markup=keyboard)

# Когда Web App отправляет tg.sendData() → сюда прилетает web_app_data
@dp.message_handler(content_types=types.ContentType.WEB_APP_DATA)
async def handle_web_app_data(message: types.Message):
    data = message.web_app_data.data
    await message.answer(f"Получено из Web App:\n<code>{data}</code>", parse_mode="HTML")

# === 3. Запуск всего ===
async def run_aiogram():
    await dp.start_polling()

def run_flask():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    # Запускаем Flask и Aiogram параллельно
    loop = asyncio.get_event_loop()
    loop.create_task(run_aiogram())
    run_flask()
