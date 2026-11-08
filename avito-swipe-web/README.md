# SwipeMarket frontend

Frontend проекта SwipeMarket на React 18, TypeScript и Vite. Общая инструкция по проекту, backend, Docker Compose, настройке окружения и демонстрационным данным находится в [корневом README](../README.md).

## Локальный запуск

Требуется Node.js 18 или новее.

Из этой папки установите зависимости и запустите dev-сервер:

```bash
npm install
```

Для PowerShell сначала создайте локальный env-файл:

```powershell
Copy-Item .env.example .env
npm run dev
```

Для macOS/Linux:

```bash
cp .env.example .env
npm run dev
```

Откройте http://localhost:3000. Для запросов к локальному backend в `.env` используется `VITE_API_URL=http://localhost:8000/api/v1`. Используйте `localhost`, так как backend ограничивает CORS origin.

## Проверки и сборка

```bash
npm run typecheck
npm run build
npm run preview
```

Сборка находится в `dist/`; `node_modules/`, `dist/` и локальные env-файлы не следует коммитить.
