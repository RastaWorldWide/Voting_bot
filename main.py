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
import pandas as pd

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

# ----------------- Загрузка сотрудников -----------------
def load_employees_from_excel():
    df = pd.read_excel("/root/telegram_webapp/prosoft_staff.xls")
    employees = {}
    for _, row in df.iterrows():
        fio = str(row["ФИО"]).strip().replace("\u00A0", " ")
        dept = str(row["Подразделение"]).strip().replace("\u00A0", " ")
        if fio:
            employees[fio] = dept
    employees_norm = {k.lower(): v.lower() for k, v in employees.items()}
    return employees, employees_norm

EMPLOYEES, EMPLOYEES_NORM = load_employees_from_excel()
print(f"✅ Загружено {len(EMPLOYEES)} сотрудников для проверки ФИО")

# ----------------- API -----------------
@app.post("/api/validate")
async def validate_user(payload: dict):
    fio = payload.get("fio", "").strip().replace("\u00A0", " ")
    dept = payload.get("department", "").strip().replace("\u00A0", " ")
    if not fio or not dept:
        return {"valid": False}

    if fio.lower() not in EMPLOYEES_NORM:
        return {"valid": False}

    if EMPLOYEES_NORM[fio.lower()] != dept.lower():
        return {"valid": False}

    return {"valid": True}

@app.post("/api/votes")
async def submit_vote(vote: Vote):
    fio = vote.fio.strip().replace("\u00A0", " ")
    dept = vote.department.strip().replace("\u00A0", " ")

    if fio.lower() not in EMPLOYEES_NORM:
        raise HTTPException(status_code=400, detail=f"ФИО '{fio}' не найдено!")

    if EMPLOYEES_NORM[fio.lower()] != dept.lower():
        raise HTTPException(status_code=400, detail=f"Отдел не совпадает с данными ({EMPLOYEES[fio]})")

    vote_data = vote.dict()
    vote_data["date"] = datetime.now().isoformat()

    votes = []
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, "r", encoding="utf-8") as f:
            votes = json.load(f)
    votes.append(vote_data)
    with open(VOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(votes, f, ensure_ascii=False, indent=2)

    asyncio.create_task(bot.send_message(vote.chat_id, f"Спасибо, {vote.fio}! Ваш голос за {vote.nominee} учтён 🎉"))
    return {"status": "ok", "message": "Голос сохранён"}

@app.get("/api/departments")
async def get_departments():
    departments = list(set(EMPLOYEES.values()))
    departments.sort()
    return {"departments": departments}

@app.get("/api/votes")
async def get_votes():
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# ----------------- Telegram бот -----------------
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_first_name = message.from_user.first_name or "друг"
    inline_markup = InlineKeyboardMarkup()
    inline_markup.add(InlineKeyboardButton(text="🗳 Проголосовать", web_app=WebAppInfo(url="https://www.prosoft-people.ru")))
    await message.answer(
        f"Привет, {user_first_name}! 👋\n\n"
        f"✨ <b>30 лет — растём вместе!</b>\n"
        f"В честь юбилея запускаем номинацию <b>«Люди Роста»</b>.\n\n"
        f"🗳 <b>Твой голос — важен!</b>",
        reply_markup=inline_markup,
        parse_mode="HTML"
    )

# ----------------- Запуск -----------------
async def start_bot():
    await dp.start_polling()

if __name__ == "__main__":
    import logging
    import uvicorn

    logging.basicConfig(level=logging.INFO)

    async def main():
        logging.info("🚀 Запуск Telegram-бота...")
        bot_task = asyncio.create_task(dp.start_polling())

        logging.info("🌐 Запуск FastAPI...")
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
        server = uvicorn.Server(config)
        api_task = asyncio.create_task(server.serve())

        try:
            await asyncio.gather(bot_task, api_task)
        except KeyboardInterrupt:
            logging.info("🛑 Остановка...")
            bot_task.cancel()
            api_task.cancel()

    asyncio.run(main())
