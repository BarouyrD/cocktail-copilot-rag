# Cocktail Assistant

A RAG (Retrieval-Augmented Generation) application that answers questions about
cocktails — ingredients, recipes, glassware, and preparation steps — using data
from [TheCocktailDB](https://www.thecocktaildb.com/).

Ask *"What's in a Margarita?"* or *"Suggest a non-alcoholic drink"* and get a
grounded answer built from a real cocktail knowledge base, with response time,
token usage, cost, and answer-relevance tracked for every conversation.

This project was built as the final project for the
[LLM Zoomcamp](https://github.com/DataTalksClub/llm-zoomcamp).

---

## Problem description

Recipe information online is scattered across blogs and inconsistent formats.
This app centralizes a clean cocktail knowledge base (~430 drinks) and lets a
user ask natural-language questions. Instead of querying the LLM directly (which
would hallucinate recipes), the app **retrieves the most relevant cocktails**
from the knowledge base and asks the LLM to answer **only from that context**,
producing accurate, grounded answers.

## Architecture

```
User ──▶ Streamlit UI (app.py)
             │
             ▼
   Hybrid retrieval (RRF)              PostgreSQL ──▶ Grafana dashboard
   ├─ text search (minsearch)   ┐        ▲
   └─ vector search (ONNX MiniLM)┘        │ conversations + feedback
             │                            │
             ▼                            │
   Prompt + context ──▶ OpenAI (LLM) ─────┘
             │
             ▼
   Answer + metrics + LLM relevance judge + user feedback
```

- **Knowledge base**: `data/cocktails.csv`, fetched from TheCocktailDB API.
- **Retrieval**: hybrid search combining `minsearch` text (TF-IDF) and vector
  search (`all-MiniLM-L6-v2` ONNX embeddings) merged with Reciprocal Rank Fusion.
- **LLM**: OpenAI via the `openai` SDK (Responses API).
- **Interface**: Streamlit.
- **Monitoring**: PostgreSQL + Grafana (auto-provisioned, 7 panels).
- **Ingestion**: Airflow DAG (or a plain Python script).
- **Containerization**: Docker Compose (Postgres + Grafana + Streamlit).

## How it works (step by step)

When a user submits a question in the Streamlit UI, the following happens:

1. **Retrieve context (hybrid search).** The question is run through two
   retrievers in parallel:
   - a **text search** over the cocktail fields (`minsearch`, TF-IDF with field
     boosts — `name` ×3, `ingredients` ×2, `category` ×0.5), and
   - a **vector search** using `all-MiniLM-L6-v2` sentence embeddings (computed
     locally with `onnxruntime`, no external embedding API).
   The two ranked lists are merged with **Reciprocal Rank Fusion (RRF)** to
   produce the final top-5 cocktails. This is implemented in
   [`rag_helper.py`](cocktail_assistant/rag_helper.py) (`RAGHybrid`).

2. **Build the prompt.** The retrieved cocktails (name, category, glass,
   ingredients, measures, instructions) are formatted into a context block and
   inserted into a prompt template, together with a system instruction telling
   the LLM to answer **only from the provided context** and to say *"I don't
   know"* if the answer isn't there. This prevents hallucinated recipes.

3. **Call the LLM.** The prompt is sent to OpenAI. The response, along with token
   counts, latency, and estimated cost, is captured in an `LLMCallRecord`
   ([`metrics.py`](cocktail_assistant/metrics.py)).

4. **Store the conversation.** The question, answer, model, tokens, response
   time, and cost are written to the `conversations` table in PostgreSQL
   ([`db_save.py`](cocktail_assistant/db_save.py)).

5. **Judge relevance.** A second LLM call ("LLM-as-a-judge") classifies the
   answer as `RELEVANT`, `PARTLY_RELEVANT`, or `NON_RELEVANT` and stores the
   verdict in the `feedback` table ([`judge.py`](cocktail_assistant/judge.py)).

6. **Collect user feedback.** The user can give a 👍 / 👎 on the answer, which is
   also stored in the `feedback` table.

7. **Monitor.** Grafana reads directly from PostgreSQL and visualises everything
   on an auto-provisioned dashboard (see [Monitoring](#monitoring)).

## Project structure

```
.
├── cocktail_assistant/        # application package
│   ├── ingest.py              # fetch + parse cocktails, build indexes
│   ├── rag_helper.py          # RAGBase / RAGVector / RAGHybrid + prompts
│   ├── embedder.py            # ONNX all-MiniLM-L6-v2 embedder
│   ├── download.py            # download the ONNX model
│   ├── metrics.py             # RAGWithMetrics + LLMCallRecord
│   ├── evaluation_utils.py    # structured LLM calls, pricing, parallel map
│   ├── judge.py               # LLM relevance judge
│   ├── assistant.py           # create_assistant() (hybrid + metrics)
│   ├── app.py                 # Streamlit chat UI
│   ├── dashboard.py           # Streamlit monitoring dashboard
│   ├── generate_data.py       # synthetic data pump for the dashboard
│   └── db_*.py                # PostgreSQL init / save / query / feedback
├── notebooks/                 # data exploration + evaluation
│   ├── 01_data_exploration.ipynb
│   ├── 02_ground_truth_gen.ipynb
│   ├── 03_retrieval_eval.ipynb
│   └── 04_rag_eval.ipynb
├── airflow/                   # standalone ingestion pipeline
│   ├── dags/ingest_cocktails.py
│   └── docker-compose.airflow.yaml
├── grafana/provisioning/      # auto-provisioned datasource + dashboard
├── data/cocktails.csv         # knowledge base
├── docker-compose.yaml
├── Dockerfile
├── pyproject.toml
└── Makefile
```

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Latest | Required for the full stack |
| [uv](https://github.com/astral-sh/uv) | Latest | Required for local runs only |
| Python | 3.12 | Managed by `uv` automatically |
| OpenAI API key | — | [platform.openai.com](https://platform.openai.com/api-keys) |

---

## Quick start (Docker — recommended)

This is the fastest way to get the full stack running on any machine.

### 1. Clone the repository

```bash
git clone https://github.com/your-username/cocktail-copilot-rag.git
cd cocktail-copilot-rag
```

### 2. Create your `.env` file

Copy the provided template and add your OpenAI key:

```bash
cp .env.example .env
```

Then open `.env` and set your real key. The file should look like this:

```env
# OpenAI API key (required)
OPENAI_API_KEY=sk-proj-...your-key-here...

# PostgreSQL connection
POSTGRES_HOST=localhost
POSTGRES_DB=cocktail_assistant
POSTGRES_USER=user
POSTGRES_PASSWORD=password

# Grafana admin password
GRAFANA_ADMIN_PASSWORD=admin
```

> **How `POSTGRES_HOST` works:** keep it as `localhost`. When running under
> Docker Compose, the value is **automatically overridden to `postgres`** (the
> service name on the Docker network), so the same `.env` works for both Docker
> and local runs without edits.

> **Never commit your `.env` file.** It is already listed in `.gitignore`, and
> the only tracked version is `.env.example`, which contains no secrets.

### 3. Start the stack

```bash
docker compose up --build
```

Or on Windows / PowerShell (no `make`):

```powershell
uv run cocktail-cli up
```

Docker will:
1. Build the Streamlit image (downloads the ONNX embedding model at build time).
2. Start Postgres and wait for it to be healthy.
3. Start Grafana (auto-provisioned with the monitoring dashboard).
4. Start Streamlit — the entrypoint script **automatically creates the database
   tables** on every startup, so no manual DB init step is needed.

### 4. Open the apps

| Service | URL | Login |
|---|---|---|
| **Cocktail assistant** | http://localhost:8501 | — |
| **Grafana dashboard** | http://localhost:3000 | `admin` / `admin` |

### 5. Stop the stack

```bash
docker compose down
```

Data in PostgreSQL and Grafana persists across restarts via named Docker volumes.
To wipe everything (including data):

```bash
docker compose down -v
```

---

## Running locally (without Docker)

Use this if you want to run the Streamlit app or notebooks outside of Docker
(e.g. for development). You still need a running PostgreSQL instance — the
easiest way is to start only the database container:

```bash
docker compose up postgres -d
```

Then install dependencies and start the app:

```bash
# macOS / Linux
make install    # uv sync — installs the project and all dependencies
make download   # download the ONNX embedding model into models/
make app        # run the Streamlit app on http://localhost:8501

# Windows / PowerShell
uv sync
uv run cocktail-cli download
uv run cocktail-cli app
```

> **Note:** Running locally uses `POSTGRES_HOST=localhost` (the default in
> `.env.example`), so the app connects to the port `5432` that the Postgres
> container exposes on your machine. You still need the OpenAI key set in `.env`.

### Available CLI commands

Every `make` target has a Windows-compatible equivalent:

| Task | make | PowerShell |
|---|---|---|
| Install dependencies | `make install` | `uv sync` |
| Download ONNX model | `make download` | `uv run cocktail-cli download` |
| Fetch cocktail data | `make ingest` | `uv run cocktail-cli ingest` |
| Start full Docker stack | `make up` | `uv run cocktail-cli up` |
| Stop full Docker stack | `make down` | `uv run cocktail-cli down` |
| Run Streamlit app locally | `make app` | `uv run cocktail-cli app` |
| Run monitoring dashboard | `make dashboard` | `uv run cocktail-cli dashboard` |
| Pump sample data | `make data` | `uv run cocktail-cli data` |
| Start Airflow stack | `make airflow-up` | `uv run cocktail-cli airflow-up` |

## Ingestion pipeline (Airflow)

An automated ingestion pipeline is provided as a standalone Airflow stack:

```bash
make airflow-up          # docker-compose -f airflow/docker-compose.airflow.yaml up
```

Open http://localhost:8080 (login: `admin` / `admin`), enable and run the
`ingest_cocktails` DAG. It fetches all cocktails from TheCocktailDB and writes
`data/cocktails.csv`. The same logic is also available as a plain script via
`make ingest`.

## Evaluation

All evaluation is in `notebooks/` (run after `make download` and `make ingest`):

- **02_ground_truth_gen** — generate 5 questions per cocktail → `data/ground_truth.csv`.
- **03_retrieval_eval** — compare **text**, **vector**, and **hybrid** retrieval
  with **hit rate** and **MRR**, plus a boost grid search. Hybrid (RRF) is used
  in the app.
- **04_rag_eval** — compare **two prompt variants** (simple vs. mixologist) by
  judging answer relevance with an LLM; the better prompt is used by default.

## Monitoring

Every conversation is stored in PostgreSQL with model, tokens, response time,
cost, and an LLM relevance judgment. Users can also give thumbs up/down feedback.

Grafana is auto-provisioned with a dashboard containing 7 panels: recent
conversations, model usage, relevance distribution, response time, token usage,
cost, and user feedback.

To populate the dashboard with sample traffic:

```bash
make data        # uv run python cocktail_assistant/generate_data.py
```

## Screenshots

> Add your own screenshots here so reviewers can see the app without running it.
> Drop the image files into a `docs/` folder and update the paths below. In the
> GitHub web editor you can also drag-and-drop an image directly into this file.

**Cocktail assistant (Streamlit UI)**

![Streamlit app](docs/app.png)

**Grafana monitoring dashboard**

![Grafana dashboard](docs/grafana.png)

## Troubleshooting

Common issues and how to fix them.

### `docker compose up` fails at `uv sync --locked`

Usually one of:
- **`package directory 'cocktail_assistant' does not exist`** or
  **`README.md cannot be found`** — dependencies are installed before the source
  is copied. This is already handled in the [`Dockerfile`](Dockerfile): the first
  `uv sync` uses `--no-install-project`, and `README.md` is copied up front.
- **Lockfile out of date** — regenerate it and rebuild:
  ```bash
  uv lock
  docker compose build --no-cache streamlit
  ```

### `relation "conversations" does not exist`

The database tables haven't been created. With the current setup the
[`entrypoint.sh`](entrypoint.sh) script creates them automatically on every
container start, so a simple restart fixes it:

```bash
docker compose up --build
```

To create the tables manually inside the running container:

```bash
docker compose exec streamlit python cocktail_assistant/db_init.py
```

### `psycopg` import hangs or errors when running `uv run cocktail-cli db` on Windows

The `psycopg[binary]` wheel can be slow/unreliable to import on some Windows
setups. You don't need to run DB init locally — it happens automatically inside
Docker. If you want to run it manually, do it in the container instead:

```bash
docker compose exec streamlit python cocktail_assistant/db_init.py
```

### Grafana shows "No data" or "you do not currently have a default database configured"

1. Make sure Postgres actually has data (ask the app a question first, or run
   `make data` to generate sample traffic).
2. Confirm the datasource provisioning file
   [`grafana/provisioning/datasources/postgres.yaml`](grafana/provisioning/datasources/postgres.yaml)
   sets a `database`, then restart Grafana:
   ```bash
   docker compose restart grafana
   ```
3. If it still misbehaves, reset **only** Grafana's state (this does not touch
   your Postgres data):
   ```bash
   docker compose stop grafana
   docker volume rm cocktail-copilot-rag_grafana_data
   docker compose up -d grafana
   ```
4. Check the dashboard time range (top-right) — the default is *Last 6 hours*.

### Port already in use (`5432`, `3000`, `8501`, or `8080`)

Another process is using that port. Either stop it, or change the host-side port
in [`docker-compose.yaml`](docker-compose.yaml), e.g. map Postgres to
`5433:5432`. Then restart with `docker compose up --build`.

### `OPENAI_API_KEY` not set / 401 errors from OpenAI

Ensure `.env` exists and contains a valid `OPENAI_API_KEY`. After editing `.env`,
restart the stack (`docker compose up --build`) so the container picks up the new
value. If a key was ever committed or shared, **rotate it** in the OpenAI
dashboard.

### Start completely fresh

To wipe all containers, volumes, and data and rebuild from scratch:

```bash
docker compose down -v
docker compose up --build
```

## Technologies

- **OpenAI** — LLM (answers + structured evaluation), via the `openai` SDK.
- **minsearch** — in-memory text (TF-IDF) and vector search.
- **all-MiniLM-L6-v2 (ONNX)** — sentence embeddings via `onnxruntime`.
- **PostgreSQL** — stores conversations and feedback.
- **Grafana** — monitoring dashboard.
- **Streamlit** — chat UI and secondary dashboard.
- **Airflow** — automated ingestion pipeline.
- **Docker Compose** — runs the whole stack.
- **uv** — dependency management (Python 3.12).

## Evaluation criteria coverage

This section maps the project to the LLM Zoomcamp grading rubric so reviewers can
quickly find each piece.

| Criterion | How it is addressed | Where to look |
|---|---|---|
| **Problem description** | A clear real-world problem (scattered, inconsistent cocktail recipes) solved with grounded RAG | [Problem description](#problem-description) |
| **Retrieval flow** | Both a knowledge base **and** an LLM are used: hybrid retrieval → prompt → OpenAI | [How it works](#how-it-works-step-by-step), [`rag_helper.py`](cocktail_assistant/rag_helper.py) |
| **Retrieval evaluation** | **Three** approaches compared (text / vector / hybrid) with hit rate & MRR; best (hybrid) is used | [`notebooks/03_retrieval_eval.ipynb`](notebooks/03_retrieval_eval.ipynb) |
| **LLM evaluation** | **Two** prompt variants compared via an LLM judge; the better prompt is used by default | [`notebooks/04_rag_eval.ipynb`](notebooks/04_rag_eval.ipynb) |
| **Interface** | Streamlit chat UI | [`app.py`](cocktail_assistant/app.py) |
| **Ingestion pipeline** | Automated with **Airflow** (plus an equivalent Python script) | [`airflow/dags/ingest_cocktails.py`](airflow/dags/ingest_cocktails.py), [`ingest.py`](cocktail_assistant/ingest.py) |
| **Monitoring** | User feedback **and** a Grafana dashboard with **7 charts** | [Monitoring](#monitoring), [`grafana/`](grafana/) |
| **Containerization** | Everything (Postgres + Grafana + Streamlit) in one `docker-compose.yaml` | [`docker-compose.yaml`](docker-compose.yaml) |
| **Reproducibility** | Clear step-by-step instructions, dataset included in `data/`, all dependency versions pinned in `uv.lock` | [Quick start](#quick-start-docker--recommended), [`pyproject.toml`](pyproject.toml), `uv.lock` |
| **Best practices — hybrid search** | Text + vector search combined with Reciprocal Rank Fusion (RRF) and evaluated | [`rag_helper.py`](cocktail_assistant/rag_helper.py), [`notebooks/03_retrieval_eval.ipynb`](notebooks/03_retrieval_eval.ipynb) |

**Not implemented (optional/bonus):** document re-ranking, user query rewriting,
and cloud deployment. The app runs locally via Docker Compose.
