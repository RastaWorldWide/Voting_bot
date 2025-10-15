from flask import Flask, send_from_directory
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv
import os
import asyncio
import threading

load_dotenv()

# === Конфигурация ===
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBAPP_URL = os.getenv('WEBAPP_URL')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()  # Теперь без передачи bot
app = Flask(__name__)


# === 1. Flask часть ===
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)


# === 2. aiogram часть ===
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    kb = [
        [types.KeyboardButton(
            text="Открыть Web App 🌐",
            web_app=types.WebAppInfo(url=WEBAPP_URL)
        )]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Привет! Открой мини-приложение 👇", reply_markup=keyboard)


@dp.message()
async def handle_web_app_data(message: types.Message):
    if hasattr(message, 'web_app_data') and message.web_app_data:
        data = message.web_app_data.data
        await message.answer(f"Получено из Web App:\n<code>{data}</code>", parse_mode="HTML")


# === 3. Запуск всего ===
async def run_aiogram():
    await dp.start_polling(bot)  # bot передается здесь


def run_flask():
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)


if __name__ == "__main__":
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Запускаем бота в основном потоке
    asyncio.run(run_aiogram())