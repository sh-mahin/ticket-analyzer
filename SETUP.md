# SETUP.md — Ticket Analyzer

A self-contained setup guide for the **Ticket Analyzer** project (bKash presents SUST CSE Carnival 2026 — Codex Community Hackathon).

This file is the single source of truth for *how to install, configure, run, and deploy* the project. It reflects the binding decisions in `IMPLEMENTATION_PLAN.md` §1 and the contracts in `PRD.md`.

---

## 1. Overview

Ticket Analyzer is a minimal full-stack app:

- **Frontend** — React + Vite, served by Nginx on port `3000`.
- **Backend** — FastAPI + Uvicorn on port `8000`, runs the tiny Hugging Face sentiment model `distilbert-base-uncased-finetuned-sst-2-english` (weights baked into the image at build time).
- **Database** — PostgreSQL 16 (named volume `pgdata`).

```
Browser :3000  →  frontend (Nginx, /api/* proxy)  →  backend :8000  →  Postgres :5432
                                                  ↘  distilbert-sst-2 (in-process)
```

---

## 2. Prerequisites

Install these on your local machine before anything else.

| Tool                | Minimum version | Why                                               | Install (macOS)                            |
| ------------------- | --------------- | ------------------------------------------------- | ------------------------------------------ |
| Docker Desktop      | 4.x             | Runs `docker compose`, builds images              | `brew install --cask docker`               |
| Docker Compose      | v2 (bundled)    | Local stack + prod overlay                        | Included with Docker Desktop               |
| Git                 | 2.40+           | Clone / push repo                                 | `brew install git`                         |
| Puku CLI            | latest          | Workshop-mandated workflow (build/run/deploy)     | https://puku.sh                            |
| AWS CLI *(Task 2)*  | 2.x             | Configure credentials from Poridhi Lab            | `brew install awscli`                      |
| DockerHub account   | —               | Push backend & frontend images                    | https://hub.docker.com/                    |
| GitHub account      | —               | Push source                                       | https://github.com/                        |
| Poridhi Lab access  | —               | Source for AWS credentials + target VM            | https://poridhi.io                         |

Optional, only if you want to edit code outside Docker:

| Tool    | Version | Purpose                     |
| ------- | ------- | --------------------------- |
| Node.js | 20 LTS  | Frontend local dev          |
| Python  | 3.11    | Backend local dev           |

Verify the required tools:

```bash
docker --version        # Docker version 24+
docker compose version  # Docker Compose version v2.x+
git --version
puku --version          # or whichever invocation your install uses
aws --version           # for Task 2 only
```

---

## 3. Repository Layout

The structure below is **authoritative** — keep it intact; the compose files assume it.

```
ticket-analyzer/
├── PRD.md                          # verbatim copy of workshop Appendix A
├── README.md                       # Task 3 deliverable
├── IMPLEMENTATION_PLAN.md          # decisions + phases
├── Phases.md                       # step-by-step build checklist
├── SETUP.md                        # this file
├── .gitignore
├── .env.example                    # documents every env var; copy → .env
├── docker-compose.yml              # local dev (build: contexts)
├── docker-compose.prod.yml         # deploy overlay (image: tags, no build:)
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .dockerignore
│   └── app/
│       ├── main.py                 # FastAPI app, lifespan startup
│       ├── config.py               # pydantic-settings Settings
│       ├── database.py             # engine, SessionLocal, Base
│       ├── models.py               # SQLAlchemy ORM: Ticket
│       ├── schemas.py              # Pydantic: TicketCreate, TicketOut, HealthOut
│       ├── crud.py                 # create_ticket, list_tickets
│       ├── sentiment.py            # model load-once + predict()
│       └── routers/
│           ├── health.py
│           └── tickets.py
├── frontend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── nginx.conf                  # reverse proxy /api → backend
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/client.ts           # uses VITE_API_BASE_URL
│       ├── components/
│       │   ├── TicketForm.tsx
│       │   └── TicketList.tsx
│       └── types/ticket.ts
└── scripts/                        # demo glue (curl smokes, dry-runs)
```

