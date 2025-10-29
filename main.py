import os
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot)

app = FastAPI(title="Prosoft Voting API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VOTES_FILE = "votes.json"

class Vote(BaseModel):
    fio: str
    department: str
    nominee: str
    chat_id: int

@app.post("/api/votes")
async def submit_vote(vote: Vote):
    try:
        vote_data = vote.dict()
        vote_data["date"] = datetime.now().isoformat()

        votes = []
        if os.path.exists(VOTES_FILE):
            with open(VOTES_FILE, "r", encoding="utf-8") as f:
                votes = json.load(f)

        votes.append(vote_data)
        with open(VOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(votes, f, ensure_ascii=False, indent=2)

        asyncio.create_task(bot.send_message(
            vote.chat_id,
            f"Спасибо, {vote.fio}! Ваш голос за {vote.nominee} учтён 🎉"))

        return {"status": "ok", "message": "Голос сохранён"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/votes")
async def get_votes():
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_first_name = message.from_user.first_name or "друг"
    inline_markup = InlineKeyboardMarkup()
    inline_markup.add(
        InlineKeyboardButton(
            text="Проголосовать",
            web_app=WebAppInfo(url="https://www.prosoft-people.ru")
        )
    )
    await message.answer(
        f"Привет, {user_first_name}!\n"
        f"30 лет растем вместе!\n"
        f"Приглашаем тебя принять участие в номинации 'Люди Роста'\n"
        f"Голос каждого важен!",
        reply_markup=inline_markup
    )

async def start_bot():
    await dp.start_polling()

if __name__ == "__main__":
    import asyncio
    import logging
    import uvicorn

    logging.basicConfig(level=logging.INFO)

    async def main():
        # Запускаем polling бота
        logging.info("🚀 Запуск Telegram-бота...")
        bot_task = asyncio.create_task(dp.start_polling())

        # Запускаем FastAPI в том же loop'е
        logging.info("🌐 Запуск FastAPI...")
        config = uvicorn.Config(app, host="127.0.0.1", port=8000, loop="asyncio")
        server = uvicorn.Server(config)
        api_task = asyncio.create_task(server.serve())

        try:
            await asyncio.gather(bot_task, api_task)
        except KeyboardInterrupt:
            logging.info("🛑 Остановка по сигналу...")
            bot_task.cancel()
            api_task.cancel()

    asyncio.run(main())
