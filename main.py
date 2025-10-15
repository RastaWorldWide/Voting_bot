from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv
import os
import ssl

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBAPP_URL = os.getenv('WEBAPP_URL')
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBAPP_URL}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    button = types.KeyboardButton(
        text="Открыть Web App 🌐",
        web_app=types.WebAppInfo(url=WEBAPP_URL)
    )
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[button]],
        resize_keyboard=True
    )
    await message.answer("Привет! Открой мини-приложение 👇", reply_markup=keyboard)


@dp.message()
async def handle_web_app_data(message: types.Message):
    if hasattr(message, 'web_app_data') and message.web_app_data:
        data = message.web_app_data.data
        await message.answer(f"Получено из Web App:\n<code>{data}</code>", parse_mode="HTML")


async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)


def main():
    dp.startup.register(on_startup)

    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    web.run_app(app, host="0.0.0.0", port=3000)


if __name__ == "__main__":
    main()