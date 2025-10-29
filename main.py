import os
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo
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


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_first_name = message.from_user.first_name or "друг"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(
        "Открыть веб страницу",
        web_app=WebAppInfo(url="https://www.prosoft-people.ru")
    ))
    await message.answer(
        f"👋 Привет, {user_first_name}! Нажмите кнопку ниже, чтобы проголосовать:",
        reply_markup=markup
    )
async def start_bot():
    await dp.start_polling()

if __name__ == "__main__":
    import uvicorn
    import logging

    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()
    logging.info("🚀 Запуск Telegram-бота...")
    loop.create_task(start_bot())
    logging.info("🌐 Запуск FastAPI через uvicorn...")
    uvicorn.run(app, host="127.0.0.1", port=8000)

