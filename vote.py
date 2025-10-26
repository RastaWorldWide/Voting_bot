from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import json
from datetime import datetime
import os

from main import bot  # 👈 импортируем бота
from aiogram import types
import asyncio

VOTES_FILE = "votes.json"

app = FastAPI(title="Prosoft Voting API")

from fastapi.middleware.cors import CORSMiddleware

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
    chat_id: int  # 👈 добавим chat_id пользователя (из бота)

# === Эндпоинт голосования ===
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

        # === Отправляем сообщение пользователю ===
        text = "✅ Спасибо, ваш голос учтён! Подводить итоги будем 30 ноября 🎉"
        asyncio.create_task(bot.send_message(vote.chat_id, text))

        return {"status": "ok", "message": "Голос сохранён"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === Получить все голоса ===
@app.get("/api/votes")
async def get_votes():
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, "r", encoding="utf-8") as f:
            votes = json.load(f)
        return votes
    return []
