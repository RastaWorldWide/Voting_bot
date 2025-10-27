import os
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher, types
from aiogram.types.web_app_info import WebAppInfo
from dotenv import load_dotenv
import asyncio

load_dotenv()

# === Настройки бота ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot)

# === FastAPI ===
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
    chat_id: int  # добавляем chat_id

# === Эндпоинт для голосования ===
@app.post("/api/votes")
async def submit_vote(vote: Vote):
    try:
        vote_data = vote.dict()
        vote_data["date"] = datetime.now().isoformat()

        # Читаем старые голоса
        votes: List[dict] = []
        if os.path.exists(VOTES_FILE):
            with open(VOTES_FILE, "r", encoding="utf-8") as f:
                votes = json.load(f)

        votes.append(vote_data)

        # Сохраняем
        with open(VOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(votes, f, ensure_ascii=False, indent=2)

        # Отправка сообщения в Telegram (асинхронно)
        asyncio.create_task(bot.send_message(
            vote.chat_id,
            "Спасибо, ваш голос учтён. Подводить итоги будем 30 ноября"
        ))

        return {"status": "ok", "message": "Голос сохранён"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === (опционально) получить все голоса ===
@app.get("/api/votes")
async def get_votes():
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# === Приветствие в боте и кнопка веб-страницы ===
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.KeyboardButton(
        'Открыть веб страницу',
        web_app=WebAppInfo(url="https://www.prosoft-people.ru")
    ))
    await message.answer("Привет!", reply_markup=markup)

# === Запуск бота в фоне вместе с FastAPI ===
async def start_bot():
    await dp.start_polling()

# === Main для uvicorn ===
if __name__ == "__main__":
    import uvicorn
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot())
    uvicorn.run(app, host="0.0.0.0", port=8000)
