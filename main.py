import os
import json
from datetime import datetime
from typing import List
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from aiogram import Bot, Dispatcher, types
from aiogram.types.web_app_info import WebAppInfo
import asyncio

# ===== Настройки =====
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot)
VOTES_FILE = "votes.json"

# ===== FastAPI =====
app = FastAPI(title="Prosoft Voting API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # временно
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Vote(BaseModel):
    fio: str
    department: str
    nominee: str
    chat_id: int   # <- сюда передаём chat_id пользователя

@app.post("/api/votes")
async def submit_vote(vote: Vote):
    try:
        vote_data = vote.dict()
        vote_data["date"] = datetime.now().isoformat()

        votes: List[dict] = []
        if os.path.exists(VOTES_FILE):
            with open(VOTES_FILE, "r", encoding="utf-8") as f:
                votes = json.load(f)
        votes.append(vote_data)
        with open(VOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(votes, f, ensure_ascii=False, indent=2)

        # ===== Отправляем сообщение в бота =====
        try:
            await bot.send_message(vote.chat_id, "✅ Спасибо! Ваш голос учтён. Подводить итоги будем 30 ноября.")
        except Exception as e:
            print(f"Ошибка при отправке Telegram-сообщения: {e}")

        return {"status": "ok", "message": "Голос сохранён"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== Aiogram команды =====
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.KeyboardButton(
        'Открыть веб страницу',
        web_app=WebAppInfo(url="https://www.prosoft-people.ru")
    ))
    await message.answer("Привет!", reply_markup=markup)

# ===== Запуск бота вместе с FastAPI =====
@app.on_event("startup")
async def on_startup():
    asyncio.create_task(dp.start_polling())
