# Smart Customer Feedback & Sentiment Engine

A real-time customer feedback intake system with async ML sentiment analysis
and automated Slack alerts for negative feedback.

Customers submit feedback through a REST API. It's validated, persisted, and
queued for background processing. A separate ML worker scores the sentiment
with a HuggingFace transformer model, writes the result back, and — if the
sentiment is negative enough — posts a Slack alert. An admin dashboard shows
the feedback stream, a sentiment trend chart, and lets you filter by
sentiment and date.

## Architecture

```
                         ┌─────────────────────┐
                         │   Admin (browser)     │
                         └──────────┬────────────┘
                                    │ HTTPS
                                    ▼
                         ┌────────────────────────┐
                         │   Next.js Dashboard     │
                         │  login · feedback list  │
                         │  · trend chart · filters│
                         └──────────┬──────────────┘
                                    │ JWT Bearer
                                    ▼
  ┌──────────┐  POST /api/v1/feedback   ┌─────────────────────────┐
  │ Customer │ ────────────────────────▶│        FastAPI API       │
  └──────────┘                          │ validation · rate limit  │
                                         │ idempotency · JWT auth   │
                                         │ correlation-ID logging   │
                                         └──────┬────────────┬─────┘
                                                │            │
                                    write       │            │ enqueue job
                                   "pending"    ▼            ▼
                                   ┌────────────────┐  ┌───────────────┐
                                   │   PostgreSQL    │  │     Redis      │
                                   │ feedback,       │  │   (RQ queue)   │
                                   │ admin_users     │  └───────┬────────┘
                                   └────────▲────────┘          │ dequeue
                                            │                   ▼
                                   write result         ┌───────────────────┐
                                            └────────────│     ML Worker       │
                                                          │  HuggingFace         │
                                                          │  DistilBERT SST-2     │
                                                          │  sentiment pipeline    │
                                                          └─────────┬─────────────┘
                                                                    │ NEGATIVE &
                                                                    │ score >= threshold
                                                                    ▼
                                                          ┌───────────────────┐
                                                          │   Slack webhook     │
                                                          └───────────────────┘
```

**Failure handling:** a failed sentiment job retries up to `MAX_RETRIES`
times with exponential backoff (`RETRY_BACKOFF_BASE_SECONDS * 2^attempt`).
Once retries are exhausted, RQ's built-in `FailedJobRegistry` acts as the
dead-letter queue and the feedback row is marked `status = "failed"` for
visibility in the dashboard.

## Tech stack

| Layer | Choice |
|---|---|
| Backend API | Python, FastAPI, SQLAlchemy, Alembic |
| ML | HuggingFace `transformers` — `distilbert-base-uncased-finetuned-sst-2-english` |
| Queue | Redis + RQ (with `Retry` and a `FailedJobRegistry` dead-letter queue) |
| Database | PostgreSQL |
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS v4, SWR, Recharts |
| Auth | JWT (HS256) via `python-jose` + `passlib`/bcrypt |
| Deployment | Docker Compose (api, ml-worker, redis, postgres, frontend) |
| CI | GitHub Actions (lint + test on push/PR) |

## Quickstart (Docker Compose)

Requires Docker and Docker Compose.

```bash
cp .env.example .env
docker compose up --build
```

That's it — the API container runs the Alembic migration automatically
before starting, so the database is ready on first boot.

| Service | URL |
|---|---|
| Admin dashboard | http://localhost:3000 |
| API | http://localhost:8000 |
| API health check | http://localhost:8000/health |

The ML worker downloads the HuggingFace model on first run, which can take a
minute or two depending on your connection — watch `docker compose logs -f
ml-worker` if you want to see it happen.

To use the dashboard, register an admin account and log in:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "changeme123"}'
```

Then open http://localhost:3000/login with those credentials.

### Environment variables

All variables are documented in [`.env.example`](.env.example). Notable ones:

- `SENTIMENT_NEGATIVE_THRESHOLD` — confidence score (0–1) above which a
  NEGATIVE result triggers a Slack alert. Defaults to `0.85`.
- `SLACK_WEBHOOK_URL` — leave empty for local dev; the worker logs and
  no-ops instead of failing when it's unset.
- `MAX_RETRIES` / `RETRY_BACKOFF_BASE_SECONDS` — retry policy for failed
  sentiment jobs.
- `RATE_LIMIT_PER_MINUTE` — requests per minute per client IP on
  `POST /api/v1/feedback`.
- `CORS_ALLOWED_ORIGINS` — comma-separated list of origins allowed to call
  the API from a browser (the dashboard's origin).
- `JWT_SECRET_KEY` — **change this** if you deploy anywhere beyond your own
  machine.

## Local development (without Docker)

### Backend

```bash
cd backend
python3 -m venv ../.venv && source ../.venv/bin/activate
pip install -r requirements-dev.txt   # API deps + test tooling, no torch

# Point at your own Postgres/Redis (defaults assume localhost:5432/6379)
export DATABASE_URL=postgresql+psycopg2://feedback:feedback@localhost:5432/feedback
export REDIS_URL=redis://localhost:6379/0

