# Ticket Analyzer

A minimal full-stack sentiment-analysis demo: submit a support ticket, run it through a tiny Hugging Face model (`distilbert-base-uncased-finetuned-sst-2-english`), persist it in PostgreSQL, and view the history in the browser.

Built as the workshop deliverable for **bKash presents SUST CSE Carnival 2026 — Codex Community Hackathon**.

---

## Overview

Ticket Analyzer demonstrates the complete engineering path from PRD to live deployment: React/Vite frontend, FastAPI backend with a baked-in ML model, PostgreSQL persistence, Docker Compose orchestration, image registries, and cloud-VM deployment.

### Architecture

```
                         ┌─────────────────────────────┐
                         │        Browser (User)        │
                         └───────────────┬──────────────┘
                                         │ HTTP :3000
                         ┌───────────────▼──────────────┐
                         │   frontend (Nginx + React)    │
                         │   - serves static SPA build   │
                         │   - reverse-proxies /api/* ───┼────┐
                         └───────────────────────────────┘    │
                                                               │ HTTP :8000 (internal docker net)
                         ┌─────────────────────────────────────▼───┐
                         │        backend (FastAPI + Uvicorn)       │
                         │  ┌─────────────────────────────────┐     │
                         │  │  Inference module                │     │
                         │  │  distilbert-sst-2 (baked at build)│    │
                         │  └─────────────────────────────────┘     │
                         │  ┌─────────────────────────────────┐     │
                         │  │  SQLAlchemy ORM layer             │    │
                         │  │  Base.metadata.create_all(engine)│    │
                         │  └─────────────────────────────────┘     │
                         └─────────────────┬───────────────────────┘
                                           │ SQL :5432 (internal docker net)
                         ┌─────────────────▼───────────────────────┐
                         │   db (postgres:16-alpine, named volume)  │
                         └──────────────────────────────────────────┘
```

**Services:**

| Service  | Image                                          | Internal port | Host port |
|----------|------------------------------------------------|---------------|-----------|
| frontend | `ishtiakrahman/ticket-analyzer-frontend:v1`    | 80 (nginx)    | **3000**  |
| backend  | `ishtiakrahman/ticket-analyzer-backend:v1`     | 8000          | 8000 (local dev only) |
| db       | `postgres:16-alpine`                           | 5432          | 5432 (local dev only) |