---

## 4. Environment Variables

`.env.example` in the repo root mirrors the table from `IMPLEMENTATION_PLAN.md` §6 and `PRD.md` §11. **No real secrets are ever committed.**

| Service   | Variable               | Example / Default                                          | Required | Notes                                                                 |
| --------- | ---------------------- | ---------------------------------------------------------- | -------- | --------------------------------------------------------------------- |
| backend   | `DATABASE_URL`         | `postgresql://postgres:postgres@db:5432/ticket_db`         | yes      | Targets the `db` service name on the compose internal network         |
| backend   | `MODEL_NAME`           | `distilbert-base-uncased-finetuned-sst-2-english`          | yes      | Must match the bake-in target in the backend Dockerfile               |
| backend   | `HF_HOME`              | `/opt/hf-cache`                                            | yes      | Must match the Dockerfile's bake-in path exactly                      |
| backend   | `TRANSFORMERS_OFFLINE` | `1`                                                        | yes      | Forces a loud failure if weights are missing (offline-boot guarantee) |
| backend   | `CORS_ALLOWED_ORIGINS` | *(empty = disabled)*                                      | no       | Fallback only; reverse proxy is the default per PRD §12               |
| backend   | `LOG_LEVEL`            | `info`                                                     | no       |                                                                       |
| frontend  | `VITE_API_BASE_URL`    | `/api`                                                     | yes      | **Baked at image build time** — Vite env vars are compile-time        |
| postgres  | `POSTGRES_USER`        | `postgres`                                                 | yes      | Demo-grade only                                                        |
| postgres  | `POSTGRES_PASSWORD`    | `postgres`                                                 | yes      | Demo-grade only                                                        |
| postgres  | `POSTGRES_DB`          | `ticket_db`                                                | yes      |                                                                       |

### Create your local `.env`

```bash
cp .env.example .env
```

Edit `.env` only if you need to change a value — defaults work for the local stack.

---

## 5. Local Setup — Step by Step

### 5.1 Clone

```bash
git clone https://github.com/Ishtiak2/ticket-analyzer.git
cd ticket-analyzer
```

### 5.2 Configure environment

```bash
cp .env.example .env
# (optional) edit .env if you need to override a value
```

### 5.3 Bring the stack up

```bash
docker compose up --build
```

This builds both images from source, creates the `db`, `backend`, and `frontend` services, and waits for the Postgres healthcheck before starting the backend.

### 5.4 Verify

In a second terminal:

```bash
curl http://localhost:8000/health
# → {"status":"ok"}

curl -I http://localhost:3000
# → HTTP/1.1 200 OK   (serves the React placeholder or full UI once built)
```

Submit a ticket via curl:

```bash
curl -X POST http://localhost:3000/api/tickets \
  -H "Content-Type: application/json" \
  -d '{"title":"Setup check","message":"Hello from SETUP.md","category":"smoke"}'
# → 201 Created, sentiment + confidence populated
```

List tickets:

```bash
curl http://localhost:3000/api/tickets
# → JSON array, newest first
```

### 5.5 End-to-end browser check

1. Open `http://localhost:3000` in a real browser (not `curl`).
2. Fill the form, submit a ticket — sentiment appears in the list without a manual page reload.
3. **Hard-refresh** the page (Cmd/Ctrl+Shift+R). The ticket must still be there — proves it's in Postgres, not in React state.

### 5.6 Tear down

```bash
docker compose down            # keeps the pgdata volume
docker compose down -v         # also wipes Postgres volume (fresh-volume test)
```

---

## 6. API Reference

All endpoints are served under `/api/*` when reached through the frontend Nginx proxy (port `3000`), and directly on port `8000` for backend-to-backend / local testing.

