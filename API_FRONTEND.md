# Avito «Свайп» — API для frontend

Документ описывает текущий контракт backend. В случае расхождения с этим файлом
актуальная схема доступна в Swagger: `http://localhost:8000/docs`
(`http://localhost:8000/openapi.json`).

## Подключение

- Локальный адрес: `http://localhost:8000`
- Префикс API: `/api/v1`
- Тело запросов и ответы — JSON, кроме прямой загрузки файлов в хранилище.
- UUID передавайте строками.
- Защищённые пользовательские методы требуют заголовок:

```http
Authorization: Bearer <access_token>
```

Access token действует 1 день. Refresh token действует 30 дней. Для запросов,
которым авторизация не нужна, заголовок не требуется.

Ошибки возвращаются в едином формате:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": []
  }
}
```

`details` может отсутствовать. Для обычных HTTP-ошибок основные коды: `unauthorized`
(401), `forbidden` (403), `not_found` (404), `validation_error` (409/422),
`wishlist_disabled` (410), `too_large` (413), `bad_format` (415).

## Авторизация и профиль

| Метод и путь | Авторизация | Запрос | Успешный ответ |
|---|---|---|---|
| `POST /api/v1/auth/guest` | Нет | `{ "name": "Имя" }` или пустое тело | `200`: access/refresh token и пользователь |
| `POST /api/v1/auth/demo` | Нет | `{ "role": "buyer" }`; роли: `buyer`, `friend`, `seller` | `200`: access/refresh token и пользователь |
| `POST /api/v1/auth/refresh` | Нет | `{ "refresh_token": "..." }` | `200`: `{ "access_token": "..." }` |
| `GET /api/v1/users/me` | Да | — | `200`: текущий пользователь |
| `PATCH /api/v1/users/me` | Да | Любые поля из `name`, `avatar_url`, `city` | `200`: обновлённый пользователь |
| `GET /api/v1/categories` | Нет | — | `200`: массив категорий |

Пример ответа авторизации:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "user": {
    "id": "00000000-0000-0000-0000-000000000000",
    "name": "Гость",
    "avatar_url": null,
    "city": null,
    "is_guest": true,
    "wishlist_count": 0
  }
}
```

Поля пользователя: `id`, `name`, `avatar_url`, `city`, `is_guest`,
`wishlist_count`. В `PATCH /users/me` неизвестные поля запрещены.

### Онбординг и интересы

| Метод и путь | Авторизация | Запрос | Успешный ответ |
|---|---|---|---|
| `GET /api/v1/users/me/onboarding` | Да | — | `200`: `{ "interests_done": false, "hint_seen": false }` |
| `PUT /api/v1/users/me/interests` | Да | `{ "category_ids": ["<uuid>", "..."], "skipped": false }` | `204`, без тела |
| `GET /api/v1/users/me/interests` | Да | — | `200`: `{ "category_ids": ["<uuid>"] }` |
| `PATCH /api/v1/users/me/onboarding` | Да | `{ "hint_seen": true }` | `204`, без тела |

Если пользователь не пропускает выбор, требуется выбрать минимум 3 категории.
`skipped: true` нельзя передавать вместе с непустым `category_ids`.

## Лента, свайпы и объявления

### `GET /api/v1/feed`

Авторизация обязательна.

Параметры запроса:

| Параметр | Тип | По умолчанию | Ограничения / назначение |
|---|---|---:|---|
| `limit` | integer | `10` | от 1 до 20 |
| `cursor` | UUID | — | `reel_id` последнего полученного элемента; для следующей страницы |
| `session_id` | string | новый ID | До 100 символов; сохраняйте и передавайте вместе с последующими свайпами/запросами ленты |

Ответ `200`:

```json
{
  "items": [
    {
      "reel_id": "<uuid>",
      "listing_id": "<uuid>",
      "media": {
        "type": "video",
        "items": [
          {
            "url": "http://localhost:9000/avito-svayp/videos/...",
            "poster": "http://localhost:9000/avito-svayp/photos/...",
            "duration_sec": 12,
            "width": 1080,
            "height": 1920
          }
        ]
      },
      "title": "Название объявления",
      "price": { "amount": 150000, "currency": "RUB" },
      "description": "Описание",
      "seller": {
        "id": "<uuid>",
        "name": "Продавец",
        "avatar_url": null,
        "rating": 4.8
      },
      "is_promoted": false,
      "in_wishlist": false
    }
  ],
  "next_cursor": "<uuid или null>",
  "session_id": "<id сессии>"
}
```

`media.type`: `video`, `photo` или `album`. `price` может быть `null`.
Когда `next_cursor` равен `null`, следующей страницы нет. Для следующей страницы
передавайте последний `next_cursor` и тот же `session_id`.

### Свайп

`POST /api/v1/swipes` (авторизация обязательна):

```json
{
  "reel_id": "<uuid>",
  "action": "like",
  "client_id": "<новый uuid для этой операции>",
  "session_id": "<id из ответа ленты>",
  "dwell_ms": 1200,
  "position": 0
}
```

