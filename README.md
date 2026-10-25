# Avito Svayp — Бэкенд режима «Свайп»

## Быстрый старт

```bash
# 1. Скопировать .env
cp .env.example .env

# 2. Запустить PostgreSQL, Redis, MinIO, API и worker
docker compose up -d

# 3. Применить миграции
docker compose exec api alembic upgrade head

# 4. Заполнить тестовыми данными
docker compose exec api python seed.py

# 5. API и документация доступны на http://localhost:8000
```

## Основные команды

```bash
# Запуск тестов
docker compose exec api pytest tests/ -v

# Просмотр API docs
# http://localhost:8000/docs
```

## Архитектура

- **FastAPI** — веб-фреймворк
- **PostgreSQL** — основная БД
- **Redis** — кэш и сессии
- **MinIO** — S3-совместимое хранилище
- **Alembic** — миграции БД
- **aioboto3** — работа с S3
- **ARQ + ffmpeg** — обработка загруженных видео и фото в фоне

## Проверки

```bash
python -m pytest -q
python -m compileall -q app alembic tests seed.py
```

Загрузка производится клиентом напрямую в MinIO по presigned URL. При завершении
загрузки API ставит задачу в Redis/ARQ; worker проверяет длительность видео,
перекодирует его в H.264, формирует постер и приводит фото/видео к формату 9:16.
Для локального запуска переменные S3 в `.env` настроены на MinIO, а `S3_PUBLIC_ENDPOINT`
должен быть адресом, доступным браузеру.

Seed-скрипт не удаляет существующие данные и безопасно завершается, если демо-пользователь
уже создан. Перед запуском seed необходимо применить все миграции.