On the production VM (see [Deployment Guide](#deployment-guide)), only port 3000 is published — nginx inside the frontend container reverse-proxies `/api/*` to the backend over the internal Docker network, so the backend and database are not reachable from the public internet.

---

## Prerequisites

You only need **Docker** for the local one-command setup. Everything else (Python, Node, model weights) is baked into the images.

| Tool           | Version       | Why                                                     |
|----------------|---------------|---------------------------------------------------------|
| Docker         | 24+           | Runs the three containers and builds/pushes the images  |
| Docker Compose | v2 (`docker compose`, not `docker-compose`) | Orchestrates the local stack        |
| Git            | any recent    | Clone the repo                                          |
| (Optional) Puku CLI / aws-cli | latest | Phase 6 deployment — credentials come from Poridhi Lab |

**For source development** (only if you want to edit code locally and rebuild):

| Tool    | Version       | Why                                       |
|---------|---------------|-------------------------------------------|
| Node.js | 20+           | Frontend build (`frontend/`)              |
| Python  | 3.11+         | Backend source (`backend/`)               |

Verify:

```bash
docker --version          # Docker version 24.x or later
docker compose version    # Docker Compose version v2.x
```

---

## Local Setup

A fresh checkout reaches a running stack in three commands.

### 1. Clone and enter the project

```bash
git clone https://github.com/Ishtiak2/ticket-analyzer.git
cd ticket-analyzer
```

### 2. Create your local `.env`

```bash
cp .env.example .env
```

The defaults in `.env.example` work out of the box for local development (Postgres on the same Docker network, model baked into the backend image, frontend talks to backend via nginx at `/api`).

### 3. Build and start the stack

```bash
docker compose up -d --build
```

The `-d` flag runs containers in the background so the command returns instead of streaming logs. You'll see, in order:

```
[+] Running X/Y
 ✔ Network ticket-analyzer_default   Created
 ✔ Volume ticket-analyzer_pgdata      Created
 ✔ Container ticket-analyzer-db        Started
 ✔ Container ticket-analyzer-db        Healthy
 ✔ Container ticket-analyzer-backend   Started
 ✔ Container ticket-analyzer-backend   Healthy
 ✔ Container ticket-analyzer-frontend  Started
```

The first boot takes ~2 minutes because the backend pulls the `distilbert` weights during the Docker build step. Subsequent boots take ~30 seconds (model warm + Postgres already initialized). To watch the backend finish loading the model and confirm readiness:

```bash
# Wait for the backend to report healthy (max ~150s)
for i in {1..30}; do
  sleep 5
  s=$(curl -sf http://localhost:3000/api/health 2>/dev/null)
  if echo "$s" | grep -q '"status":"ok"'; then
    echo "READY after $((i*5))s: $s"
    break
  fi
  echo "[poll $i] waiting for backend..."
done

# To follow live logs while debugging:
docker compose logs -f backend
```

### 4. Open the app

| URL                              | What you'll see                              |
|----------------------------------|----------------------------------------------|
| http://localhost:3000            | The frontend UI — submit a ticket here       |
| http://localhost:3000/api/health | `{"status":"ok","model_loaded":true}`        |
| http://localhost:8000/health     | Same as above, hit directly on backend       |

### 5. Verify end-to-end

```bash
# Health
curl http://localhost:3000/api/health
# {"status":"ok","model_loaded":true}

# Submit a positive ticket
curl -X POST http://localhost:3000/api/tickets \
  -H 'Content-Type: application/json' \
  -d '{"title":"smoke","message":"Everything works","category":"smoke"}'
# {"id":1,"title":"smoke",...,"sentiment":"POSITIVE","confidence":1.0,...}

# Submit a negative ticket
curl -X POST http://localhost:3000/api/tickets \
  -H 'Content-Type: application/json' \
  -d '{"title":"bug","message":"This is broken and awful","category":"smoke"}'
# {"id":2,"title":"bug",...,"sentiment":"NEGATIVE","confidence":1.0,...}

# List tickets (newest first)
curl http://localhost:3000/api/tickets
# [{"id":2,...,"sentiment":"NEGATIVE",...}, {"id":1,...,"sentiment":"POSITIVE",...}]
```

(`id` numbers depend on prior data — a fresh database starts at `id=1`; the dev stack used to build this README had prior tickets so the new IDs were `11` and `12`. Either way, the schema and sentiment labels are what matters.)

### Tear down

```bash
docker compose down              # stop containers, keep the pgdata volume
docker compose down -v           # stop containers AND wipe the database (fresh start)
```

`docker compose down` (no `-v`) is what you want for normal restarts — your tickets survive. `-v` is only for deliberately starting from scratch.

---

## Environment Variables

All variables live in `.env` (gitignored). The contract below is from PRD §11; defaults in `.env.example` cover local dev.

### Backend

| Variable               | Default                                                          | Required | Notes |
|------------------------|------------------------------------------------------------------|----------|-------|
| `DATABASE_URL`         | `postgresql://postgres:postgres@db:5432/ticket_db`               | yes      | Use `db` as host (Docker service name), not `localhost` |
| `MODEL_NAME`           | `distilbert-base-uncased-finetuned-sst-2-english`                | yes      | Must match the model baked at build time |
| `HF_HOME`              | `/opt/hf-cache`                                                  | yes      | Must match the `ENV HF_HOME` in `backend/Dockerfile` |
| `TRANSFORMERS_OFFLINE` | `1`                                                              | yes      | Forces runtime to use baked-in weights only — container fails loudly if weights are missing (better than silent network fetch) |
| `CORS_ALLOWED_ORIGINS` | *(empty)*                                                        | no       | Empty disables CORS. Only needed if you bypass the nginx proxy. |

### Frontend (Vite — **baked at build time**, not runtime)

| Variable             | Default | Required | Notes |
|----------------------|---------|----------|-------|
| `VITE_API_BASE_URL`  | `/api`  | yes      | **Read once at `npm run build`**. `/api` works on both localhost and the VM because nginx proxies the same path in both places. If you change this, you must rebuild the frontend image — `.env` edits alone won't propagate. |

### Postgres (used by the `db` service in `docker-compose.yml`)

| Variable            | Default    | Notes |
|---------------------|------------|-------|
| `POSTGRES_USER`     | `postgres` | Demo-grade credentials. See [Known Limitations](#known-limitations). |
| `POSTGRES_PASSWORD` | `postgres` | Same. |
| `POSTGRES_DB`       | `ticket_db`| Must match the database name in `DATABASE_URL`. |

---

## API Reference

Base URL during local dev: `http://localhost:3000/api` (note the `/api` prefix — the frontend talks to the backend through nginx).

### `GET /health`

Returns backend status and whether the model is loaded.

**Response 200:**

```json
{"status":"ok","model_loaded":true}
```

`model_loaded:true` confirms the `distilbert-sst-2` weights are in memory and ready — the first POST will return a real inference (not a cold-start delay).

### `POST /tickets`

Create a ticket and run sentiment analysis. Title and message are required; category is optional.

**Request:**

```json
{
  "title": "Lab VM issue",
  "message": "My lab VM is not opening before the deadline.",
  "category": "lab"
}
```

**Response 201:**

```json
{
  "id": 1,
  "title": "Lab VM issue",
  "message": "My lab VM is not opening before the deadline.",
  "category": "lab",
  "sentiment": "NEGATIVE",
  "confidence": 0.999,
  "created_at": "2026-06-25T14:13:13.985293"
}
```

(`id` is whatever the next ticket number is on your database — this is a generic example showing the response shape, not the exact id you'd see.)

`sentiment` is always `"POSITIVE"` or `"NEGATIVE"` — never `LABEL_0` / `LABEL_1`. This is the proof in PRD §13 that the real `distilbert-sst-2` model is loaded, not a placeholder.

**Response 422** (validation error — empty title and message):

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "title"],
      "msg": "String should have at least 1 character",
      "input": "",
      "ctx": {"min_length": 1}
    },
    {
      "type": "string_too_short",
      "loc": ["body", "message"],
      "msg": "String should have at least 1 character",
      "input": "",
      "ctx": {"min_length": 1}
    }
  ]
}
```

Length limits (also enforced on the frontend): `title` ≤ 255 chars, `message` ≤ 4000 chars, `category` ≤ 100 chars.

### `GET /tickets`

List all saved tickets, newest first (ordered by `created_at DESC, id DESC`).

**Response 200:**

```json
[
  {
    "id": 12,
    "title": "README smoke negative",
    "message": "This is broken and awful",
    "category": "smoke",
    "sentiment": "NEGATIVE",
    "confidence": 1.0,
    "created_at": "2026-06-25T14:13:14.077479"
  }
]
```

There is no pagination — this is a demo. Refreshing the browser fetches the full list.

---

## Deployment Guide

This project ships as two pre-built images on DockerHub plus one production compose file. A new machine with only Docker installed can run the full stack without any source code.

### Prerequisites on the target VM

- Linux VM with Docker 24+ and Docker Compose v2 installed
- Port 3000 open on the public interface (do **not** open 5432 or 8000 — see [Known Limitations](#known-limitations))

### Deploy steps

```bash
# 1. Pull the images
docker pull ishtiakrahman/ticket-analyzer-backend:v1
docker pull ishtiakrahman/ticket-analyzer-frontend:v1
docker pull postgres:16-alpine

