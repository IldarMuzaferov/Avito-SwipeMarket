# Avito Svayp — Бэкенд режима «Свайп»

## Быстрый старт

```bash
# 1. Скопировать .env
cp .env.example .env

# 2. Запустить PostgreSQL, Redis, SeaweedFS, API и worker
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
- **SeaweedFS** — S3-совместимое хранилище для локальной разработки
- **Alembic** — миграции БД
- **aioboto3** — работа с S3
- **ARQ + ffmpeg** — обработка загруженных видео и фото в фоне

## Проверки

```bash
python -m pytest -q
python -m compileall -q app alembic tests seed.py
```

Загрузка производится клиентом напрямую в SeaweedFS по presigned URL. При завершении
загрузки API ставит задачу в Redis/ARQ; worker проверяет длительность видео,
перекодирует его в H.264, формирует постер и приводит фото/видео к формату 9:16.
Для локального запуска `S3_ENDPOINT` должен указывать на SeaweedFS внутри Compose
(`http://seaweedfs:9000`), а `S3_PUBLIC_ENDPOINT` — на адрес, доступный браузеру
(`http://localhost:9000`). При переходе со старой конфигурации замените
`S3_ENDPOINT=http://minio:9000` в локальном `.env` на
`S3_ENDPOINT=http://seaweedfs:9000`.

SeaweedFS автоматически создаёт бакет из `S3_BUCKET` и использует значения
`S3_ACCESS_KEY` / `S3_SECRET_KEY` как S3-учётные данные. CORS настроен для локальных
frontend-origin `localhost:3000` и `localhost:5173`. Интерфейсы доступны на
`http://localhost:9333` (master) и `http://localhost:8888` (filer).

Seed-скрипт не удаляет существующие данные и безопасно завершается, если демо-пользователь
уже создан. Перед запуском seed необходимо применить все миграции.