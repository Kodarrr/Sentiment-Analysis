# Smart Customer Feedback & Sentiment Engine (with BanglaBERT & DistilBERT)

A real-time customer feedback intake system with dual-engine async ML sentiment analysis (Bangla & English) and automated Slack alerts for negative feedback.

Customers submit feedback in either Bengali or English through a REST API. It is validated, persisted, and queued for background processing in Redis/RQ. A dedicated ML worker executes the unified sentiment engine:
- **Bengali text**: routed to a fine-tuned **BanglaBERT** model (`sm-khalil/banglabert-sentigold`) returning 5 fine-grained classes (`NU`, `SN`, `WN`, `SP`, `WP`) with `csebuetnlp` text normalization.
- **English/Other text**: fallback to **DistilBERT** (`distilbert-base-uncased-finetuned-sst-2-english`).
- **Slack Alerting**: triggers on negative polarity (`SN` or `WN`) when confidence exceeds the threshold.
- **Admin Dashboard**: Next.js dashboard displaying real-time feedback with fine-grained badges and hover legends, a 3-polarity trend chart (Positive / Neutral / Negative), and a label distribution chart.

---

## Model Benchmark & Evaluation

- **Model ID**: [`sm-khalil/banglabert-sentigold`](https://huggingface.co/sm-khalil/banglabert-sentigold) (BanglaBERT fine-tuned on SentiGOLD)
- **Classes (5 fine-grained)**:
  - `SN`: Strongly Negative (coarse polarity: *negative*)
  - `WN`: Weakly Negative (coarse polarity: *negative*)
  - `NU`: Neutral (coarse polarity: *neutral*)
  - `WP`: Weakly Positive (coarse polarity: *positive*)
  - `SP`: Strongly Positive (coarse polarity: *positive*)
- **Test Set Evaluation** (7,000 samples):
  - **Accuracy**: **0.673** (67.3%)
  - **Macro-F1**: **0.667**

---

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
                         │  · 3-polarity trend    │
                         │  · label distribution  │
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
                                   write result         ┌───────────────────────┐
                                            └───────────│       ML Worker       │
                                                        │  Unified Sentiment    │
                                                        │  Engine               │
                                                        │  ├─ BanglaBERT        │
                                                        │  │  (csebuetnlp norm) │
                                                        │  └─ DistilBERT (en)   │
                                                        └──────────┬────────────┘
                                                                   │ polarity == "negative"
                                                                   │ & score >= threshold
                                                                   ▼
                                                        ┌───────────────────┐
                                                        │   Slack webhook     │
                                                        └───────────────────┘
```

**Failure handling:** a failed sentiment job retries up to `MAX_RETRIES` times with exponential backoff (`RETRY_BACKOFF_BASE_SECONDS * 2^attempt`). Once retries are exhausted, RQ's built-in `FailedJobRegistry` acts as the dead-letter queue and the feedback row is marked `status = "failed"` for visibility in the dashboard.

## Tech stack

| Layer | Choice |
|---|---|
| Backend API | Python, FastAPI, SQLAlchemy 2.0, Alembic |
| ML Engine | Hugging Face `transformers` & `torch`: `sm-khalil/banglabert-sentigold` + `distilbert-base-uncased-finetuned-sst-2-english` |
| Text Normalizer | `csebuetnlp/normalizer` (for Bangla text preprocessing) |
| Queue | Redis + RQ (with `Retry` and a `FailedJobRegistry` dead-letter queue) |
| Database | PostgreSQL 16 |
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS v4, SWR, Recharts |
| Auth | JWT (HS256) via `python-jose` + `passlib`/bcrypt |
| Deployment | Docker Compose (`api`, `ml-worker`, `redis`, `postgres`, `frontend`, `hf_cache` volume) |
| CI | GitHub Actions (lint + test on push/PR with mocked models) |

## Quickstart (Docker Compose)

Requires Docker and Docker Compose.

```bash
# 1. Copy env template
cp .env.example .env

# 2. If the Hugging Face model repository is private, add your Hugging Face Token:
# HF_TOKEN=hf_YourAccessTokenHere

# 3. Build and launch all services
docker compose up --build
```

That's it — the API container automatically applies the Alembic database migrations (`3a1c5d9e7b2f_add_fine_grained_sentiment_columns.py`) before starting. The Hugging Face models are cached in the persistent Docker volume `hf_cache` (`/app/.cache/huggingface`), preventing re-downloading across container restarts.

| Service | URL |
|---|---|
| Admin dashboard | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API health check | http://localhost:8000/health |

Watch worker logs while the model initializes:
```bash
docker compose logs -f ml-worker
```

To use the dashboard, register an admin account and log in:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "changeme123"}'
```

Then open http://localhost:3000/login with those credentials.

### Environment variables

All variables are documented in [`.env.example`](.env.example). Notable keys:

- `BANGLA_MODEL_ID` — Hugging Face model repository ID (default: `sm-khalil/banglabert-sentigold`).
- `HF_TOKEN` — Hugging Face User Access Token (required for private repositories).
- `HF_HOME` — Hugging Face cache directory path (default in container: `/app/.cache/huggingface`).
- `SENTIMENT_ENGINE` — Routing mode: `auto` (auto-detect script), `bangla` (force BanglaBERT), or `distilbert` (force DistilBERT). Defaults to `auto`.
- `CONFIDENCE_THRESHOLD` / `SENTIMENT_NEGATIVE_THRESHOLD` — Confidence score (0–1) above which a negative result triggers a Slack alert. Defaults to `0.85`.
- `SLACK_WEBHOOK_URL` — Slack Incoming Webhook URL. Leave empty for local dev; the worker logs and gracefully no-ops when unset.
- `MAX_RETRIES` / `RETRY_BACKOFF_BASE_SECONDS` — Retry policy for failed sentiment jobs.
- `RATE_LIMIT_PER_MINUTE` — Requests per minute per client IP on `POST /api/v1/feedback`.
- `CORS_ALLOWED_ORIGINS` — Comma-separated list of origins allowed to call the API from a browser.
- `JWT_SECRET_KEY` — Secret key for signing admin JWT tokens.
- `SLACK_WEBHOOK_URL` — leave empty for local dev; the worker logs and
  no-ops instead of failing when it's unset.
- `MAX_RETRIES` / `RETRY_BACKOFF_BASE_SECONDS` — retry policy for failed
  sentiment jobs.
- `RATE_LIMIT_PER_MINUTE` — requests per minute per client IP on
  `POST /api/v1/feedback`.
- `CORS_ALLOWED_ORIGINS` — comma-separated list of origins allowed to call
  the API from a browser (the dashboard's origin).
- `FRONTEND_PORT` — host port the dashboard is published on (default
  `3000`). If you change this because something else on your machine
  already uses 3000, **also update `CORS_ALLOWED_ORIGINS`** to match — the
  dashboard's own requests to the API get blocked by CORS otherwise, since
  `.env` values aren't cross-referenced.
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
| GET | `/api/v1/feedback` | JWT | Paginated list. Query params: `page`, `page_size` (max 100), `sentiment` (`positive`/`negative`/`neutral` or fine-grained `SN`, `WN`, `NU`, `SP`, `WP`), `start_date`, `end_date`. |
| GET | `/api/v1/feedback/stats/trend` | JWT | Daily aggregate counts: `positive_count`, `negative_count`, `neutral_count`. Query params: `start_date`, `end_date`. |
| GET | `/api/v1/feedback/stats/distribution` | JWT | Fine-grained label count distribution for bar charts. Query params: `start_date`, `end_date`. |

#### Example Submissions via `curl`

**1. Bangla Feedback (BanglaBERT Route):**
```bash
curl -i -X POST http://localhost:8000/api/v1/feedback \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-bangla-01" \
  -d '{"user_id": "cust-bn-1", "text": "পণ্যটির কোয়ালিটি অনেক ভালো এবং সার্ভিস অসাধারণ!"}'
```

**2. Negative Bangla Feedback (Triggers Slack Alert if score >= threshold):**
```bash
curl -i -X POST http://localhost:8000/api/v1/feedback \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-bangla-02" \
  -d '{"user_id": "cust-bn-2", "text": "একদম বাজে অভিজ্ঞতা, ডেলিভারি অনেক দেরি হয়েছে এবং পণ্য ভাঙ্গা ছিল।"}'
```

**3. English Feedback (DistilBERT Route):**
```bash
curl -i -X POST http://localhost:8000/api/v1/feedback \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-en-01" \
  -d '{"user_id": "cust-en-1", "text": "Excellent delivery time and great packaging!"}'
```

**POST /api/v1/feedback** initial response (`201 Created`):

```json
{
  "id": "c1f72a9b-43e8-4682-bb34-3158c3bcdd04",
  "user_id": "cust-bn-2",
  "text": "একদম বাজে অভিজ্ঞতা, ডেলিভারি অনেক দেরি হয়েছে এবং পণ্য ভাঙ্গা ছিল।",
  "status": "pending",
  "sentiment_label": null,
  "sentiment_score": null,
  "sentiment_polarity": null,
  "confidence": null,
  "probabilities": null,
  "model_id": null,
  "model_revision": null,
  "retry_count": 0,
  "created_at": "2026-10-16T12:00:00Z",
  "processed_at": null
}
```

Once processed by the background worker, fetching the item via `GET /api/v1/feedback` yields:

```json
{
  "id": "c1f72a9b-43e8-4682-bb34-3158c3bcdd04",
  "user_id": "cust-bn-2",
  "text": "একদম বাজে অভিজ্ঞতা, ডেলিভারি অনেক দেরি হয়েছে এবং পণ্য ভাঙ্গা ছিল।",
  "status": "processed",
  "sentiment_label": "SN",
  "sentiment_score": 0.9412,
  "sentiment_polarity": "negative",
  "confidence": 0.9412,
  "probabilities": {
    "SN": 0.9412,
    "WN": 0.0410,
    "NU": 0.0120,
    "WP": 0.0035,
    "SP": 0.0023
  },
  "model_id": "sm-khalil/banglabert-sentigold",
  "model_revision": "4f83b1a",
  "retry_count": 0,
  "created_at": "2026-10-16T12:00:00Z",
  "processed_at": "2026-10-16T12:00:02Z"
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

## Manual Verification Checklist

Once the services are running with `docker compose up --build`:

1. **Verify Database Migration:**
   ```bash
   docker compose exec api alembic current
   # Output should confirm: 3a1c5d9e7b2f (head)
   ```
2. **Submit Feedback via `curl`:**
   - Submit a positive Bangla sample:
     ```bash
     curl -s -X POST http://localhost:8000/api/v1/feedback \
       -H "Content-Type: application/json" \
       -d '{"user_id": "cust-1", "text": "খুব ভালো সেবা পেয়েছি, ধন্যবাদ।"}'
     ```
   - Submit a strongly negative Bangla sample:
     ```bash
     curl -s -X POST http://localhost:8000/api/v1/feedback \
       -H "Content-Type: application/json" \
       -d '{"user_id": "cust-2", "text": "একদম জঘন্য কোয়ালিটি, কখনো আর কিনব না।"}'
     ```
   - Submit an English sample:
     ```bash
     curl -s -X POST http://localhost:8000/api/v1/feedback \
       -H "Content-Type: application/json" \
       -d '{"user_id": "cust-3", "text": "This product works as advertised."}'
     ```
3. **Verify Worker Logs & Language Routing:**
   ```bash
   docker compose logs -f ml-worker
   ```
   Check that:
   - Bangla sentences route to `sm-khalil/banglabert-sentigold` and log fine-grained labels (`SP`, `SN`, etc.).
   - English sentences route to `distilbert-base-uncased-finetuned-sst-2-english`.
   - If `SLACK_WEBHOOK_URL` is set, check that a negative alert formatted with `[SN]` is dispatched.
4. **Inspect Database Records:**
   ```bash
   docker compose exec postgres psql -U feedback -d feedback -c \
     "SELECT text, sentiment_label, sentiment_polarity, confidence, model_id FROM feedback ORDER BY created_at DESC LIMIT 5;"
   ```
5. **Inspect Dashboard UI (http://localhost:3000):**
   - Log into the dashboard with your admin credentials.
   - Hover over the fine-grained badges (`SN`, `WN`, `NU`, `WP`, `SP`) to view the Bengali label tooltip.
   - Check the **Sentiment Trend Over Time** chart (displays Positive, Neutral, and Negative lines).
   - Check the **Label Distribution** bar chart (displays counts for each of the 5 Bangla classes plus English classes).
   - Test filtering by Coarse Polarity (`positive`, `negative`, `neutral`) and Fine-grained Label (`SN`, `WN`, etc.).

## What's not included (by design, for a portfolio-scoped project)

- Dashboard auth uses JWTs stored in `localStorage` rather than httpOnly
  cookies — simpler for a local/demo deployment, but worth hardening before
  any real production use.
- No pagination on the trend endpoint's date range — fine at the current
  scale, would want bucketing/downsampling for a long history.
- Admin registration is open (`POST /api/v1/auth/register` has no
  authorization check) — a real deployment would gate this behind an
  invite flow or an existing admin's permission.