# 2. Place docker-compose.prod.yml on the VM (it's in the GitHub repo root)

# 3. Create a .env on the VM (same shape as .env.example)
cp .env.example .env
# Edit DATABASE_URL if you're pointing at a remote Postgres — for a single-VM
# deploy, the default (db:5432) is correct.

# 4. Bring the stack up
docker compose -f docker-compose.prod.yml up -d

# 5. Wait for the backend to finish loading the model (~30-90s on cold boot)
for i in {1..30}; do
  sleep 5
  if curl -sf http://localhost:3000/api/health | grep -q '"status":"ok"'; then
    echo "READY"
    break
  fi
done
```

### Credential flow

Cloud credentials (AWS access key / secret, or Poridhi Lab session details) are **issued only inside the Poridhi Lab environment** during the workshop session and used at deploy time via environment variables or the Puku CLI's credential mechanism.

**No real secrets are committed to this repository.** `.env` is in `.gitignore`. The `.env.example` shipped here contains only demo-grade values (`postgres`/`postgres`) for local development.

### Image-tagging discipline

- Tags are **versioned** (`v1`, `v1.1`, ...) — never `:latest` on DockerHub
- Bumping the tag forces every downstream redeploy to pick up the new code
- A fix pushed under the same tag as the deployed VM would silently ship old code

### Verifying a deployment from outside the VM

The acceptance test that proves nginx, the proxy, and the model all work together:

```bash
# From a machine that is NOT the VM and NOT localhost (your laptop, your phone)
curl http://<vm-host>:3000/api/health
# {"status":"ok","model_loaded":true}

