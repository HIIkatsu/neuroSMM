
NeuroSMM Telegram Mini App

Это панель управления для вашего SMM Telegram бота.

Стек:
- FastAPI (backend API)
- Telegram Mini App (frontend)
- Vanilla JS + Telegram WebApp SDK

Запуск локально:

1. Установить зависимости

pip install fastapi uvicorn

2. Запустить API

uvicorn miniapp_server:app --reload --port 8000

3. Открыть Mini App

http://localhost:8000/miniapp/index.html

Для Telegram Mini App нужен HTTPS.
Когда будете переносить на сервер — используйте:
- VPS
- Railway
- Render
- Fly.io

Структура:

miniapp_server.py — API
miniapp/ — интерфейс Mini App

Эндпоинты API:

GET /api/channels
POST /api/channels/select
GET /api/drafts
POST /api/drafts/create
POST /api/drafts/publish
GET /api/plan
POST /api/plan/generate
