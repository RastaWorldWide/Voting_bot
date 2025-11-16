import os
import json
import asyncio
import fcntl
import tempfile
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
BINDINGS_FILE = "user_bindings.json"  # ← новый файл привязок


class Vote(BaseModel):
    fio: str
    department: str
    nominee: str
    chat_id: int


# 🔐 ЛОКАЛЬНАЯ база — только для валидации
def load_local_employees():
    df = pd.read_excel("/root/voting_bot/prosoft_staff.xlsx")
    employees = {}
    for _, row in df.iterrows():
        fio = str(row["ФИО"]).strip()
        dept = str(row["Подразделение"]).strip()
        if fio:
            employees[fio] = dept
    return employees

LOCAL_EMPLOYEES = load_local_employees()
LOCAL_DEPARTMENTS = sorted(set(LOCAL_EMPLOYEES.values()))


# 🌐 ОБЩАЯ база — для кандидатов
def load_all_employees_for_nominees():
    all_emps = {}
    try:
        df1 = pd.read_excel("/root/voting_bot/prosoft_staff.xlsx")
        for _, row in df1.iterrows():
            fio = str(row["ФИО"]).strip()
            dept = str(row["Подразделение"]).strip()
            if fio and fio not in all_emps:
                all_emps[fio] = dept
    except Exception as e:
        print("⚠️ Ошибка загрузки prosoft_staff.xlsx:", e)

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


# 🔒 Вспомогательные функции
def load_bindings():
    if os.path.exists(BINDINGS_FILE):
        try:
            with open(BINDINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_bindings(bindings):
    with tempfile.NamedTemporaryFile(mode="w", dir=".", delete=False, encoding="utf-8") as tmp:
        json.dump(bindings, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, BINDINGS_FILE)

def safe_save_votes(votes_dict: dict, filepath: str = VOTES_FILE):
    dir_path = os.path.dirname(filepath) or "."
    with tempfile.NamedTemporaryFile(mode="w", dir=dir_path, delete=False, encoding="utf-8") as tmp:
        json.dump(votes_dict, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    with open(filepath, "a+") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            os.replace(tmp_path, filepath)
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


# ✅ /api/validate — фиксирует привязку chat_id → fio
@app.post("/api/validate")
async def validate_user(payload: dict):
    try:
        fio = payload.get("fio", "").strip()
        dept = payload.get("department", "").strip()
        chat_id = payload.get("chat_id")

        if not fio or not dept or not chat_id:
            return {"valid": False}

        # 1. Базовая валидация по Excel
        if fio not in LOCAL_EMPLOYEES or LOCAL_EMPLOYEES[fio].lower() != dept.lower():
            return {"valid": False}

        # 2. Загружаем привязки
        bindings = load_bindings()
        chat_key = str(chat_id)

        # 3. Если уже привязан — проверяем соответствие
        if chat_key in bindings:
            return {"valid": bindings[chat_key] == fio}

        # 4. Новый chat_id — привязываем
        bindings[chat_key] = fio
        save_bindings(bindings)
        return {"valid": True}

    except Exception as e:
        print("❌ Ошибка в /api/validate:", e)
        return {"valid": False}


# ✅ /api/votes — проверяет, что fio соответствует привязанному
@app.post("/api/votes")
async def submit_vote(vote: Vote):
    try:
        fio = vote.fio.strip()
        dept = vote.department.strip()
        nominee = vote.nominee.strip()
        chat_id = vote.chat_id

        # 1. Валидация (уже включает проверку привязки)
        #    Но делаем явно для надёжности
        bindings = load_bindings()
        chat_key = str(chat_id)
        if chat_key in bindings and bindings[chat_key] != fio:
            raise HTTPException(400, "Вы не можете голосовать за другого человека.")

        # 2. Базовая проверка по Excel
        if fio not in LOCAL_EMPLOYEES:
            raise HTTPException(400, "ФИО не найдено в списке сотрудников.")
        if LOCAL_EMPLOYEES[fio].lower() != dept.lower():
            raise HTTPException(400, "Отдел не совпадает с данными в системе.")

        # 3. Загрузка голосов
        votes = {}
        if os.path.exists(VOTES_FILE):
            with open(VOTES_FILE, "r", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        votes = {str(v.get("chat_id")): v for v in data if v.get("chat_id")}
                    else:
                        votes = data
                except Exception as e:
                    print(f"⚠️ Ошибка парсинга {VOTES_FILE}: {e}")
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        # 4. Уникальность по chat_id
        if chat_key in votes:
            existing = votes[chat_key]
            raise HTTPException(
                status_code=403,
                detail=f"Вы уже голосовали за {existing['nominee']}."
            )

        # 5. Сохранение
        vote_data = vote.dict()
        vote_data["date"] = datetime.now().isoformat()
        votes[chat_key] = vote_data
        safe_save_votes(votes, VOTES_FILE)

        # 6. Уведомление
        if chat_id:
            asyncio.create_task(bot.send_message(
                chat_id,
                f"<b>Спасибо, {fio}!</b>\n"
                f"Ваш голос за <b>{nominee}</b> учтён.\n\n"
                f"Увидимся 26 декабря — на юбилее в MTS Live Hall.",
                parse_mode="HTML"
            ))

        return {"status": "ok", "message": "Голос сохранён"}

    except HTTPException:
        raise
    except Exception as e:
        print("❌ Ошибка в /api/votes:", repr(e))
        raise HTTPException(status_code=500, detail="Ошибка сервера.")


@app.get("/api/employees")
async def get_employees(department: str = None):
    if department:
        filtered = [fio for fio, dept in ALL_EMPLOYEES.items() if dept.lower() == department.lower()]
    else:
        filtered = list(ALL_EMPLOYEES.keys())
    return {"employees": filtered}


@app.get("/api/departments")
async def get_departments():
    return {"departments": LOCAL_DEPARTMENTS}


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_first_name = message.from_user.first_name or "друг"
    inline_markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🗳 Проголосовать", web_app=WebAppInfo(url="https://www.prosoft-people.ru"))
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
    with open("/root/voting_bot/index.html", "r", encoding="utf-8") as f:
        return f.read()


# === Запуск ===
if __name__ == "__main__":
    import logging
    import uvicorn

    logging.basicConfig(level=logging.INFO)

    async def main():
        logging.info("🚀 Запуск Telegram-бота...")
        bot_task = asyncio.create_task(dp.start_polling())

        logging.info("🌐 Запуск FastAPI на порту 8000...")
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
        server = uvicorn.Server(config)
        api_task = asyncio.create_task(server.serve())

        try:
            await asyncio.gather(bot_task, api_task)
        except KeyboardInterrupt:
            logging.info("🛑 Остановка бота и API...")
            bot_task.cancel()
            api_task.cancel()

    asyncio.run(main())