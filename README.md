# Avito Svayp — Бэкенд режима «Свайп»

## Быстрый старт

```bash
# 1. Скопировать .env
cp .env.example .env

# 2. Запустить сервисы
docker compose up -d

# 3. Применить миграции
docker compose exec api alembic upgrade head

# 4. Заполнить тестовыми данными
docker compose exec api python seed.py

# 5. API доступен на http://localhost:8000
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

## Этапы реализации

1. ✅ Каркас: docker-compose, конфиг, БД, Alembic, `/health`, `/auth/guest`, `/auth/demo`, `/users/me`, seed-скрипт
2. ✅ Онбординг и лента: `/categories`, интересы, `/feed`, `/swipes`
3. ⬜ Вишлист и шаринг
4. ⬜ Продавец: загрузка медиа, рилсы
5. ⬜ Рекомендации и продвижение