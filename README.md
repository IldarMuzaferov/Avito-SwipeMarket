# SwipeMarket

Backend API for a marketplace discovery experience built around short product videos and swipe-based browsing. Sellers can create video or photo reels for listings; buyers can discover products, save favorites, and share wishlists.

The project is a FastAPI service with background media processing and a Docker Compose setup for local development.

## Features

- Guest and demo authentication, user profiles, categories, and onboarding interests.
- Personalized product feed with swipe actions, undo, and recommendation signals.
- Seller listings and reels, including direct-to-storage uploads using presigned URLs.
- Background media processing with FFmpeg: video validation and transcoding, poster generation, and portrait formatting.
- Wishlists with public sharing links.
- Promotion plans, mock payments, and payment webhook handling.
- Internal listing updates and administrative reel moderation.

## Tech stack

- **Python 3.12** and **FastAPI**
- **PostgreSQL** with SQLAlchemy and Alembic
- **Redis** and **ARQ** for background jobs
- **SeaweedFS** for local S3-compatible media storage
- **FFmpeg** for media processing
- **Docker Compose** for local development

## Getting started

### Requirements

- Docker Desktop with Docker Compose
- Git

### Run locally

Clone the repository and enter its directory:

```bash
git clone https://github.com/IldarMuzaferov/SwipeMarket.git
cd SwipeMarket
```

Create a local environment file, then start the services:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

On macOS or Linux, use `cp .env.example .env` instead of `Copy-Item`.

Apply database migrations and optionally load demo data:

```bash
docker compose exec api alembic upgrade head
docker compose exec api python seed.py
```

The seed script adds sample users, listings, reels, and categories. It is safe to rerun: if demo data already exists, it makes no changes.

The API is available at [http://localhost:8000](http://localhost:8000).

## API documentation

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- OpenAPI schema: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
- Liveness check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- Dependency readiness: [http://localhost:8000/api/v1/ready](http://localhost:8000/api/v1/ready)

All application endpoints use the `/api/v1` prefix. Authenticated endpoints expect a bearer access token in the `Authorization` header. See Swagger UI for request schemas and authentication details.

## Media uploads

The client uploads media directly to the S3-compatible storage using a presigned URL. The API queues completed uploads for the ARQ worker, which processes videos and images in the background.

In the provided Docker Compose setup, the API and worker use the internal storage endpoint (`http://seaweedfs:9000`), while browser clients use the public endpoint (`http://localhost:9000`). The local storage console is available at [http://localhost:8888](http://localhost:8888); the SeaweedFS master UI is at [http://localhost:9333](http://localhost:9333).

## Tests

Run the test suite inside the API container:

```bash
docker compose exec api python -m pytest -q
```

The tests use an isolated SQLite database and do not require a separate test PostgreSQL instance.

## Configuration and security

Use `.env.example` as the starting point for local configuration. The `.env` file is ignored by Git and must not be committed. Replace development keys and credentials before deploying anywhere beyond a local environment. Keep internal, admin, and payment webhook secrets private.

The included demo seed data and mock payment flow are intended for development, not production.