alembic -c alembic.ini upgrade head
uvicorn backend.api.main:app --reload   # run from the repo root
```

To run the ML worker locally you additionally need
`pip install -r requirements-worker.txt` (pulls in `torch` + `transformers`)
and `python -m backend.worker.worker_main`.

### Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

### Tests

```bash
# from the repo root, with DATABASE_URL/REDIS_URL pointing at a real Postgres/Redis
pytest backend/tests -v
ruff check backend
```

The test suite runs against a real Postgres (via a transaction-per-test
fixture that rolls back automatically) and a real Redis — there's no SQLite
substitution, so what passes locally matches what runs in CI. The one
integration test (`test_integration_pipeline.py`) goes further: it drives an
actual RQ `SimpleWorker` against the real queue, so the only thing mocked
anywhere in the suite is the HuggingFace model call itself (no `torch`
required to run tests).

If your machine already has something bound to 5432 or 6379, override with
`TEST_DATABASE_URL` / `TEST_REDIS_URL` instead of changing `DATABASE_URL`/
`REDIS_URL` — CI uses the standard ports via GitHub Actions service
containers.

```bash
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

## API reference

Interactive docs (Swagger UI) are available at `/docs` when the API is
running. Summary:

### Health

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | none | Liveness probe |
| GET | `/ready` | none | Readiness probe — checks Postgres + Redis connectivity |

### Feedback

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/feedback` | none (rate-limited) | Submit feedback. Optional `Idempotency-Key` header — a repeated key returns the original record (200) instead of creating a duplicate (201). |
| GET | `/api/v1/feedback` | JWT | Paginated list. Query params: `page`, `page_size` (max 100), `sentiment` (`POSITIVE`/`NEGATIVE`), `start_date`, `end_date`. |
| GET | `/api/v1/feedback/stats/trend` | JWT | Per-day POSITIVE/NEGATIVE counts for the trend chart. Query params: `start_date`, `end_date`. |

**POST /api/v1/feedback** request body:

```json
{ "user_id": "user-123", "text": "This product is great!" }
```

Response (`201 Created`, or `200 OK` on idempotent replay):

```json
{
  "id": "uuid",
  "user_id": "user-123",
  "text": "This product is great!",
  "status": "pending",
  "sentiment_label": null,
  "sentiment_score": null,
  "retry_count": 0,
  "created_at": "2026-01-01T00:00:00Z",
  "processed_at": null
}
```

`status` transitions `pending` → `processed` (or `failed` once retries are
exhausted) as the worker picks up the job.

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | none | Create an admin account: `{ "email": "...", "password": "..." }` (password: 8–128 chars). |
| POST | `/api/v1/auth/login` | none | `{ "email": "...", "password": "..." }` → `{ "access_token": "...", "token_type": "bearer" }`. Send as `Authorization: Bearer <token>` on protected routes. |

## Project structure

```
backend/
  api/            FastAPI app: routers, middleware, dependencies
  common/         Shared: config, db session, models, schemas, logging, queue, security
  worker/         RQ job (sentiment analysis), Slack alerting, worker entrypoint
  alembic/        Database migrations
  tests/          pytest suite (unit + the one integration test)
  Dockerfile.api
  Dockerfile.worker
frontend/
  src/app/        Next.js App Router pages (/, /login)
  src/components/ FeedbackTable, Pagination, Filters, SentimentTrendChart
  src/lib/        api client, auth context, SWR data hooks, shared types
  Dockerfile
docker-compose.yml
.github/workflows/ci.yml
```

## Design notes

- **Idempotency** is enforced via an optional `Idempotency-Key` header
  rather than requiring one, since public feedback intake shouldn't force
  every client to generate a key — it's there for clients that need
  safe retries.
- **Dead-letter queue**: rather than build a second, custom queue for failed
  jobs, the worker leans on RQ's own `FailedJobRegistry`, which already does
  this job. A `handle_job_failure` callback keeps the database in sync
  (`retry_count`, and `status = "failed"` only once retries are exhausted).
- **Structured logging**: every log line is one JSON object
  (`backend/common/logging.py`). A `CorrelationIdMiddleware` generates or
  passes through an `X-Request-ID` per API request; the worker reuses the
  feedback id itself as the correlation id for its own logs, so an API log
  line and the worker log lines for the same piece of feedback share one
  identifier.
- **Testing against real Postgres/Redis, not fakes**: the test suite uses a
  transaction-per-test fixture (rolled back automatically) against a real
  Postgres, and a real Redis for the queue and rate-limiter tests. The only
  thing ever mocked is the HuggingFace model call, so CI doesn't need
  `torch` installed and stays fast.

## What's not included (by design, for a portfolio-scoped project)

- Dashboard auth uses JWTs stored in `localStorage` rather than httpOnly
  cookies — simpler for a local/demo deployment, but worth hardening before
  any real production use.
- No pagination on the trend endpoint's date range — fine at the current
  scale, would want bucketing/downsampling for a long history.
- Admin registration is open (`POST /api/v1/auth/register` has no
  authorization check) — a real deployment would gate this behind an
  invite flow or an existing admin's permission.
