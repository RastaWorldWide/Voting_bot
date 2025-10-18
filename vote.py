from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import json
from datetime import datetime
import os

VOTES_FILE = "votes.json"

app = FastAPI(title="Prosoft Voting API")

# === Модель данных для голоса ===
class Vote(BaseModel):
    fio: str
    department: str
    nominee: str

# === Эндпоинт для отправки голоса ===
@app.post("/api/votes")
async def submit_vote(vote: Vote):
    try:
        # Сохраняем дату голосования
        vote_data = vote.dict()
        vote_data["date"] = datetime.now().isoformat()

        # Читаем существующие голоса
        votes: List[dict] = []
        if os.path.exists(VOTES_FILE):
            with open(VOTES_FILE, "r", encoding="utf-8") as f:
                votes = json.load(f)

        # Добавляем новый голос
        votes.append(vote_data)

        # Сохраняем обратно
        with open(VOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(votes, f, ensure_ascii=False, indent=2)

        return {"status": "ok", "message": "Голос сохранён"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === (опционально) получить все голоса ===
@app.get("/api/votes")
async def get_votes():
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, "r", encoding="utf-8") as f:
            votes = json.load(f)
        return votes
    return []