curl -X POST http://<vm-host>:3000/api/tickets \
  -H 'Content-Type: application/json' \
  -d '{"title":"remote test","message":"submitted from another network","category":"smoke"}'
# {"id":...,"sentiment":"POSITIVE","confidence":...}
```

If you see the response, the entire chain — public internet → VM port 3000 → nginx → backend → model + DB — is wired correctly.

---

## Links

| Resource          | URL                                                                    |
|-------------------|------------------------------------------------------------------------|
| GitHub repository | https://github.com/Ishtiak2/ticket-analyzer                           |
| Backend image     | https://hub.docker.com/r/ishtiakrahman/ticket-analyzer-backend/tags   |
| Frontend image    | https://hub.docker.com/r/ishtiakrahman/ticket-analyzer-frontend/tags  |
| Live deployment   | *(placeholder — filled in after Phase 6 VM deploy)*                    |

---

## Troubleshooting Notes

These are real issues hit during Phase 4's deliberate-breakage pass. Each entry is in **symptom → cause → fix** form so the failure mode is recognizable, not the resolution alone.

### 1. Browser shows CORS error in console

**Symptom:** Submitting a ticket from the frontend produces `Access to fetch at 'http://localhost:8000/tickets' from origin 'http://localhost:3000' has been blocked by CORS policy`.

**Cause:** The frontend bundle has `http://localhost:8000` baked in as the API base URL. This was the default in Phase 0. The frontend then makes cross-origin requests directly to the backend, which has CORS disabled (default — we use the nginx reverse proxy instead).

**Fix:** Rebuild the frontend with `VITE_API_BASE_URL=/api` (the relative path that nginx proxies):

```bash
# In docker-compose.yml and frontend/Dockerfile, change:
VITE_API_BASE_URL: ${VITE_API_BASE_URL:-/api}   # NOT http://localhost:8000

docker compose build frontend
docker compose up -d frontend
```

Reload the browser. The bundle now contains `/api`, not `localhost:8000`.

### 2. Backend boots offline, then crashes with `OSError: We couldn't connect to 'huggingface.co'`

**Symptom:** Container exits within seconds of starting with `OSError` and a stack trace pointing at `transformers/utils/hub.py`.

**Cause:** `HF_HOME` is pointing at a directory that has no model weights — usually because `HF_HOME` was overridden at runtime to a path the build step didn't use.

**Fix:** `HF_HOME` must match the path the build step baked weights into. The correct pair is:

```dockerfile
# backend/Dockerfile
ENV HF_HOME=/opt/hf-cache
RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
  AutoTokenizer.from_pretrained('distilbert-base-uncased-finetuned-sst-2-english'); \
  AutoModelForSequenceClassification.from_pretrained('distilbert-base-uncased-finetuned-sst-2-english')"
```

And in `.env`:

```
HF_HOME=/opt/hf-cache
TRANSFORMERS_OFFLINE=1
```

`TRANSFORMERS_OFFLINE=1` makes the failure loud instead of silently downloading on stage.

### 3. POST returns 500 with `OperationalError: could not translate host name "db"`

**Symptom:** Backend stays up and `/health` returns 200, but `POST /tickets` returns 500 with `OperationalError: could not translate host name "db"`.

**Cause:** The Postgres container isn't running, or the backend started before Postgres was reachable.