### `GET /health`

```http
GET /api/health     # via proxy
GET /health         # direct to :8000
```

**200 OK**
```json
{ "status": "ok", "model_loaded": true }
```

### `POST /tickets`

**Request**
```json
{
  "title": "Lab VM issue",
  "message": "My lab VM is not opening before the deadline.",
  "category": "lab"
}
```

**Validation**
- `title`: required, 1–255 chars
- `message`: required, 1–4000 chars (model truncates internally at 512 tokens)
- `category`: optional, ≤100 chars

**201 Created**
```json
{
  "id": 1,
  "title": "Lab VM issue",
  "message": "My lab VM is not opening before the deadline.",
  "category": "lab",
  "sentiment": "NEGATIVE",
  "confidence": 0.999,
  "created_at": "2026-05-20T10:30:00"
}
```

**422** — validation error (FastAPI default). **503** — model not loaded yet (should not occur; documented for honesty).

### `GET /tickets`

**Query params:** `limit` (default 50, max 200), `offset` (default 0).

**200 OK** — JSON array, `created_at DESC`.

```json
[
  {
    "id": 2,
    "title": "Great onboarding",
    "message": "The setup docs were super clear, thanks!",
    "category": "feedback",
    "sentiment": "POSITIVE",
    "confidence": 0.998,
    "created_at": "2026-05-20T10:31:00"
  },
  {
    "id": 1,
    "title": "Lab VM issue",
    "message": "My lab VM is not opening before the deadline.",
    "category": "lab",
    "sentiment": "NEGATIVE",
    "confidence": 0.999,
    "created_at": "2026-05-20T10:30:00"
  }
]
```

---

## 7. Data Model

Table `tickets`, auto-created at backend startup via `Base.metadata.create_all(engine)`.

| Column       | Type           | Constraints                  | Notes                                  |
| ------------ | -------------- | ---------------------------- | -------------------------------------- |
| `id`         | `INTEGER`      | PK, autoincrement            | Decision: integer PK (per Plan §1.2)   |
| `title`      | `VARCHAR(255)` | NOT NULL                     |                                        |
| `message`    | `TEXT`         | NOT NULL                     | Body sent to the model                 |
| `category`   | `VARCHAR(100)` | NULLABLE                     | Optional per PRD §4                    |
| `sentiment`  | `VARCHAR(20)`  | NOT NULL                     | `POSITIVE` \| `NEGATIVE`               |
| `confidence` | `FLOAT`        | NOT NULL                     | 0.0–1.0 from model softmax             |
| `created_at` | `TIMESTAMP`    | NOT NULL, server default `now()` | UTC, indexed for `ORDER BY DESC`   |

---

## 8. AI Model Integration

Strategy follows `IMPLEMENTATION_PLAN.md` §7 and PRD §9.

1. **Bake, don't fetch.** The backend Dockerfile calls `AutoTokenizer.from_pretrained(MODEL_NAME)` and `AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)` **during the build**, with `HF_HOME=/opt/hf-cache`.
2. **Offline by default.** Runtime sets `TRANSFORMERS_OFFLINE=1`. If the bake step was skipped or the cache path mismatches, the container fails loudly on startup — no silent network fallback.
3. **Load once at startup.** The pipeline is loaded in the FastAPI lifespan hook into a module-level singleton in `app/sentiment.py`. Every request reuses it.
4. **CPU-only torch.** Installed from `https://download.pytorch.org/whl/cpu` to keep the image ~600–800 MB.
5. **Pinned versions.** `transformers`, `torch`, and the model name are pinned in `requirements.txt` and the Dockerfile.
6. **Label sanity check.** At startup we assert `id2label` resolves to exactly `POSITIVE`/`NEGATIVE` — never `LABEL_0`/`LABEL_1`.

**Offline-boot proof** (one of the PRD §13 dry-runs):

