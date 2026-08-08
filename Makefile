# Thin wrapper around the cross-platform CLI (cocktail_assistant/cli.py).
# On Windows / PowerShell (no `make`), use the same tasks directly, e.g.:
#     uv run cocktail-cli download
.PHONY: install download ingest db up down dashboard data app airflow-up airflow-down

# Install dependencies (also installs the `cocktail-cli` command)
install:
	uv sync

download:
	uv run cocktail-cli download

ingest:
	uv run cocktail-cli ingest

db:
	uv run cocktail-cli db

up:
	uv run cocktail-cli up

down:
	uv run cocktail-cli down

dashboard:
	uv run cocktail-cli dashboard

data:
	uv run cocktail-cli data

app:
	uv run cocktail-cli app

airflow-up:
	uv run cocktail-cli airflow-up

airflow-down:
	uv run cocktail-cli airflow-down