- `action`: `like`, `dislike` или `skip`.
- `client_id` обязателен и служит ключом идемпотентности. При повторной отправке
  того же запроса используйте тот же ID; новый свайп должен иметь новый UUID.
- `dwell_ms` необязателен, от 0 до 3 600 000; `position` — индекс позиции,
  по умолчанию 0.
- `like` добавляет объявление в избранное. Повторно показывать оценённые `like`
  и `dislike` элементы лента не будет; `skip` исключает элемент на 24 часа.

Ответ `200`:

```json
{ "in_wishlist": true, "wishlist_count": 1, "swipes_total": 1 }
```

`POST /api/v1/swipes/undo` отменяет последний свайп текущего пользователя и
возвращает карточку `FeedItem` (формат элемента из ответа ленты). Если свайпов
нет — `404`.

### Карточка и объявление

| Метод и путь | Авторизация | Ответ |
|---|---|---|
| `GET /api/v1/reels/{reel_id}` | Да | `200`: `FeedItem` |
| `GET /api/v1/listings/{listing_id}` | Нет | `200`: карточка объявления |

`ListingPage`: `listing_id`, `title`, `description`, `price` (`amount`, `currency`),
`city`, `seller`, `status` (`available`, `sold`, `removed`), `listing_url`, `images`.
`images` — массив объектов `{ "url": "..." }`.

## Избранное и публичная ссылка

| Метод и путь | Авторизация | Запрос / параметры | Успешный ответ |
|---|---|---|---|
| `GET /api/v1/wishlist` | Да | `limit` (1–50, default 20), `cursor` (UUID) | `200`: список, общее количество, share и курсор |
| `POST /api/v1/wishlist/items` | Да | `{ "listing_id": "<uuid>" }` | `201`: `{ "status": "ok" }` |
| `DELETE /api/v1/wishlist/items/{listing_id}` | Да | — | `204`, без тела |
| `GET /api/v1/wishlist/share` | Да | — | `200`: `{ "enabled": false, "url": null }` |
| `PUT /api/v1/wishlist/share` | Да | `{ "enabled": true }` | `200`: новое состояние и публичный URL |
| `POST /api/v1/wishlist/share/rotate` | Да | — | `200`: новая включённая ссылка |
| `GET /api/v1/public/wishlists/{share_token}` | Нет | `limit` (1–50, default 20), `cursor` (UUID) | `200`: публичный список |

Пример элемента личного списка: `listing_id`, `reel_id`, `title`, `price`,
`cover_url`, `city`, `status` (`available`, `sold`, `removed`), `added_at`.
Ответ списка содержит `count`, `items`, `share` (`enabled`, `url`) и `next_cursor`.
`next_cursor` передавайте как `cursor` следующего запроса. Повторное добавление
уже сохранённого объявления безопасно и может вернуть
`{ "status": "ok", "message": "Already in wishlist" }`.

Публичный ответ содержит `owner` (`display_name`, `avatar_url`), `count`, `items`
и `next_cursor`. В публичных элементах нет `reel_id`; удалённые и проданные
объявления отображаются как `sold`. Отключённая ссылка отвечает `410`.

## Кабинет продавца: медиа и рилсы

### Загрузка медиа

1. Создайте загрузку запросом `POST /api/v1/media/uploads` (авторизация обязательна):

```json
{
  "kind": "video",
  "files": [
    {
      "filename": "clip.mp4",
      "content_type": "video/mp4",
      "size_bytes": 12345678
    }
  ]
}
```

`kind` — `video` (ровно один файл) или `photos` (от 1 до 10 файлов).
Допустимые видео: `video/mp4`, `video/quicktime`, `video/webm`, максимум 200 MiB.
Допустимые фото: `image/jpeg`, `image/png`, `image/webp`, максимум 10 MiB каждое.

Ответ `200`: `{ "upload_id": "<uuid>", "files": [{ "file_id": "<uuid>", "put_url": "<presigned URL>", "headers": { "Content-Type": "video/mp4" } }], "expires_in": 3600 }`.

2. Загрузите байты файла **напрямую** по `put_url`, не через API:

```http
PUT <put_url>
Content-Type: <точно как в headers>

<raw file bytes>
```

URL временный (`expires_in` секунд). Не отправляйте JSON или `multipart/form-data`;
загружайте исходный файл как тело PUT. Используйте значение `Content-Type`,
которое вернул backend.

3. После успешной загрузки всех файлов вызовите
`POST /api/v1/media/uploads/{upload_id}/complete`. Ответ `202`:
`{ "status": "processing" }`. Backend проверяет размер и MIME и запускает
фоновую обработку.

4. Опросите `GET /api/v1/media/uploads/{upload_id}` до статуса `ready` или `failed`.
Ответ содержит `status` (`created`, `uploaded`, `processing`, `ready`, `failed`),
`error`, `duration_sec` и `files` с `file_id`, `preview_url`, `filename`,
`duration_sec`, `status`.

Дополнительные операции до обработки:

