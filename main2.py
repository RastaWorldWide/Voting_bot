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
from fastapi.responses import HTMLResponse


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN2")

bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot)

app = FastAPI(title="Prosoft Voting API (RegLab)")

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


# 🔐 ЛОКАЛЬНАЯ база — только для валидации (вход разрешён ТОЛЬКО этим сотрудникам)
def load_local_employees():
    df = pd.read_excel("/root/voting_bot/reg_lab_staff.xlsx")  # ← ВАЖНО: reg_lab_staff.xlsx
    employees = {}
    for _, row in df.iterrows():
        fio = str(row["ФИО"]).strip()
        dept = str(row["Подразделение"]).strip()
        if fio:
            employees[fio] = dept
    return employees

LOCAL_EMPLOYEES = load_local_employees()
print(f"✅ Локальная база (для входа): {len(LOCAL_EMPLOYEES)} сотрудников")


# 🌐 ОБЩАЯ база — для отображения кандидатов (все из обоих Excel)
def load_all_employees_for_nominees():
    all_emps = {}
    # 1. Основной штат
    try:
        df1 = pd.read_excel("/root/voting_bot/prosoft_staff.xlsx")
        for _, row in df1.iterrows():
            fio = str(row["ФИО"]).strip()
            dept = str(row["Подразделение"]).strip()
            if fio and fio not in all_emps:
                all_emps[fio] = dept
    except Exception as e:
        print("⚠️ Ошибка загрузки prosoft_staff.xlsx:", e)

    # 2. Реглаб
    try:
        df2 = pd.read_excel("/root/voting_bot/reg_lab_staff.xlsx")
        for _, row in df2.iterrows():
            fio = str(row["ФИО"]).strip()
            dept = str(row["Подразделение"]).strip()
            if fio and fio not in all_emps:
                all_emps[fio] = dept
    except Exception as e:
        print("⚠️ Ошибка загрузки reg_lab_staff.xlsx:", e)

    return all_emps

ALL_EMPLOYEES = load_all_employees_for_nominees()
print(f"🌍 Общая база (для номинации): {len(ALL_EMPLOYEES)} сотрудников")


@app.post("/api/votes")
async def submit_vote(vote: Vote):
    try:
        fio = vote.fio.strip()
        dept = vote.department.strip()
        nominee = vote.nominee.strip()

        # 🔐 Проверка: голосующий — только из ЛОКАЛЬНОЙ базы (reg_lab)
        if fio not in LOCAL_EMPLOYEES:
            raise HTTPException(status_code=400, detail=f"ФИО '{fio}' не найдено в списке сотрудников RegLab.")

        correct_dept = LOCAL_EMPLOYEES[fio]
        if correct_dept.lower() != dept.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Отдел не совпадает с данными в системе ({correct_dept})."
            )

        # 🎯 Номинант — НЕ проверяется на принадлежность
        if nominee not in ALL_EMPLOYEES:
            print(f"ℹ️ Нестандартный номинант: '{nominee}' не найден ни в одном Excel. Принимаем голос.")

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
            f"Ваш голос за <b>{vote.nominee}</b> учтён.\n\n"
            f"Увидимся 26 декабря — на юбилее в MTS Live Hall.\n"
            f"Именно там мы назовём имена тех, кто помогает нам расти.",
            parse_mode="HTML"
        ))

        return {"status": "ok", "message": "Голос сохранён"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении голоса: {str(e)}")


@app.post("/api/validate")
async def validate_user(payload: dict):
    """
    Проверяет ФИО и отдел ТОЛЬКО по локальной базе (reg_lab_staff.xlsx).
    """
    try:
        fio = payload.get("fio", "").strip()
        dept = payload.get("department", "").strip()
        if not fio or not dept:
            return {"valid": False}

        if fio not in LOCAL_EMPLOYEES:
            return {"valid": False}

        correct_dept = LOCAL_EMPLOYEES[fio]
        return {"valid": correct_dept.lower() == dept.lower()}
    except Exception as e:
        print("❌ Ошибка валидации:", e)
        return {"valid": False}


@app.get("/api/votes")
async def get_votes():
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@app.get("/api/employees")
async def get_employees(department: str = None):
    """
    Возвращает список ФИО для выбора номинанта — из ОБЩЕЙ базы.
    """
    if department:
        filtered = [
            fio for fio, dept in ALL_EMPLOYEES.items()
            if dept.lower() == department.lower()
        ]
    else:
        filtered = list(ALL_EMPLOYEES.keys())
    return {"employees": filtered}


@app.get("/api/departments")
async def get_departments():
    departments = list(set(ALL_EMPLOYEES.values()))
    departments.sort()
    return {"departments": departments}


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_first_name = message.from_user.first_name or "друг"
    inline_markup = InlineKeyboardMarkup()
    inline_markup.add(
        InlineKeyboardButton(
            text="🗳 Проголосовать",
            web_app=WebAppInfo(url="https://www.prosoft-people.online")
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


@app.get("/", response_class=HTMLResponse)
async def serve_webapp():
    with open("/root/voting_bot/index2.html", "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import logging
    import uvicorn

    logging.basicConfig(level=logging.INFO)

    async def main():
        logging.info("🚀 Запуск Telegram-бота (RegLab)...")
        bot_task = asyncio.create_task(dp.start_polling())

        logging.info("🌐 Запуск FastAPI на порту 8001...")
        config = uvicorn.Config(app, host="0.0.0.0", port=8001, loop="asyncio")
        server = uvicorn.Server(config)
        api_task = asyncio.create_task(server.serve())

        try:
            await asyncio.gather(bot_task, api_task)
        except KeyboardInterrupt:
            logging.info("🛑 Остановка бота и API...")
            bot_task.cancel()
            api_task.cancel()

    asyncio.run(main())
