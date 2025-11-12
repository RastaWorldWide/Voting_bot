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
BOT_TOKEN = os.getenv("BOT_TOKEN2")

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

VOTES_FILE = "votes2.json"


class Vote(BaseModel):
    fio: str
    department: str
    nominee: str
    chat_id: int


def load_employees_from_excel():
    df = pd.read_excel("/root/voting_bot/reg_lab_staff.xlsx")
    # Ожидаем, что в файле есть столбцы "ФИО" и "Отдел"
    employees = {}
    for _, row in df.iterrows():
        fio = str(row["ФИО"]).strip()
        dept = str(row["Подразделение"]).strip()
        if fio:
            employees[fio] = dept
    return employees

EMPLOYEES = load_employees_from_excel()
print(f"✅ Загружено {len(EMPLOYEES)} сотрудников для проверки ФИО")


@app.post("/api/votes")
async def submit_vote(vote: Vote):
    try:
        fio = vote.fio.strip()
        dept = vote.department.strip()

        # Проверка: есть ли ФИО в Excel
        if fio not in EMPLOYEES:
            raise HTTPException(status_code=400, detail=f"ФИО '{fio}' не найдено в списке сотрудников!")

        # Проверка: совпадает ли отдел
        correct_dept = EMPLOYEES[fio]
        if correct_dept.lower() != dept.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Отдел не совпадает с данными в системе ({correct_dept})."
            )

        # Сохранение голоса
        vote_data = vote.dict()
        vote_data["date"] = datetime.now().isoformat()

        votes = []
        if os.path.exists(VOTES_FILE):
            with open(VOTES_FILE, "r", encoding="utf-8") as f:
                votes = json.load(f)

        votes.append(vote_data)
        with open(VOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(votes, f, ensure_ascii=False, indent=2)

        # Сообщение в Telegram
        asyncio.create_task(bot.send_message(
            vote.chat_id,
            f"<b>Спасибо, {vote.fio}!</b>\n"
            f"Ваш голос за {vote.nominee} учтён.\n\n"
            f"Увидимся 26 декабря — на юбилее в MTS Live Hall.\n"
            f"Именно там мы назовём имена тех, кто помогает нам расти.",
            parse_mode="HTML"
        ))

        return {"status": "ok", "message": "Голос сохранён"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/validate")
async def validate_user(payload: dict):
    """
    Проверяет ФИО и отдел по Excel.
    Ожидаемый payload: { "fio": "Иванов Иван Иванович", "department": "Отдел" }
    """
    try:
        fio = payload.get("fio", "").strip()
        dept = payload.get("department", "").strip()
        if not fio or not dept:
            return {"valid": False}

        if fio not in EMPLOYEES:
            return {"valid": False}

        correct_dept = EMPLOYEES[fio]
        if correct_dept.lower() != dept.lower():
            return {"valid": False}

        return {"valid": True}
    except Exception as e:
        return {"valid": False, "error": str(e)}


@app.get("/api/votes")
async def get_votes():
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@app.get("/api/employees")
async def get_employees(department: str = None):
    if department:
        filtered = [fio for fio, dept in EMPLOYEES.items() if dept.lower() == department.lower()]
    else:
        filtered = list(EMPLOYEES.keys())
    return {"employees": filtered}

@app.get("/api/departments")
async def get_departments():
    # Берём уникальные отделы из Excel
    departments = list(set(EMPLOYEES.values()))
    departments.sort()
    return {"departments": departments}


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_first_name = message.from_user.first_name or "друг"
    inline_markup = InlineKeyboardMarkup()
    inline_markup.add(
        InlineKeyboardButton(
            text="🗳 Проголосовать",
            web_app=WebAppInfo(url="https://www.prosoft-people.ru")
        )
    )
    await message.answer(
        f"<b>Привет, {user_first_name}!</b>\n\n"
        f"Мы запускаем номинацию <b>«Люди роста»</b> — важной части юбилея «Прософт-Системы».\n\n"
        f"Вы можете отдать голос за коллегу, который, по вашему мнению, по-настоящему вдохновляет и двигает команду вперёд!\n"
        f"<b>Голос — у каждого. Решение — общее.</b>",
        reply_markup=inline_markup,
        parse_mode="HTML"
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
        config = uvicorn.Config(app, host="0.0.0.0", port=8001, loop="asyncio")
        server = uvicorn.Server(config)
        api_task = asyncio.create_task(server.serve())

        try:
            await asyncio.gather(bot_task, api_task)
        except KeyboardInterrupt:
            logging.info("🛑 Остановка по сигналу...")
            bot_task.cancel()
            api_task.cancel()

    asyncio.run(main())