| Метод и путь | Тело | Успешный ответ |
|---|---|---|
| `POST /api/v1/media/uploads/{upload_id}/crop` | `{ "x": 0.1, "y": 0, "width": 0.8, "height": 1 }` | `200`: `{ "status": "ok" }` |
| `PUT /api/v1/media/uploads/{upload_id}/order` | `{ "file_ids": ["<uuid>", "..."] }` | `204`; перечислите каждый файл ровно один раз |
| `DELETE /api/v1/media/uploads/{upload_id}/files/{file_id}` | — | `204` |

Координаты crop нормализованы в диапазон 0–1; прямоугольник должен помещаться
в исходное изображение. Порядок файлов важен для альбома.

### Объявления и рилсы продавца

| Метод и путь | Авторизация | Запрос / параметры | Успешный ответ |
|---|---|---|---|
| `GET /api/v1/me/listings` | Да | — | `200`: активные объявления продавца: `id`, `title`, `price`, `has_reel` |
| `POST /api/v1/reels` | Да | `{ "listing_id": "<uuid>", "upload_id": "<uuid>", "show_price": true, "description": "..." }` | `201`: `ReelOut` |
| `GET /api/v1/me/reels` | Да | `status` (optional), `limit` (1–50, default 20), `cursor` (UUID) | `200`: список рилсов и `next_cursor` |
| `GET /api/v1/reels/{reel_id}/preview` | Да | `show_price` (bool), `description` (до 300 символов) | `200`: карточка `FeedItem` с предпросмотром |
| `PATCH /api/v1/reels/{reel_id}` | Да | Любые поля из `show_price`, `description`, `enabled` | `200`: `ReelOut` |
| `DELETE /api/v1/reels/{reel_id}` | Да | — | `204`, без тела |

Создавать рилс можно только для своего активного объявления и после того, как
загрузка имеет статус `ready`. Один рилс на объявление. Ответ `ReelOut` содержит
`reel_id`, `listing_id`, `status`, `media_type`, `show_price`, `description`,
`cover_url`, `enabled`, `published_at`. После создания статус обычно `moderation`;
в демо-конфигурации с автопубликацией может быть `published`.

Список рилсов содержит `items` и `next_cursor`. Элемент: `reel_id`, `listing_id`,
`title`, `price`, `cover_url`, `status`, `reject_reason`, `stats` (`views`, `likes`),
`promotion` (`active_until`).

## Продвижение и аналитика

| Метод и путь | Авторизация | Запрос / параметры | Успешный ответ |
|---|---|---|---|
| `GET /api/v1/promotion/plans` | Нет | — | `200`: массив тарифов |
| `POST /api/v1/reels/{reel_id}/promotions` | Да | `{ "plan_id": "<uuid>" }` | `200`: созданное продвижение и `payment_url` |
| `POST /api/v1/promotions/{promotion_id}/mock-pay` | Да | — | `200`: состояние продвижения (только demo/mock flow) |
| `GET /api/v1/reels/{reel_id}/promotions` | Да | — | `200`: история продвижений рилса |
| `POST /api/v1/events` | Да | `{ "events": [...] }` | `202`: `{ "status": "accepted" }` |

Тариф содержит `id`, `days`, `estimated_reach`, `price_amount`, `is_best_value`.
Продвигать можно только свой опубликованный и включённый рилс. Ответ создания
содержит `promotion_id`, `status`, `payment_url`, `active_until`.
История содержит `promotion_id`, `plan_id`, `status`, `starts_at`, `active_until`.

Событие аналитики:

```json
{
  "type": "watch",
  "reel_id": "<uuid>",
  "value_ms": 12000,
  "ts": "2026-10-26T10:00:00Z"
}
```

`type`: `view`, `watch`, `expand_description`, `open_listing`, `sound_toggle`.
`value_ms` и `ts` необязательны. Отправляйте от 1 до 100 событий в одном запросе.

## Служебные методы (не вызывать из frontend)

| Метод и путь | Заголовок / тело | Назначение |
|---|---|---|
| `POST /api/v1/payments/webhook` | `X-Payment-Signature`; `{ "payment_id": "...", "status": "paid" }` | Webhook платежного провайдера; HMAC-SHA256 подпись тела `payment_id:status` |
| `POST /api/v1/internal/listings/{listing_id}/status` | `X-Internal-Key`; `{ "status": "sold" }` | Внутреннее обновление объявления; статус `active`, `sold`, `removed` |
| `POST /api/v1/admin/reels/{reel_id}/moderation` | `X-Admin-Key`; `{ "decision": "reject", "reason": "..." }` | Модерация; `decision`: `approve` или `reject` |

Секреты для этих заголовков хранятся только на backend. Не включайте их в frontend.
Mock-pay — демонстрационный endpoint, его не следует использовать вместо реальной
интеграции с платежным провайдером.

## Проверка сервиса

| Метод и путь | Назначение |
|---|---|
| `GET /health` или `GET /api/v1/health` | Liveness, ответ `{ "status": "ok" }` |
| `GET /ready` или `GET /api/v1/ready` | Readiness; проверяет базу, Redis и S3-хранилище |

В локальном Docker Compose SeaweedFS предоставляет S3 API на `http://localhost:9000`.
Frontend использует только `put_url` для загрузки; endpoint получения presigned URL
возвращает абсолютный адрес, доступный браузеру.
