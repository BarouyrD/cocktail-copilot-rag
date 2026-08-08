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

## Setup

Requirements: Docker + Docker Compose. For local (non-Docker) runs you also need
[`uv`](https://github.com/astral-sh/uv) and Python 3.12.

1. Copy the environment file and add your OpenAI key:

   ```bash
   cp .env.example .env
   # edit .env and set OPENAI_API_KEY
   ```

2. (Local only) install dependencies and download the embedding model:

   ```bash
   make install     # uv sync
   make download    # download the ONNX model into models/
   make ingest      # fetch cocktails into data/cocktails.csv (already included)
   ```

   > **Windows / PowerShell (no `make`)?** Every task is also exposed as a
   > cross-platform command. Run `uv sync` once, then use `uv run cocktail-cli
   > <task>` for any task, e.g. `uv run cocktail-cli download`,
   > `uv run cocktail-cli ingest`. See `uv run cocktail-cli --help` for the full
   > list. The `make` targets below are just thin wrappers around these commands.

## Running with Docker Compose

Start Postgres, Grafana, and the Streamlit app together:

```bash
docker-compose up --build
```

Initialize the database tables (one time):

```bash
docker-compose exec streamlit python cocktail_assistant/db_init.py
```

- App: http://localhost:8501
- Grafana: http://localhost:3000 (login: `admin` / `admin`)

Stop everything:

```bash
docker-compose down
```

Data in PostgreSQL and Grafana persists across restarts via Docker volumes.

## Running locally (without Docker)

```bash
make db          # create tables (needs a running PostgreSQL)
make up          # or: uv run streamlit run cocktail_assistant/app.py
make dashboard   # the Streamlit monitoring dashboard
```

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

| Criterion | How it is addressed |
|---|---|
| Problem description | This README |
| Retrieval flow | Knowledge base + LLM (hybrid retrieval → prompt → OpenAI) |
| Retrieval evaluation | text / vector / hybrid compared (notebook 03) |
| LLM evaluation | two prompts compared via LLM judge (notebook 04) |
| Interface | Streamlit UI |
| Ingestion pipeline | Airflow DAG (+ Python script) |
| Monitoring | Postgres + Grafana (7 panels) and user feedback |
| Containerization | full `docker-compose.yaml` |
| Reproducibility | pinned deps, included data, clear instructions |
| Best practices | hybrid text + vector search (RRF) |