**Fix:**

```bash
docker compose ps           # check db container status
docker compose logs db      # if exited, check for "database system is ready"
```

If the backend started before Postgres, the `depends_on: condition: service_healthy` block in `docker-compose.yml` prevents this — but only if the Postgres container actually has a `healthcheck:` block. Both must be present together.

### 4. Browser console shows `Unexpected token <` after submitting

**Symptom:** Frontend logs `SyntaxError: Unexpected token '<'` or similar when parsing the POST response.

**Cause:** The nginx `/api/` reverse-proxy block was removed from `frontend/nginx.conf`. Without it, the SPA fallback catches `/api/tickets` and serves `index.html` (which starts with `<`) instead of forwarding to the backend.

**Fix:** Restore the `/api/` block in `frontend/nginx.conf`:

```nginx
location /api/ {
    proxy_pass http://backend:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Then rebuild: `docker compose build frontend && docker compose up -d frontend`.

### 5. Backend returns `sentiment: "LABEL_0"` instead of `"NEGATIVE"`

**Symptom:** Tickets persist successfully, but `sentiment` is `"LABEL_0"` or `"LABEL_1"` rather than the human-readable labels.

**Cause:** A different model is loaded — usually `sshleifer/tiny-distilbert-base-uncased-finetuned-sst-2-english` (the architecture diagram's model) instead of `distilbert-base-uncased-finetuned-sst-2-english` (the PRD's model). The `tiny-*` variant's label mapping is unreliable.

**Fix:** Ensure `MODEL_NAME` in `.env` matches the model baked at build time:

```
MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english
```

Then rebuild the backend image: `docker compose build backend`.

### 6. First POST after boot takes 30+ seconds; later POSTs are fast

**Symptom:** Cold-boot latency on the first request, then normal speed afterwards.

**Cause:** Model is being lazy-loaded on first request rather than at startup.

**Fix:** The backend loads the model eagerly during the FastAPI `startup` event handler in `backend/app/main.py`. If you see cold-start latency, check that the `@app.on_event("startup")` hook is still present and that the model load call isn't inside a request handler.

```python
@app.on_event("startup")
def load_model() -> None:
    global _classifier
    _classifier = pipeline("sentiment-analysis", model=_model_name)
```

A synthetic warm-up request can also be sent from the deploy script after `docker compose up -d` returns.

---

## Known Limitations

These are intentional scope decisions from PRD §3 ("Not Included" column) and §12, stated explicitly so reviewers don't mistake them for oversights.

| Limitation | Why it's here |
|------------|---------------|
| **No migrations** — `Base.metadata.create_all()` runs at startup | PRD scope: "Minimal live demo focused on workflow, not feature depth." Migrations are explicitly out of scope. |
| **No authentication** — anyone who can reach the frontend can submit tickets | PRD scope: "One page form and ticket list. Authentication, dashboard" are out of scope. |
| **Demo-grade DB credentials** — `postgres`/`postgres` in `.env.example` | Workshop-only. If you reuse this stack beyond the hackathon, rotate `POSTGRES_PASSWORD` in `.env` and the `POSTGRES_PASSWORD` env var in `docker-compose.yml`. |
| **No CI/CD** — images are built and pushed by hand from a developer machine | PRD scope: "Kubernetes or CI/CD" is out of scope. A team-of-one push workflow is fine for a demo. |
| **No HTTPS in local dev** — `http://localhost:3000` only | Local stack assumes you're on a trusted network. The VM deployment is expected to be behind a reverse proxy (e.g. nginx, CloudFront, ALB) that terminates TLS. |
| **Only port 3000 published on prod** — backend and DB not reachable from outside the VM | Intentional: see Risk Register row 3 in `IMPLEMENTATION_PLAN.md`. Debugging access via SSH tunnel. |
| **Vite env vars are compile-time** — `VITE_API_BASE_URL` is baked at build, not runtime | A Vite constraint, not a project bug. The default `/api` works on both localhost and the VM because the path is relative; nginx proxies the same path in both places. |

---

## License

This project was built for the bKash presents SUST CSE Carnival 2026 workshop. Treat it as a demo, not a production system.
