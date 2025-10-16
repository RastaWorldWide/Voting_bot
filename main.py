from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.web_app_info import WebAppInfo
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(BOT_TOKEN)

dp = Dispatcher(bot)

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    markup = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton('Открыть веб страницу', web_app=WebAppInfo(url="https://www.prosoft-people.ru")))
    await message.answer("Привет!", reply_markup=markup)


executor.start_polling(dp)