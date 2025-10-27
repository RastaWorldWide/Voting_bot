import os
import json
from datetime import datetime
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher, types
from aiogram.types.web_app_info import WebAppInfo
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot)

VOTES_FILE = "votes.json"

app = FastAPI(title="Prosoft Voting API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Модель данных ===
class Vote(BaseModel):
    fio: str
    department: str
    nominee: str
    chat_id: int  # передаём chat_id из Telegram WebApp

# === Эндпоинт голосования ===
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

        # === Отправка сообщения в Telegram ===
        asyncio.create_task(bot.send_message(
            vote.chat_id,
            "✅ Спасибо, ваш голос учтён! Подводить итоги будем 30 ноября 🎉"
        ))

        return {"status": "ok", "message": "Голос сохранён"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === Бот для кнопки "Открыть веб страницу" ===
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.KeyboardButton(
        "Открыть веб страницу",
        web_app=WebAppInfo(url="https://www.prosoft-people.ru")
    ))
    await message.answer("Привет!", reply_markup=markup)

# === Запуск бота вместе с FastAPI через uvicorn ===
async def start_bot():
    await dp.start_polling()

if __name__ == "__main__":
    import uvicorn
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot())
    uvicorn.run(app, host="0.0.0.0", port=8000)
