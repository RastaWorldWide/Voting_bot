# 🗳️ Voting Bot

Бот для проведения внутреннего голосования среди сотрудников с поддержкой уникальных голосов и валидации участников.

> ⚙️ **Стек**: Python, Telegram Bot API (`aiogram` или `pyTelegramBotAPI`), Excel (`.xlsx`) как файловое хранилище  

> 🌐 **Развёртывание**: Поддержка вебхуков через Nginx + HTTPS 

> 🧩 **Гибкость**: Возможность запуска нескольких инстансов 
---

## 📦 Основные возможности

- Двухэтапный процесс:  
  1. **Валидация пользователя** (по ФИО)  
  2. **Голосование** (только после успешной проверки)
- Гарантия **уникальности голоса** на человека (через `user_id` Telegram + email/ФИО)
- Хранение данных в Excel:  
  - `employees.xlsx` — реестр сотрудников  
  - `votes.xlsx` — журнал голосов
- Поддержка нескольких ботов/окружений (раздельные порты и файлы)
- Настройка через `.env` (токен, admin ID, порт, вебхук-домен)

---

## 🚀 Быстрый старт

### 1. Клонирование
```bash
git clone https://github.com/RastaWorldWide/Voting_bot.git
```
```bash
cd Voting_bot
```

### 2. Окружение и зависимости
```bash
python -m venv .venv
```
```bash
.venv\Scripts\activate
```
```bash
pip install -r requirements.txt
```
### 3. Настройка .env
```
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
WEBAPP_URL=https://prosoft-people.online/webhook
EMPLOYEES_FILE="C:\Users\user\Desktop\prosoft_staff.xls"
```

### 5. Запуск
```bash
python main.py
```