```bash
docker run --rm --network none \
  -e DATABASE_URL=postgresql://x:x@localhost/x \
  -e TRANSFORMERS_OFFLINE=1 -e HF_HOME=/opt/hf-cache \
  <backend-image-name> python -c "from app.sentiment import load_model; load_model(); print('OK')"
```

Must print `OK` with zero network errors.

---

## 9. Docker & Compose Strategy

- **`docker-compose.yml`** — local dev. Uses `build:` contexts so `docker compose up --build` always reflects current source.
- **`docker-compose.prod.yml`** — deploy overlay. Uses `image: <dockerhub-username>/ticket-analyzer-backend:v1` and `image: <dockerhub-username>/ticket-analyzer-frontend:v1` (no `build:` keys). Run on the VM with `docker compose -f docker-compose.prod.yml up -d`.

**Healthcheck-gated startup** keeps the cold boot honest:

```yaml
db:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
    interval: 5s
    timeout: 5s
    retries: 5
backend:
  depends_on:
    db:
      condition: service_healthy
```

**Port exposure:** only `3000` (frontend) is published to the host. `5432` (db) and `8000` (backend) live on the internal compose network and are **not** exposed publicly on the VM.

**Secrets:** `.env` is gitignored. `.env.example` carries placeholders only. Demo-grade DB creds are acceptable per PRD scope but flagged as a known limitation.

---

## 10. Deployment Guide (Task 2)

### 10.1 Get cloud credentials from Poridhi Lab

Open your Poridhi Lab environment and copy the issued AWS credentials (access key, secret, region, optional session token). **Do not write them into any repo file.**

```bash
aws configure
# or, for session-token credentials:
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...
export AWS_DEFAULT_REGION=...
```

### 10.2 Push source and images

```bash
# Source to GitHub
git add .
git commit -m "Ticket Analyzer: Tasks 0-4 complete"
git push -u origin main

# Login and build/tag/push images
docker login
docker build -t <dockerhub-username>/ticket-analyzer-backend:v1 ./backend
docker build -t <dockerhub-username>/ticket-analyzer-frontend:v1 ./frontend

docker push <dockerhub-username>/ticket-analyzer-backend:v1
docker push <dockerhub-username>/ticket-analyzer-frontend:v1
```

### 10.3 Deploy via Puku CLI

Follow the Puku CLI workflow for provisioning / connecting to the target (AWS instance or Poridhi Cloud VM). Place `docker-compose.prod.yml` and a deploy-time `.env` on the VM (via Puku's deploy mechanism or `scp`), then:

```bash
# On the VM
docker login
docker compose -f docker-compose.prod.yml up -d
```

### 10.4 Warm-up + verify from a remote client

```bash
# Warm-up to absorb first-request cold start
curl -X POST http://<vm-host>:3000/api/tickets \
  -H "Content-Type: application/json" \
  -d '{"title":"warmup","message":"warming up the model"}'

# From a different network (laptop on cellular, phone, etc.):
# Open http://<vm-host>:3000, submit a ticket, refresh — sentiment + persistence confirmed.
```

---

## 11. Verification Checklist (Acceptance Criteria)

Run these in order. Every box must be ✅ before you call the project done.

- [ ] `docker compose up --build` brings up all three services clean from a fresh checkout.
- [ ] `curl http://localhost:8000/health` → `{"status":"ok"}`.
- [ ] `POST /api/tickets` returns 201 with a real sentiment label (`POSITIVE`/`NEGATIVE`) and a real confidence score (close to 1.0 for obvious cases), never `LABEL_0`/`LABEL_1`.
- [ ] `GET /api/tickets` returns the just-created ticket.
- [ ] Browser: submit a ticket, see sentiment in the list, **hard-refresh** — ticket still there.
- [ ] **Offline-boot dry-run:** `docker run --network none …` loads the model with no network access.
- [ ] **Fresh-volume dry-run:** `docker compose down -v && docker compose up --build` — first `POST /tickets` succeeds without manual migrations.
- [ ] **Remote-browser dry-run:** submit from a non-VM, non-localhost browser — round-trip works.
- [ ] GitHub repo is public and contains `PRD.md` + `README.md`.
- [ ] DockerHub image pages (backend + frontend) are public and show the deployed `:v1` tag.
- [ ] Deployed URL (frontend `:3000`) is reachable from outside the VM.

---

## 12. Troubleshooting

Symptom → cause → fix. Populated from Phase 4's deliberate-breakage pass and likely live-demo edge cases.

| Symptom | Cause | Fix |
| --- | --- | --- |
| `curl /health` → connection refused on first boot | Backend started before Postgres was ready | Ensure `depends_on: db: condition: service_healthy` is set; rebuild compose |
| `POST /tickets` → `LABEL_0` returned | Wrong model variant loaded (e.g. `sshleifer/tiny-*`) | Confirm `MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english` matches what was baked in; rebuild backend image |
| `OSError: model weights not found` at startup | `HF_HOME` mismatch between Dockerfile and runtime env | Both must be `/opt/hf-cache`; rebuild image so bake path matches |
| Frontend network calls fail with CORS / 404 | Nginx `/api` proxy block missing or wrong | Restore the `location /api/ { proxy_pass http://backend:8000/; }` block in `frontend/nginx.conf`; rebuild frontend image |
| Slow first `POST /tickets` (5+ s) | Model lazy-loading on first request | Move the pipeline load into the FastAPI lifespan startup; rebuild |
| Backend image > 1.5 GB | Accidentally pulled GPU torch | Confirm `torch` is installed via `--index-url https://download.pytorch.org/whl/cpu` |
| `POST /tickets` → 422 on valid-looking body | Field validation rejected (e.g. `title` empty) | FastAPI's default — inspect response `detail` for the exact field |
| `docker compose up` fails on a fresh clone | `.env` missing | `cp .env.example .env` |
| `git status` shows `node_modules/` or `__pycache__/` | `.gitignore` not honored on existing files | `git rm -r --cached <path>` and recommit |
| Deployed URL loads UI but `POST /api/tickets` 502 | Backend not running or unhealthy on the VM | `docker compose -f docker-compose.prod.yml ps` and `logs backend` on the VM |

---

## 13. Known Limitations

These are **scoped-out by the PRD**, not oversights. Stated explicitly so reviewers don't mistake them for production gaps.

- **No migrations.** Schema is created via `Base.metadata.create_all()` at backend startup (hackathon shortcut). Upgrade path if this grows: Alembic.
- **No auth / no users.** Per PRD §3.
- **Demo-grade DB credentials.** `postgres`/`postgres` scoped to the internal Docker network; not production-grade.
- **No CI/CD.** Build + push is a manual sequence documented in §10.2.
- **Single-process model load.** FastAPI workers > 1 would each load their own copy of the model. Default to `WORKERS=1`.
- **No fine-tuning / no LLM agents.** Per PRD §3; we use the base distilbert-sst-2 checkpoint as-is.

---

## 14. One-Page Quickstart

```bash
# 1. Prerequisites: Docker Desktop + Docker Compose v2
# 2. Clone
git clone https://github.com/Ishtiak2/ticket-analyzer.git && cd ticket-analyzer

# 3. Configure
cp .env.example .env

# 4. Run
docker compose up --build

# 5. Verify (separate terminal)
curl http://localhost:8000/health
curl -X POST http://localhost:3000/api/tickets \
  -H "Content-Type: application/json" \
  -d '{"title":"hi","message":"This is wonderful","category":"smoke"}'
curl http://localhost:3000/api/tickets

# 6. Open the UI
open http://localhost:3000
```

---

*End of SETUP.md. Cross-references: PRD.md (what), IMPLEMENTATION_PLAN.md (why), Phases.md (how).*
